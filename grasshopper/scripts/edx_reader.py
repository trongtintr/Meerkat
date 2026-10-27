"""ENVI-met EDX/EDT reader -> mesh + values for LB Spatial Heatmap
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8).

Inputs (Type hint):
    _run    : bool  - True = read the file and build the result; False = do nothing:
                      the file is not read and all outputs are empty.
                      Connect a Boolean Toggle. Default True if the input is missing.
    _edx    : str   - path to the .EDX file (the .EDT file must share its name and folder)
    _var    : str   - variable name (or part of it, e.g. "air temp") or its index
    _axis_  : str   - section plane: "z" (plan, default), "x" (vertical section in the YZ plane),
                      "y" (vertical section in the XZ plane)
    _k      : int   - cell index along _axis_ (z: level, x: column i, y: row j)
    _origin_: Point3d (optional) - model origin in Rhino
    _decimals_: int (optional) - decimals for Min / Max text, default 2
    _wrap_  : int (optional) - max characters per line of the variable name in
                      legend_title, default 22 (longer names wrap onto several lines)
    _ascii_unit_: bool (optional) - True = write units without special characters
                      ("degC", "m3", "W/m2") for fonts that cannot show ° ² ³; default False
    _fill_  : bool (optional) - True = cells without data (buildings / no-data, -999) are
                      kept in the mesh and filled with _fill_value_; False = they are
                      removed (old behaviour). Default True
    _fill_value_: float (optional) - value used for empty cells, default 0
Outputs:
    var_names : list of variables in the file
    dims      : (nx, ny, nz)
    x_levels, y_levels, z_levels : cell-centre coordinates along each axis (m) - use to pick _k
    mesh      : grid mesh (empty cells filled with _fill_value_, or removed if _fill_ = False)
    values    : per-face values -> connect to LB Spatial Heatmap
    date      : simulation date of this output file, "YYYY-MM-DD"
    hour      : hour of this output file (int, 0-23) - e.g. for LB Analysis Period / titles
    time      : time "HH:MM" (hours and minutes, no seconds)
    datetime  : "YYYY-MM-DD HH:MM" (handy as a heatmap title)
    v_min, v_max : minimum / maximum of the REAL data (filled cells are ignored)
    filled    : list of bool per face, True = this face had no data and was filled
    unit      : unit of the variable, e.g. "°C"
    min_txt, max_txt : "28.31 °C" style text
    legend_title : multi-line title -> legend_title_ of LB Legend Parameters:
                       Variable name
                       ------------------
                       Date
                       Time
                       --------------------
                       Min: ...
                       Max: ...
    (read from <simulation_date>/<simulation_time> in the EDX header; if missing, from the
     ENVI-met file name, e.g. ..._AT_2025-06-21_14.00.01.EDX)
"""
import re
import os
from array import array
import Rhino.Geometry as rg

NODATA = -999.0


def opt(name, default=None):
    v = globals().get(name, default)
    return default if v is None else v


