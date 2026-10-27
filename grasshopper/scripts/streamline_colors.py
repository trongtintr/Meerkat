"""Colour streamlines by wind speed (ENVI-met EDX/EDT) for Grasshopper
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8).

Takes the `curves` output of envimet_wind_3d.py (or any curves inside the model),
samples wind speed from the ENVI-met file at every curve vertex and returns
smooth vertex-coloured tubes plus a legend. Shares the data cache with
envimet_wind_3d.py, so the EDT file is not read twice.

Performance notes (v2):
  - curve vertices are read as one block copy per curve (no per-point .NET calls)
  - trilinear lookup uses direct index on uniform grids (bisect only for telescoping z)
  - colours come from a 256-step lookup table (no Color object per vertex)
  - the tube mesh is handed to Rhino in one block copy (vertices, faces, colours)
  - segments (Line objects) are only built when that output is connected;
    seg_colors / seg_speeds only when one of them is connected
  - the building mask of the shared data cache is built with one comprehension

Inputs (only _curves and _edx are required):
    _run        : bool         - True = read the file and build; False = do nothing (file not
                                 read, all outputs empty). Boolean Toggle; default True
    _curves     : list Curve   - streamlines (LIST ACCESS)
    _edx        : str          - path to the .EDX file (.EDT with same name, same folder)
    _vmin_      : float        - speed at the bottom of the colour scale (default: data min)
    _vmax_      : float        - speed at the top of the colour scale (default: data max);
                                 fix _vmin_/_vmax_ when comparing scenarios
    _plane_     : str          - "x" / "y" / "z": ignore the velocity component normal to
                                 that slice (use for 2D-slice streamlines); empty = 3D speed
    _colors_    : list Colour  - custom gradient (LIST ACCESS); default = Ladybug palette
    _radius_    : float        - tube radius in m (default 0.15)
    _sides_     : int          - tube sides (default 6)
    _legend_pt_ : Point3d      - base point of the legend (default: right of the curves)
    _legend_scale_: float      - size multiplier for the whole legend (bar + text), default 1.0
    _legend_h_  : float        - legend bar height in m (overrides the automatic height)
    _legend_w_  : float        - legend bar width in m (default: height x 0.075)
    _legend_n_  : int          - number of value labels on the legend (default 6)
    _title_xz_  : bool         - True = legend (bar, value labels, title) stands upright in the
                                 vertical XZ plane; legend_pts then become PLANES. Default False
    _origin_    : Point3d      - model origin in Rhino (same as in envimet_wind_3d.py)
Outputs:
    mesh        : vertex-coloured tube mesh (shows coloured in the Grasshopper preview;
                  bake it to keep the colours)
    segments    : line segments            } for Custom Preview / Gradient workflows
    seg_colors  : colour of each segment   }
    seg_speeds  : speed of each segment (m/s)
    legend      : vertex-coloured legend bar mesh
    legend_pts, legend_txt : label points and texts -> Text Tag 3D component
                  (planes in the XZ plane when _title_xz_ is True)
    text_size   : suggested text height -> Size input of Text Tag 3D (scales with the legend)
    v_range     : (vmin, vmax) used
"""
import re
import os
import math
import time
import bisect
from array import array
import Rhino.Geometry as rg
import scriptcontext as sc
import System
import System.Drawing as sd
from System.Runtime.InteropServices import GCHandle, GCHandleType, Marshal

NODATA = -999.0
LB_COLORS = [(75, 107, 169), (115, 147, 202), (170, 200, 247), (193, 213, 208),
             (245, 239, 103), (252, 230, 74), (239, 156, 21), (234, 123, 0),
             (234, 74, 0), (234, 38, 0)]


