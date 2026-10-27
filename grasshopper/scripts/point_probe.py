"""ENVI-met point probe: value of the grid cell nearest to each input point
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8). No numpy needed.

For every input point, finds the ENVI-met cell that contains it (= the nearest cell
centre), optionally steps out of building cells to the nearest air cell, and returns the
values of the chosen variables plus ready-made labels.

Inputs (only _run, _pts and _edx are required):
    _run        : bool         - set to True to run (connect a Boolean Toggle / Button)
    _pts        : list Point3d - probe points (LIST ACCESS)
    _edx        : str          - path to the .EDX file (.EDT with same name, same folder)
    _vars_      : list str     - variables to read (LIST ACCESS): full name, part of it
                                 ("air temp", "wind speed") or index. Default: air
                                 temperature, wind speed, relative humidity (if present)
    _skip_bldg_ : bool         - point inside a building -> use nearest air cell
                                 (default True); False = return None there
    _decimals_  : int          - decimals in labels (default 2)
    _csv_       : str          - optional path; writes the table as a .csv file
    _axis_      : str          - lock probing to one slice of the data, same as the heatmap
                                 script: "z" = plan at level _k, "x" = YZ section at column
                                 _k, "y" = XZ section at row _k. The point's coordinate
                                 along that axis is ignored. Empty = use the point's own
                                 3D position (default)
    _k          : int          - slice index for _axis_ (see x/y/z_levels), default 0
    _origin_    : Point3d      - model origin in Rhino (same as the other scripts)
Outputs:
    var_names   : all variables in the file (to pick _vars_)
    x_levels, y_levels, z_levels : cell-centre coordinates (m) - use to pick _k
    used_vars   : variables actually read
    values      : DataTree, one branch per point, one item per variable
    first_vals  : value of the first variable per point (flat list, e.g. for colouring)
    cells       : centre point of the cell used for each point
    ijk         : "i,j,k" index of that cell
    dist        : distance from input point to the cell centre (m)
    labels      : multi-line text per point -> Text Tag 3D (with tag_pts)
    labels_val  : values + units only, one line per variable (e.g. "30.12 °C");
                  empty for points inside buildings / outside the domain
    tag_pts     : label positions (input points; with _axis_ projected onto the slice)
    table       : CSV lines (header + one line per point)
"""
import io
import re
import os
import bisect
from array import array
import Rhino.Geometry as rg
import scriptcontext as sc
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

NODATA = -999.0


def opt(name, default=None):
    v = globals().get(name, default)
    return default if v is None or v == [] else v


run_on = bool(opt('_run', False))
pts_in = opt('_pts', [])
if not isinstance(pts_in, (list, tuple)):
    pts_in = list(pts_in) if hasattr(pts_in, '__iter__') else [pts_in]
pts_in = [p for p in pts_in if p is not None]
vars_in = opt('_vars_', None)
if vars_in is not None and not isinstance(vars_in, (list, tuple)):
    vars_in = list(vars_in) if hasattr(vars_in, '__iter__') and not isinstance(vars_in, str) else [vars_in]
skip_bldg = bool(opt('_skip_bldg_', True))
dec = int(opt('_decimals_', 2))
csv_path = opt('_csv_', None)
o = opt('_origin_', rg.Point3d(0, 0, 0))
axis = str(opt('_axis_', '')).strip().lower()
axis = axis if axis in ('x', 'y', 'z') else None
k_in = int(opt('_k', 0))

# outputs stay empty until _run is True
var_names = x_levels = y_levels = z_levels = used_vars = None
values = first_vals = cells = ijk = dist = labels = labels_val = tag_pts = table = None


# ---------- header helpers ----------
def tag(txt, name):
    m = re.search(r'<%s>(.*?)</%s>' % (name, name), txt, re.S | re.I)
    return m.group(1).strip() if m else None


def floats(s):
    return [float(v) for v in s.replace('\n', ',').split(',') if v.strip()]