_run = bool(opt('_run', True))
_axis_ = opt('_axis_', 'z')
_k = opt('_k', 0)
_origin_ = opt('_origin_', None)
_decimals_ = int(opt('_decimals_', 2))
_wrap_ = max(8, int(opt('_wrap_', 22)))
_ascii_unit_ = bool(opt('_ascii_unit_', False))
_fill_ = bool(opt('_fill_', True))
_fill_value_ = float(opt('_fill_value_', 0.0))
TIPS_IN = {
    '_run': 'bool - True = read the file and build the result.\nFalse = do nothing: the file is not read and all outputs are empty.\nConnect a Boolean Toggle. Default True.',
    '_edx': 'str - full path to the ENVI-met .EDX file.\nThe .EDT file must have the same name and be in the same folder.',
    '_var': 'str - variable to read: full name, part of it (e.g. "air temp") or its index.\nSee the var_names output for the list.',
    '_axis_': 'str - section plane:\n"z" = plan (default)\n"x" = vertical section in the YZ plane\n"y" = vertical section in the XZ plane',
    '_k': 'int - cell index along _axis_ (z: level, x: column i, y: row j).\nUse x_levels / y_levels / z_levels to find the index of a height or position. Default 0.',
    '_origin_': 'Point3d (optional) - position of the ENVI-met model origin in Rhino. Default (0,0,0).',
    '_decimals_': 'int (optional) - decimals of the Min / Max texts. Default 2.',
    '_wrap_': 'int (optional) - max characters per line of the variable name in legend_title;\nlonger names wrap onto several lines. Default 22 (min 8).',
    '_ascii_unit_': 'bool (optional) - True = write units without special characters\n("degC", "m3", "W/m2") for fonts that cannot show deg / 2 / 3. Default False.',
    '_fill_': 'bool (optional) - True = cells without data (buildings / no-data, -999) are kept\nand get _fill_value_ (use the filled output to exclude them later).\nFalse = those cells are removed from the mesh. Default True.',
    '_fill_value_': 'float (optional) - value given to empty cells when _fill_ is True. Default 0.',
}
TIPS_OUT = {
    'var_names': 'List of all variables stored in the file (name + unit).',
    'dims': 'Grid size (nx, ny, nz).',
    'x_levels': 'Cell-centre x coordinates (m) - pick _k for _axis_ = "x".',
    'y_levels': 'Cell-centre y coordinates (m) - pick _k for _axis_ = "y".',
    'z_levels': 'Cell-centre heights (m) - pick _k for _axis_ = "z" (plan level).',
    'mesh': 'Grid mesh of the section, one face per ENVI-met cell\n-> _mesh of the Heatmap component.',
    'values': 'One value per mesh face -> _values of the Heatmap component (List Access).',
    'date': 'Simulation date of this output file, "YYYY-MM-DD".',
    'hour': 'Hour of this output file (int, 0-23).',
    'time': 'Time of this output file, "HH:MM".',
    'datetime': '"YYYY-MM-DD HH:MM" - handy as global title.',
    'v_min': 'Minimum of the REAL data (filled cells ignored) -> _vmin_ of the Heatmap.',
    'v_max': 'Maximum of the REAL data (filled cells ignored) -> _vmax_ of the Heatmap.',
    'unit': u'Unit of the variable, e.g. "\u00b0C".',
    'min_txt': u'Minimum as text with unit, e.g. "28.31 \u00b0C".',
    'max_txt': u'Maximum as text with unit, e.g. "36.02 \u00b0C".',
    'legend_title': 'Multi-line legend title (variable / date / time / Min / Max)\n-> _legend_title_ of the Heatmap.',
    'filled': 'One bool per face: True = the cell had no data and was filled\n-> _filled_ of the Heatmap (List Access), so buildings stay out of smoothing / contours.',
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


OUTS = ('var_names', 'dims', 'x_levels', 'y_levels', 'z_levels', 'mesh', 'values',
        'date', 'hour', 'time', 'datetime', 'v_min', 'v_max', 'unit', 'min_txt', 'max_txt',
        'legend_title', 'filled')


def tag(txt, name):
    m = re.search(r'<%s>(.*?)</%s>' % (name, name), txt, re.S | re.I)
    return m.group(1).strip() if m else None


def floats(s):
    return [float(v) for v in s.replace('\n', ',').split(',') if v.strip()]


def edges(spacing):
    e = [0.0]
    for d in spacing:
        e.append(e[-1] + d)
    return e


def centers(e):
    return [(e[i] + e[i + 1]) / 2.0 for i in range(len(e) - 1)]


def norm(s):
    # strip special characters (°, ³, spaces...) so matching is encoding-independent
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


def ascii_unit(u):
    for a, b in ((u'\u00b0C', 'degC'), (u'\u00b0', 'deg'), (u'\u00b2', '2'),
                 (u'\u00b3', '3'), (u'\u00b5', 'u')):
        u = u.replace(a, b)
    return u


def wrap(text, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines or ['']


def parse_datetime(txt, path):
    """-> (date 'YYYY-MM-DD', hour int, time 'HH:MM'); None where not found"""
    d_raw, t_raw = tag(txt, 'simulation_date'), tag(txt, 'simulation_time')
    name = os.path.basename(path)
    if not d_raw:                                        # fallback: file name
        m = re.search(r'(\d{4})[-_.](\d{2})[-_.](\d{2})', name)
        d_raw = '%s-%s-%s' % m.groups() if m else None
    if not t_raw:
        m = re.search(r'\d{4}[-_.]\d{2}[-_.]\d{2}[_ ](\d{2})[.:]?(\d{2})(?:[.:](\d{2}))?', name)
        t_raw = ':'.join(g or '00' for g in m.groups()) if m else None
    date = None
    if d_raw:
        n = re.findall(r'\d+', d_raw)
        if len(n) >= 3:
            if len(n[0]) == 4:                           # YYYY-MM-DD
                y, mo, d = n[0], n[1], n[2]
            else:                                        # DD.MM.YYYY (ENVI-met default)
                d, mo, y = n[0], n[1], n[2]
            date = '%04d-%02d-%02d' % (int(y), int(mo), int(d))
    hour = time = None
    if t_raw:
        n = (re.findall(r'\d+', t_raw) + ['0', '0', '0'])[:3]
        h, mi = int(n[0]), int(n[1])
        hour, time = h, '%02d:%02d' % (h, mi)
    return date, hour, time


def build():
    # ---- 1. Read the EDX header
    with open(_edx, 'rb') as f:
        txt = decode_text(f.read())

    nx = int(tag(txt, 'nr_xdata'))
    ny = int(tag(txt, 'nr_ydata'))
    nz = int(tag(txt, 'nr_zdata'))
    xe = edges(floats(tag(txt, 'spacing_x')))
    ye = edges(floats(tag(txt, 'spacing_y')))
    ze = edges(floats(tag(txt, 'spacing_z')))
    var_names = [s.strip() for s in tag(txt, 'name_variables').split(',') if s.strip()]
    dims = (nx, ny, nz)
    x_levels, y_levels, z_levels = centers(xe), centers(ye), centers(ze)
    date, hour, time = parse_datetime(txt, _edx)
    datetime = ('%s %s' % (date or '', time or '')).strip() or None

    # ---- 2. Select variable, axis and index
    try:
        vi = int(_var)
    except (ValueError, TypeError):
        key = norm(_var)
        hits = [i for i, n in enumerate(var_names) if norm(n) == key]
        if not hits:
            hits = [i for i, n in enumerate(var_names) if key in norm(n)]
        if not hits:
            raise ValueError('Variable "%s" not found. See the var_names output.' % _var)
        vi = hits[0]

    axis = (_axis_ or 'z').strip().lower()
    k = int(_k) if _k is not None else 0
    limit = {'x': nx, 'y': ny, 'z': nz}[axis]
    if not 0 <= k < limit:
        raise ValueError('_k must be in the range 0..%d for axis %s' % (limit - 1, axis))

    # ---- 3. Read data from EDT (float32 LE, order: variable -> z -> y -> x)
    n2 = nx * ny
    edt = os.path.splitext(_edx)[0] + '.EDT'
    if not os.path.exists(edt):
        edt = os.path.splitext(_edx)[0] + '.edt'


    def read(offset, count):
        with open(edt, 'rb') as f:
            f.seek(offset * 4)
            buf = f.read(count * 4)
        a = array('f')
        try:
            a.frombytes(buf)
        except AttributeError:
            a.fromstring(buf)
        return a


    if axis == 'z':
        data = read((vi * nz + k) * n2, n2)   # read a single level only
        get = lambda i, j, kk: data[j * nx + i]
    else:
        data = read(vi * nz * n2, nz * n2)    # read the variable's full 3D block
        get = lambda i, j, kk: data[kk * n2 + j * nx + i]

    # ---- 4. Build the mesh
    o = _origin_ if _origin_ else rg.Point3d(0, 0, 0)
    mesh = rg.Mesh()
    values = []
    filled = []


    def quad(p0, p1, p2, p3, v):
        if v <= NODATA + 1:                       # empty cell (building / no data)
            if not _fill_:
                return
            v = _fill_value_
            filled.append(True)
        else:
            filled.append(False)
        a = mesh.Vertices.Count
        for p in (p0, p1, p2, p3):
            mesh.Vertices.Add(o.X + p[0], o.Y + p[1], o.Z + p[2])
        mesh.Faces.AddFace(a, a + 1, a + 2, a + 3)
        values.append(float(v))


    if axis == 'z':        # plan at level k
        z = z_levels[k]
        for j in range(ny):
            for i in range(nx):
                quad((xe[i], ye[j], z), (xe[i + 1], ye[j], z),
                     (xe[i + 1], ye[j + 1], z), (xe[i], ye[j + 1], z), get(i, j, k))

    elif axis == 'x':      # YZ section at column i = k
        x = x_levels[k]
        for kk in range(nz):
            for j in range(ny):
                quad((x, ye[j], ze[kk]), (x, ye[j + 1], ze[kk]),
                     (x, ye[j + 1], ze[kk + 1]), (x, ye[j], ze[kk + 1]), get(k, j, kk))

    else:                  # 'y' - XZ section at row j = k
        y = y_levels[k]
        for kk in range(nz):
            for i in range(nx):
                quad((xe[i], y, ze[kk]), (xe[i + 1], y, ze[kk]),
                     (xe[i + 1], y, ze[kk + 1]), (xe[i], y, ze[kk + 1]), get(i, k, kk))

    mesh.Normals.ComputeNormals()
    mesh.Compact()

    # ---- 5. Min / Max + legend title
    name = var_names[vi]
    um = re.search(r'\(([^()]*)\)\s*$', name)
    unit = um.group(1).strip() if um else ''
    if _ascii_unit_:
        unit = ascii_unit(unit)
    fmt = '%.' + str(_decimals_) + 'f'

    def with_unit(v):
        if v is None:
            return '-'
        return (fmt % v + (' ' + unit if unit else '')).strip()

    real = [v for v, f in zip(values, filled) if not f]   # ignore filled cells
    v_min = min(real) if real else None
    v_max = max(real) if real else None
    min_txt, max_txt = with_unit(v_min), with_unit(v_max)
    name_lines = wrap(name if not _ascii_unit_ else ascii_unit(name), _wrap_)
    body = [date or '-', time or '-', 'Min: ' + min_txt, 'Max: ' + max_txt]
    bar = '-' * max(len(l) for l in name_lines + body)   # same length for both bars
    legend_title = '\n'.join(name_lines + [bar] + body[:2] + [bar] + body[2:] + [' '])  # blank line below
    print('Variable #%d: %s | axis %s, index %d | %s' % (vi, var_names[vi], axis, k,
                                                          datetime or 'date/time not found'))
    return dict(var_names=var_names, dims=dims, x_levels=x_levels, y_levels=y_levels,
                z_levels=z_levels, mesh=mesh, values=values,
                date=date, hour=hour, time=time, datetime=datetime,
                v_min=v_min, v_max=v_max, unit=unit, min_txt=min_txt, max_txt=max_txt,
                legend_title=legend_title, filled=filled)

set_tooltips(TIPS_IN, TIPS_OUT,
             'Meerkat - reads an ENVI-met EDX/EDT output file and builds a section mesh + values')
if _run:
    result = build()
else:
    print('_run is False - nothing read, outputs empty')
    result = dict((n, None) for n in OUTS)

var_names, dims = result['var_names'], result['dims']
x_levels, y_levels, z_levels = result['x_levels'], result['y_levels'], result['z_levels']
mesh, values = result['mesh'], result['values']
date, hour, time, datetime = result['date'], result['hour'], result['time'], result['datetime']
v_min, v_max, unit = result['v_min'], result['v_max'], result['unit']
min_txt, max_txt, legend_title = result['min_txt'], result['max_txt'], result['legend_title']
filled = result['filled']