TIPS_IN = {
    '_run': 'bool - True = read the file and build; False = do nothing\n'
            '(file not read, all outputs empty). Connect a Boolean Toggle. Default True.',
    '_curves': 'list Curve - streamlines to colour, e.g. curves output of envimet_wind3d\n'
               '(any curves inside the model work). Set this input to LIST ACCESS.',
    '_edx': 'str - full path to the ENVI-met ATMOSPHERE .EDX file (Flow u / v / w).\n'
            'The .EDT file must have the same name and folder. Shares the data cache with envimet_wind3d.',
    '_vmin_': 'float (optional) - speed (m/s) at the bottom of the colour scale. Default: data minimum.\n'
              'Fix _vmin_ / _vmax_ when comparing scenarios.',
    '_vmax_': 'float (optional) - speed (m/s) at the top of the colour scale. Default: data maximum.',
    '_plane_': 'str (optional) - "x" / "y" / "z": ignore the velocity component normal to that slice\n'
               '(use the same value as for 2D-slice streamlines); empty = full 3D speed.',
    '_colors_': 'list Colour (optional, LIST ACCESS) - custom gradient from low to high.\n'
                'Default: Ladybug palette.',
    '_radius_': 'float (optional) - tube radius (m). Default 0.15.',
    '_sides_': 'int (optional) - number of tube sides (min 3). Default 6.',
    '_legend_pt_': 'Point3d (optional) - base point (bottom-left) of the legend. Default: right of the curves.',
    '_legend_scale_': 'float (optional) - size multiplier for the whole legend (bar + text). Default 1.0.',
    '_legend_h_': 'float (optional) - legend bar height (m); overrides the automatic height\n'
                  '(0.4 x bounding-box diagonal of the curves).',
    '_legend_w_': 'float (optional) - legend bar width (m). Default: bar height x 0.075.',
    '_legend_n_': 'int (optional) - number of value labels on the legend (min 2). Default 6.',
    '_title_xz_': 'bool (optional) - True = the legend (bar, value labels, title) stands upright in\n'
                  'the vertical XZ plane (text faces -Y, reads along +X, up = +Z), e.g. for sections or\n'
                  '3D views. legend_pts then output PLANES - connect them to the Location of Text Tag 3D\n'
                  'as before. Default False (flat in XY).',
    '_origin_': 'Point3d (optional) - position of the ENVI-met model origin in Rhino\n'
                '(use the same value as in envimet_wind3d). Default (0,0,0).',
}
TIPS_OUT = {
    'mesh': 'Vertex-coloured tube mesh with a smooth speed gradient. Coloured in the\n'
            'Grasshopper preview; bake it to keep the colours.',
    'segments': 'Line segments between curve vertices -> Custom Preview / gradient workflows.\n'
                'Built only when this output is connected (saves time).',
    'seg_colors': 'Colour of each segment (same order as segments).',
    'seg_speeds': 'Wind speed (m/s) of each segment (mean of its two end points).',
    'legend': 'Vertex-coloured legend bar mesh.',
    'legend_pts': 'Positions of the legend labels + title -> Location of Text Tag 3D.\n'
                  'Points (flat XY) or planes (upright XZ, _title_xz_ = True).',
    'legend_txt': 'Legend label texts + title "Wind speed (m/s)" -> Text of Text Tag 3D.',
    'text_size': 'Suggested text height (scales with the legend) -> Size of Text Tag 3D.',
    'v_range': '(vmin, vmax) actually used for the colours.',
}


def set_tooltips(tips_in, tips_out, comp_desc=None):
    """write the tooltip (Description) of every input / output of this component.
    Matched by NickName; only changed when different, so it costs nothing after the first run"""
    try:
        comp = ghenv.Component  # noqa: F821
    except NameError:
        return
    try:
        if comp_desc and comp.Description != comp_desc:
            comp.Description = comp_desc
        for plist, tips in ((comp.Params.Input, tips_in), (comp.Params.Output, tips_out)):
            for p in plist:
                t = tips.get(p.NickName) or tips.get(p.Name)
                if t and p.Description != t:
                    p.Description = t
    except Exception as ex:                              # tooltips must never break the solve
        print('tooltips not set: %s' % ex)


set_tooltips(TIPS_IN, TIPS_OUT,
             'Meerkat - colour streamlines by ENVI-met wind speed: smooth coloured tubes + legend')


def opt(name, default=None):
    v = globals().get(name, default)
    return default if v is None or v == [] else v


run = bool(opt('_run', True))
curves_in = opt('_curves', [])
if not isinstance(curves_in, (list, tuple)):
    curves_in = [curves_in]