def edges(sp):
    e = [0.0]
    for d in sp:
        e.append(e[-1] + d)
    return e


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def decode_text(raw):
    """EDX files are usually UTF-8; older ones ANSI. Also repairs mojibake like 'Â°C'."""
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            txt = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    for bad, good in ((u'\u00c3\u201a\u00c2\u00b0', u'\u00b0'), (u'\u00c2\u00b0', u'\u00b0'),
                      (u'\u00c2\u00b2', u'\u00b2'), (u'\u00c2\u00b3', u'\u00b3'),
                      (u'\u00c2\u00b5', u'\u00b5')):
        txt = txt.replace(bad, good)
    return txt


def cell_of(e, x):
    i = bisect.bisect_right(e, x) - 1
    return min(max(i, 0), len(e) - 2)


def run():
    if not pts_in:
        raise ValueError('Connect _pts (set the input to List Access).')

    # ---------- header ----------
    with open(_edx, 'rb') as f:
        txt = decode_text(f.read())
    nx, ny, nz = [int(tag(txt, t)) for t in ('nr_xdata', 'nr_ydata', 'nr_zdata')]
    xe, ye, ze = [edges(floats(tag(txt, t))) for t in ('spacing_x', 'spacing_y', 'spacing_z')]
    xc = [(xe[i] + xe[i + 1]) / 2 for i in range(nx)]
    yc = [(ye[i] + ye[i + 1]) / 2 for i in range(ny)]
    zc = [(ze[i] + ze[i + 1]) / 2 for i in range(nz)]
    vnames = [s.strip() for s in tag(txt, 'name_variables').split(',') if s.strip()]
    if axis:
        lim = {'x': nx, 'y': ny, 'z': nz}[axis]
        if not 0 <= k_in < lim:
            raise ValueError('_k must be in range 0..%d for _axis_ %s' % (lim - 1, axis))

    def find_var(q):
        try:
            i = int(q)
            if 0 <= i < len(vnames):
                return i
        except (ValueError, TypeError):
            pass
        key = norm(str(q))
        for i, n in enumerate(vnames):
            if norm(n) == key:
                return i
        for i, n in enumerate(vnames):
            if key in norm(n):
                return i
        return None

    if vars_in:
        idx = []
        for q in vars_in:
            i = find_var(q)
            if i is None:
                raise ValueError('Variable "%s" not found. Check var_names.' % q)
            idx.append(i)
    else:                                               # sensible defaults
        idx = [i for i in (find_var('potentialairtemp') if find_var('potentialairtemp') is not None
                           else find_var('airtemp'),
                           find_var('windspeed'), find_var('relativehum')) if i is not None]
        if not idx:
            idx = [0]
    uvars = [vnames[i] for i in idx]

    # ---------- read needed variables (cached per file + variable) ----------
    edt = os.path.splitext(_edx)[0] + '.EDT'
    if not os.path.exists(edt):
        edt = os.path.splitext(_edx)[0] + '.edt'
    n2, n3 = nx * ny, nx * ny * nz
    stamp = (os.path.getmtime(_edx), os.path.getmtime(edt))
    cache = sc.sticky.get('envimet_probe_cache')
    if not cache or cache.get('key') != (_edx, stamp):
        cache = {'key': (_edx, stamp)}
        sc.sticky['envimet_probe_cache'] = cache

    def block(vi):
        if vi not in cache:
            with open(edt, 'rb') as f:
                f.seek(vi * n3 * 4)
                buf = f.read(n3 * 4)
            a = array('f')
            try:
                a.frombytes(buf)
            except AttributeError:
                a.fromstring(buf)
            cache[vi] = a
        return cache[vi]

    data = [block(i) for i in idx]
    ref = data[0]                                       # building cells = NODATA

    def is_air(i, j, k):
        return ref[k * n2 + j * nx + i] > NODATA + 1

    def nearest_air(x, y, z, i0, j0, k0, rmax=4):
        best, bd = None, None
        for r in range(1, rmax + 1):
            rk = 0 if axis == 'z' else r                # stay on the slice
            rj = 0 if axis == 'y' else r
            ri = 0 if axis == 'x' else r
            for k in range(max(k0 - rk, 0), min(k0 + rk, nz - 1) + 1):
                for j in range(max(j0 - rj, 0), min(j0 + rj, ny - 1) + 1):
                    for i in range(max(i0 - ri, 0), min(i0 + ri, nx - 1) + 1):
                        if max(abs(i - i0), abs(j - j0), abs(k - k0)) != r or not is_air(i, j, k):
                            continue
                        d = (xc[i] - x) ** 2 + (yc[j] - y) ** 2 + (zc[k] - z) ** 2
                        if bd is None or d < bd:
                            best, bd = (i, j, k), d
            if best:
                return best
        return None

    # ---------- probe ----------
    vtree = DataTree[object]()
    fv, cl, ij, ds, lb, lv, tps = [], [], [], [], [], [], []
    short = [re.sub(r'\s*\(.*?\)', '', n) for n in uvars]
    units = [(re.search(r'\((.*?)\)', n).group(1) if re.search(r'\((.*?)\)', n) else '') for n in uvars]
    tbl = ['point,x,y,z,i,j,k,dist_m,' + ','.join('"%s"' % n for n in uvars)]
    fmt = '%.' + str(dec) + 'f'

    for n, p in enumerate(pts_in):
        x, y, z = p.X - o.X, p.Y - o.Y, p.Z - o.Z
        if axis == 'z':                                 # snap onto the chosen slice
            z = zc[k_in]
        elif axis == 'y':
            y = yc[k_in]
        elif axis == 'x':
            x = xc[k_in]
        tp = rg.Point3d(o.X + x, o.Y + y, o.Z + z)      # label point (on the slice)
        i, j, k = cell_of(xe, x), cell_of(ye, y), cell_of(ze, max(z, 0.0))
        if axis == 'z':
            k = k_in
        elif axis == 'y':
            j = k_in
        elif axis == 'x':
            i = k_in
        note = ''
        outside = not (xe[0] <= x <= xe[-1] and ye[0] <= y <= ye[-1] and z <= ze[-1])
        if outside:
            i = j = k = None
        elif not is_air(i, j, k):
            hit = nearest_air(x, y, z, i, j, k) if skip_bldg else None
            if hit:
                i, j, k = hit
                note = ' (nearest air cell)'
            else:
                i = j = k = None
        path = GH_Path(n)
        if i is None:
            vtree.AddRange([None] * len(idx), path)
            fv.append(None)
            cl.append(None)
            ij.append(None)
            ds.append(None)
            lb.append('P%d outside model domain' % n if outside else 'P%d inside building' % n)
            lv.append('')
            tps.append(tp)
            tbl.append('%d,%.2f,%.2f,%.2f,,,,,' % (n, p.X, p.Y, p.Z) + ','.join([''] * len(idx)))
            continue
        q = k * n2 + j * nx + i
        vals = [float(d[q]) if d[q] > NODATA + 1 else None for d in data]
        c = rg.Point3d(o.X + xc[i], o.Y + yc[j], o.Z + zc[k])
        vtree.AddRange(vals, path)
        fv.append(vals[0])
        cl.append(c)
        ij.append('%d,%d,%d' % (i, j, k))
        ds.append(tp.DistanceTo(c))
        lines = [('%s: %s %s' % (s, (fmt % v) if v is not None else '-', u)).rstrip()
                 for s, v, u in zip(short, vals, units)]
        lb.append('\n'.join(['P%d [%d,%d,%d]%s' % (n, i, j, k, note)] + lines))
        lv.append('\n'.join((('%s %s' % ((fmt % v) if v is not None else '-', u)).strip())
                            for v, u in zip(vals, units)))
        tps.append(tp)
        tbl.append('%d,%.2f,%.2f,%.2f,%d,%d,%d,%.2f,' % (n, p.X, p.Y, p.Z, i, j, k, ds[-1])
                   + ','.join((fmt % v) if v is not None else '' for v in vals))

    if csv_path:
        with io.open(csv_path, 'w', encoding='utf-8-sig') as f:   # Excel reads ° correctly
            f.write(u'\n'.join(tbl))

    print('%d points | variables: %s' % (len(pts_in), ', '.join(uvars)))
    return vnames, xc, yc, zc, uvars, vtree, fv, cl, ij, ds, lb, lv, tps, tbl


if run_on:
    (var_names, x_levels, y_levels, z_levels, used_vars, values, first_vals,
     cells, ijk, dist, labels, labels_val, tag_pts, table) = run()
else:
    print('Set _run to True to run.')