curves_in = [c for c in curves_in if c is not None]
vmin_in, vmax_in = opt('_vmin_', None), opt('_vmax_', None)
plane = str(opt('_plane_', '')).strip().lower()
cols_in = opt('_colors_', None)
radius = float(opt('_radius_', 0.15))
sides = max(3, int(opt('_sides_', 6)))
legend_pt = opt('_legend_pt_', None)
legend_scale = float(opt('_legend_scale_', 1.0))
legend_h_in = opt('_legend_h_', None)
legend_w_in = opt('_legend_w_', None)
legend_n = max(2, int(opt('_legend_n_', 6)))
_xz = opt('_title_xz_', False)
title_xz = (_xz.strip().lower() not in ('false', '0', 'no', 'off', '')) if isinstance(_xz, str) \
    else bool(_xz)
o = opt('_origin_', rg.Point3d(0, 0, 0))
ox, oy, oz = o.X, o.Y, o.Z
if run and not curves_in:
    raise ValueError('Connect _curves (set the input to List Access).')

palette = [(c.R, c.G, c.B) for c in cols_in] if cols_in else LB_COLORS
if not isinstance(palette, list) or len(palette) < 2:
    palette = LB_COLORS


# =============== 0. BULK .NET HELPERS ===============
def _pin_copy_to(arr, flat, net_type):
    src = System.Array[net_type](flat)
    h = GCHandle.Alloc(arr, GCHandleType.Pinned)
    try:
        Marshal.Copy(src, 0, h.AddrOfPinnedObject(), len(flat))
    finally:
        h.Free()


def point_array(flat):
    """flat [x, y, z, ...] -> Point3d[] with one memory copy"""
    n = len(flat) // 3
    arr = System.Array.CreateInstance(rg.Point3d, n)
    if n:
        try:
            _pin_copy_to(arr, flat, System.Double)
        except Exception:
            for i in range(n):
                arr[i] = rg.Point3d(flat[3 * i], flat[3 * i + 1], flat[3 * i + 2])
    return arr


def face_array(flat):
    """flat [a, b, c, d, ...] -> MeshFace[] with one memory copy"""
    n = len(flat) // 4
    arr = System.Array.CreateInstance(rg.MeshFace, n)
    if n:
        try:
            _pin_copy_to(arr, flat, System.Int32)
        except Exception:
            for i in range(n):
                arr[i] = rg.MeshFace(*flat[4 * i:4 * i + 4])
    return arr


def points_xyz(arr):
    """Point3d[] -> flat Python list [x, y, z, ...] with one memory copy"""
    n = arr.Length
    if not n:
        return []
    try:
        dbl = System.Array.CreateInstance(System.Double, 3 * n)
        h = GCHandle.Alloc(arr, GCHandleType.Pinned)
        try:
            Marshal.Copy(h.AddrOfPinnedObject(), dbl, 0, 3 * n)
        finally:
            h.Free()
        return list(dbl)
    except Exception:
        out = []
        for p in arr:
            out.extend((p.X, p.Y, p.Z))
        return out


def output_wanted(*names):
    """True if one of these outputs is connected (or when not running in Grasshopper)"""
    try:
        outs = ghenv.Component.Params.Output  # noqa: F821
    except NameError:
        return True
    for p in outs:
        if p.NickName in names and p.Recipients.Count > 0:
            return True
    return False


# =============== 1. LOAD DATA (shared cache with envimet_wind_3d.py) ===============
def tag(txt, name):
    m = re.search(r'<%s>(.*?)</%s>' % (name, name), txt, re.S | re.I)
    return m.group(1).strip() if m else None


def floats(s):
    return [float(v) for v in s.replace('\n', ',').split(',') if v.strip()]


def centers(sp):
    c, e = [], 0.0
    for d in sp:
        c.append(e + d / 2.0)
        e += d
    return c


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def read(path, offset, count):
    with open(path, 'rb') as f:
        f.seek(offset * 4)
        buf = f.read(count * 4)
    a = array('f')
    try:
        a.frombytes(buf)
    except AttributeError:
        a.fromstring(buf)
    return a


def load(edx, edt):
    with open(edx, 'rb') as f:
        txt = f.read().decode('latin-1')
    d = {}
    d['nx'], d['ny'], d['nz'] = [int(tag(txt, t)) for t in ('nr_xdata', 'nr_ydata', 'nr_zdata')]
    d['dxs'], d['dys'], d['dzs'] = [floats(tag(txt, t)) for t in ('spacing_x', 'spacing_y', 'spacing_z')]
    names = [s.strip() for s in tag(txt, 'name_variables').split(',') if s.strip()]

    def find(prefix):
        for i, n in enumerate(names):
            if norm(n).startswith(prefix):
                return i
        raise ValueError('Variable "%s" not found. Is this an atmosphere output?' % prefix)

    n3 = d['nx'] * d['ny'] * d['nz']
    U = read(edt, find('flowu') * n3, n3)
    V = read(edt, find('flowv') * n3, n3)
    W = read(edt, find('floww') * n3, n3)
    lim = NODATA + 1                                    # 1 = building / no-data
    S = bytearray([1 if (a <= lim or b <= lim or c <= lim) else 0 for a, b, c in zip(U, V, W)])
    d['U'], d['V'], d['W'], d['S'] = U, V, W, S
    return d


def make_locator(cs, sp):
    """coordinate -> (index i, fraction t), clamped to the grid (same as the v1 clamp_loc)"""
    n = len(cs)
    c0, c1 = cs[0], cs[-1]
    if max(sp) - min(sp) < 1e-6:                        # uniform grid: direct index
        inv = 1.0 / sp[0]
        last = n - 2

        def loc(x):
            if x <= c0:
                return 0, 0.0
            if x >= c1:
                return last, 1.0
            f = (x - c0) * inv
            i = int(f)
            if i > last:
                i = last
            return i, f - i
    else:                                               # non-uniform (telescoping z): bisect
        def loc(x):
            if x <= c0:
                return 0, 0.0
            if x >= c1:
                return n - 2, 1.0
            i = min(max(bisect.bisect_right(cs, x) - 1, 0), n - 2)
            return i, (x - cs[i]) / (cs[i + 1] - cs[i])
    return loc


def make_lut(pal):
    n = len(pal) - 1
    lut = []
    for s in range(256):
        t = s / 255.0 * n
        i = min(int(t), n - 1)
        f = t - i
        a, b = pal[i], pal[i + 1]
        lut.append(sd.Color.FromArgb(int(a[0] + (b[0] - a[0]) * f),
                                     int(a[1] + (b[1] - a[1]) * f),
                                     int(a[2] + (b[2] - a[2]) * f)))
    return lut


def build():
    t0 = time.time()
    edt_path = os.path.splitext(_edx)[0] + '.EDT'
    if not os.path.exists(edt_path):
        edt_path = os.path.splitext(_edx)[0] + '.edt'
    key = (_edx, os.path.getmtime(_edx), os.path.getmtime(edt_path))
    cache = sc.sticky.get('envimet_wind3d_cache')
    if not cache or cache.get('key') != key:
        cache = load(_edx, edt_path)
        cache['key'] = key
        sc.sticky['envimet_wind3d_cache'] = cache
    t_load = time.time() - t0

    nx, ny = cache['nx'], cache['ny']
    U, V, W, S = cache['U'], cache['V'], cache['W'], cache['S']
    dxs, dys, dzs = cache['dxs'], cache['dys'], cache['dzs']
    xc, yc, zc = centers(dxs), centers(dys), centers(dzs)
    n2 = nx * ny
    locx, locy, locz = make_locator(xc, dxs), make_locator(yc, dys), make_locator(zc, dzs)
    keep_u, keep_v, keep_w = plane != 'x', plane != 'y', plane != 'z'
    sqrt = math.sqrt

    # =============== 2. SPEED AT A POINT (trilinear, skips building cells) ===============
    def speed_at(x, y, z):
        i, tx = locx(x - ox)
        j, ty = locy(y - oy)
        k, tz = locz(z - oz)
        b = k * n2 + j * nx + i
        sx, sy, sz = 1.0 - tx, 1.0 - ty, 1.0 - tz
        u = v = w = ws = 0.0
        for q, wt in ((b, sx * sy * sz), (b + 1, tx * sy * sz),
                      (b + nx, sx * ty * sz), (b + nx + 1, tx * ty * sz),
                      (b + n2, sx * sy * tz), (b + n2 + 1, tx * sy * tz),
                      (b + n2 + nx, sx * ty * tz), (b + n2 + nx + 1, tx * ty * tz)):
            if wt > 0.0 and not S[q]:                   # renormalise over valid cells
                u += wt * U[q]
                v += wt * V[q]
                w += wt * W[q]
                ws += wt
        if ws < 1e-9:
            return None
        s2 = 0.0
        if keep_u:
            s2 += u * u
        if keep_v:
            s2 += v * v
        if keep_w:
            s2 += w * w
        return sqrt(s2) / ws

    # =============== 3. CURVE VERTICES + SPEEDS ===============
    step_len = max(0.5, radius * 3)

    def curve_xyz(c):
        try:
            ok, pl = c.TryGetPolyline()
        except Exception:
            ok, pl = False, None
        if ok and pl is not None and pl.Count >= 2:
            return points_xyz(pl.ToArray())
        ts = c.DivideByLength(step_len, True)
        pts = [c.PointAt(t) for t in ts] if ts else [c.PointAtStart, c.PointAtEnd]
        out = []
        for p in pts:
            out.extend((p.X, p.Y, p.Z))
        return out

    lines = []                                          # (flat xyz, speeds) per curve
    xmin = ymin = zmin = 1e300
    xmax = ymax = zmax = -1e300
    for c in curves_in:
        xyz = curve_xyz(c)
        n = len(xyz) // 3
        if n < 1:
            continue
        spd = [speed_at(xyz[3 * m], xyz[3 * m + 1], xyz[3 * m + 2]) for m in range(n)]
        last = next((s for s in spd if s is not None), 0.0)   # fill gaps (wall-adjacent points)
        filled = []
        for s in spd:
            if s is not None:
                last = s
            filled.append(last)
        lines.append((xyz, filled))
        xs, ys, zs = xyz[0::3], xyz[1::3], xyz[2::3]
        xmin, xmax = min(xmin, min(xs)), max(xmax, max(xs))
        ymin, ymax = min(ymin, min(ys)), max(ymax, max(ys))
        zmin, zmax = min(zmin, min(zs)), max(zmax, max(zs))
    if not lines:
        raise ValueError('No usable curves.')

    all_s = [s for _, ss in lines for s in ss]
    vmin = float(vmin_in) if vmin_in is not None else min(all_s)
    vmax = float(vmax_in) if vmax_in is not None else max(all_s)
    if vmax - vmin < 1e-9:
        vmax = vmin + 1e-6
    v_range = (vmin, vmax)
    lut = make_lut(palette)
    span = 255.0 / (vmax - vmin)

    def color(s):
        q = int((s - vmin) * span + 0.5)
        return lut[0 if q < 0 else (255 if q > 255 else q)]

    # =============== 4. COLOURED TUBES (vertex colours, smooth gradient) ===============
    angles = [(math.cos(2 * math.pi * s / sides), math.sin(2 * math.pi * s / sides))
              for s in range(sides)]
    ring_faces = [(s, (s + 1) % sides) for s in range(sides)]
    vflat, fflat, vcols = [], [], []
    vext, fext, cext = vflat.extend, fflat.extend, vcols.extend
    want_lines = output_wanted('segments')              # Line objects are the costly part
    want_seg = want_lines or output_wanted('seg_colors', 'seg_speeds')
    segments, seg_colors, seg_speeds = [], [], []
    Line = rg.Line

    for xyz, spd in lines:
        n = len(xyz) // 3
        if n < 2:
            continue
        base = len(vflat) // 3
        rings = 0
        for m in range(n):
            a3, b3 = 3 * max(m - 1, 0), 3 * min(m + 1, n - 1)   # central-difference tangent
            dx, dy, dz = xyz[b3] - xyz[a3], xyz[b3 + 1] - xyz[a3 + 1], xyz[b3 + 2] - xyz[a3 + 2]
            l = sqrt(dx * dx + dy * dy + dz * dz)
            if l < 1e-9:
                continue
            dx, dy, dz = dx / l, dy / l, dz / l
            if abs(dz) < 0.9:                           # frame: e1 = d x Z (or d x X)
                e1x, e1y, e1z = dy, -dx, 0.0
            else:
                e1x, e1y, e1z = 0.0, dz, -dy
            le = sqrt(e1x * e1x + e1y * e1y + e1z * e1z)
            e1x, e1y, e1z = e1x / le, e1y / le, e1z / le
            e2x, e2y, e2z = dy * e1z - dz * e1y, dz * e1x - dx * e1z, dx * e1y - dy * e1x
            px, py, pz = xyz[3 * m], xyz[3 * m + 1], xyz[3 * m + 2]
            for ca, sa in angles:
                vext((px + radius * (e1x * ca + e2x * sa),
                      py + radius * (e1y * ca + e2y * sa),
                      pz + radius * (e1z * ca + e2z * sa)))
            cext([color(spd[m])] * sides)
            rings += 1
        for r in range(rings - 1):
            a0, a1 = base + r * sides, base + (r + 1) * sides
            for s, s1 in ring_faces:
                fext((a0 + s, a0 + s1, a1 + s1, a1 + s))
        if want_seg:
            for m in range(n - 1):
                sv = 0.5 * (spd[m] + spd[m + 1])
                if want_lines:
                    q = 3 * m
                    segments.append(Line(xyz[q], xyz[q + 1], xyz[q + 2],
                                         xyz[q + 3], xyz[q + 4], xyz[q + 5]))
                seg_colors.append(color(sv))
                seg_speeds.append(sv)

    mesh = rg.Mesh()
    mesh.Vertices.AddVertices(point_array(vflat))
    mesh.Faces.AddFaces(face_array(fflat))
    mesh.VertexColors.SetColors(System.Array[sd.Color](vcols))
    mesh.Normals.ComputeNormals()

    # =============== 5. LEGEND ===============
    bb = rg.BoundingBox(xmin, ymin, zmin, xmax, ymax, zmax)
    diag = bb.Diagonal.Length or 1.0
    h = float(legend_h_in) if legend_h_in else 0.4 * diag
    h *= legend_scale
    w = float(legend_w_in) * legend_scale if legend_w_in else 0.075 * h
    text_size = 0.5 * w
    lp = legend_pt if legend_pt else rg.Point3d(bb.Max.X + 0.05 * diag, bb.Min.Y, bb.Min.Z)

    def P(u, v):
        """legend coordinates (u = right, v = up) -> world (x, y, z), flat XY or upright XZ"""
        if title_xz:
            return (lp.X + u, lp.Y, lp.Z + v)
        return (lp.X + u, lp.Y + v, lp.Z)

    nseg = 20
    lv, lf, lc = [], [], []
    for s in range(nseg + 1):
        y = h * s / float(nseg)
        col = color(vmin + (vmax - vmin) * s / float(nseg))
        lv.extend(P(0.0, y) + P(w, y))
        lc.extend((col, col))
        if s:
            a = 2 * (s - 1)
            lf.extend((a, a + 1, a + 3, a + 2))
    legend = rg.Mesh()
    legend.Vertices.AddVertices(point_array(lv))
    legend.Faces.AddFaces(face_array(lf))
    legend.VertexColors.SetColors(System.Array[sd.Color](lc))
    legend.Normals.ComputeNormals()
    legend_pts, legend_txt = [], []
    nl = legend_n - 1
    for s in range(legend_n):
        legend_pts.append(rg.Point3d(*P(1.5 * w, h * s / float(nl))))
        legend_txt.append('%.2f' % (vmin + (vmax - vmin) * s / float(nl)))
    legend_pts.append(rg.Point3d(*P(0.0, h + 1.5 * text_size)))
    legend_txt.append('Wind speed (m/s)')
    if title_xz:                                        # Text Tag 3D needs planes to stand up
        legend_pts = [rg.Plane(p, rg.Vector3d.XAxis, rg.Vector3d.ZAxis) for p in legend_pts]

    nsegs = sum(len(x) // 3 - 1 for x, _ in lines)
    print('%d curves | %d segments%s | speed %.2f-%.2f m/s | load %.2fs | total %.2fs'
          % (len(lines), nsegs, '' if want_seg else ' (segment outputs not connected: skipped)',
             vmin, vmax, t_load, time.time() - t0))
    return dict(mesh=mesh, segments=segments, seg_colors=seg_colors, seg_speeds=seg_speeds,
                legend=legend, legend_pts=legend_pts, legend_txt=legend_txt, v_range=v_range,
                text_size=text_size)


OUTS = ('mesh', 'segments', 'seg_colors', 'seg_speeds', 'legend', 'legend_pts',
        'legend_txt', 'v_range', 'text_size')
if run:
    result = build()
else:
    print('_run is False - nothing read, outputs empty')
    result = dict((n, None) for n in OUTS)
mesh, segments, seg_colors = result['mesh'], result['segments'], result['seg_colors']
seg_speeds, legend, v_range = result['seg_speeds'], result['legend'], result['v_range']
legend_pts, legend_txt = result['legend_pts'], result['legend_txt']
text_size = result['text_size']