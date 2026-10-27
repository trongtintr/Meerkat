"""ENVI-met EDX/EDT -> wind vectors (arrows) for Grasshopper / Ladybug
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8).
Reads the "Flow u", "Flow v", "Flow w" variables (m/s) from the atmosphere output.

Inputs (Type hint):
    _run    : bool    - set to True to run (connect a Boolean Toggle / Button)
    _edx    : str     - path to the .EDX file (the .EDT file must share its name and folder)
    _axis_  : str     - "z" (plan, default), "x" (YZ section), "y" (XZ section)
    _k      : int     - cell index along _axis_ (z: level, x: column i, y: row j)
    _step_  : int     - sample every n cells (default 2) so arrows are not too dense
    _scale_ : float   - arrow length factor (default 1.0)
    _vmax_  : float   - reference speed (m/s). Fix this value when comparing scenarios;
                        leave empty = use the slice maximum
    _origin_: Point3d - model origin in Rhino (optional)
Outputs:
    x_levels, y_levels, z_levels : cell-centre coordinates (m) - use to pick _k
    arrows  : arrow mesh -> connect to _mesh of LB Spatial Heatmap
    values  : wind speed per face -> connect to _values of LB Spatial Heatmap
    points  : arrow anchor points    } use with Grasshopper's
    vectors : wind vectors (m/s)     } Vector Display component if desired
    speeds  : speed at each point (m/s)
"""
import re
import os
import math
from array import array
import Rhino.Geometry as rg

NODATA = -999.0

TIPS_IN = {
    '_run': 'bool - True = read the file and build the arrows.\n'
            'False = do nothing, all outputs empty (default). Connect a Boolean Toggle / Button.',
    '_edx': 'str - full path to the ENVI-met ATMOSPHERE .EDX file\n'
            '(must contain Flow u / Flow v / Flow w). The .EDT file must have the same name and folder.',
    '_axis_': 'str (optional) - section plane:\n"z" = plan (default)\n"x" = vertical section in the YZ plane\n'
              '"y" = vertical section in the XZ plane',
    '_k': 'int - cell index along _axis_ (z: level, x: column i, y: row j).\n'
          'Use x_levels / y_levels / z_levels to find the index of a height or position. Default 0.',
    '_step_': 'int (optional) - sample every n-th cell in the section plane so arrows are not\n'
              'too dense (vertical direction of x / y sections is always every cell). Default 2.',
    '_scale_': 'float (optional) - multiplier for arrow length and width. Default 1.0.',
    '_vmax_': 'float (optional) - reference speed (m/s): an arrow of this speed is ~0.9 cell long\n'
              '(capped at 1.5x). Fix it when comparing scenarios; empty = maximum of this slice.',
    '_origin_': 'Point3d (optional) - position of the ENVI-met model origin in Rhino. Default (0,0,0).',
}
TIPS_OUT = {
    'x_levels': 'Cell-centre x coordinates (m) - pick _k for _axis_ = "x".',
    'y_levels': 'Cell-centre y coordinates (m) - pick _k for _axis_ = "y".',
    'z_levels': 'Cell-centre heights (m) - pick _k for _axis_ = "z" (plan level).',
    'arrows': 'Flat arrow mesh in the section plane (2 faces per arrow: shaft + head),\n'
              'length ~ in-plane speed -> _mesh of the Heatmap / LB Spatial Heatmap.',
    'values': 'In-plane wind speed (m/s) per mesh face (2 per arrow)\n'
              '-> _values of the Heatmap / LB Spatial Heatmap (List Access).',
    'points': 'Cell centre of every sampled cell (incl. calm cells without an arrow).',
    'vectors': 'Full 3D wind vector (u, v, w) in m/s at each point -> Vector Display.',
    'speeds': 'Full 3D wind speed (m/s) at each point.',
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
             'Meerkat - wind arrows from ENVI-met Flow u / v / w on a plan or section')


# ---------- optional inputs: runs even if they are not created on the component ----------
def opt(name, default=None):
    v = globals().get(name, default)
    return default if v is None else v


_run = opt('_run', False)
_axis_ = opt('_axis_', 'z')
_k = opt('_k', 0)
_step_ = opt('_step_', 2)
_scale_ = opt('_scale_', 1.0)
_vmax_ = opt('_vmax_', None)
_origin_ = opt('_origin_', None)

# outputs stay empty until _run is True
x_levels = y_levels = z_levels = None
arrows = values = points = vectors = speeds = None


# ---------- EDX header helpers ----------
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
    return re.sub(r'[^a-z0-9]', '', s.lower())


def run():
    # ---------- read the EDX header ----------
    with open(_edx, 'rb') as f:
        txt = f.read().decode('latin-1')

    nx = int(tag(txt, 'nr_xdata'))
    ny = int(tag(txt, 'nr_ydata'))
    nz = int(tag(txt, 'nr_zdata'))
    dxs = floats(tag(txt, 'spacing_x'))
    dys = floats(tag(txt, 'spacing_y'))
    dzs = floats(tag(txt, 'spacing_z'))
    xl = centers(edges(dxs))
    yl = centers(edges(dys))
    zl = centers(edges(dzs))
    var_names = [s.strip() for s in tag(txt, 'name_variables').split(',') if s.strip()]

    def find_var(prefix):
        for i, n in enumerate(var_names):
            if norm(n).startswith(prefix):
                return i
        raise ValueError('Variable "%s" not found in EDX. Is this an atmosphere output?' % prefix)

    iu, iv, iw = find_var('flowu'), find_var('flowv'), find_var('floww')

    # ---------- parameters ----------
    axis = (_axis_ or 'z').strip().lower()
    k = int(_k) if _k is not None else 0
    step = max(1, int(_step_)) if _step_ else 2
    scale = float(_scale_) if _scale_ else 1.0
    limit = {'x': nx, 'y': ny, 'z': nz}[axis]
    if not 0 <= k < limit:
        raise ValueError('_k must be in the range 0..%d for axis %s' % (limit - 1, axis))

    # ---------- read EDT (float32 LE, variable -> z -> y -> x) ----------
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
        U = read((iu * nz + k) * n2, n2)
        V = read((iv * nz + k) * n2, n2)
        W = read((iw * nz + k) * n2, n2)
        idx = lambda i, j, kk: j * nx + i
    else:
        U = read(iu * nz * n2, nz * n2)
        V = read(iv * nz * n2, nz * n2)
        W = read(iw * nz * n2, nz * n2)
        idx = lambda i, j, kk: kk * n2 + j * nx + i

    # ---------- collect samples on the slice ----------
    # each sample: (cell centre, full 3D vector, vector projected onto the section plane, cell size)
    o = _origin_ if _origin_ else rg.Point3d(0, 0, 0)
    samples = []

    if axis == 'z':
        plane_n = rg.Vector3d.ZAxis
        cells = [(i, j, k) for j in range(0, ny, step) for i in range(0, nx, step)]
    elif axis == 'x':
        plane_n = rg.Vector3d.XAxis
        cells = [(k, j, kk) for kk in range(0, nz, 1) for j in range(0, ny, step)]
    else:
        plane_n = rg.Vector3d.YAxis
        cells = [(i, k, kk) for kk in range(0, nz, 1) for i in range(0, nx, step)]

    for (i, j, kk) in cells:
        n = idx(i, j, kk)
        u, v, w = U[n], V[n], W[n]
        if u <= NODATA + 1 or v <= NODATA + 1 or w <= NODATA + 1:
            continue                                    # building / no-data cell
        full = rg.Vector3d(u, v, w)
        if axis == 'z':
            proj = rg.Vector3d(u, v, 0)
            cell = min(dxs[i], dys[j]) * step
        elif axis == 'x':
            proj = rg.Vector3d(0, v, w)
            cell = min(dys[j] * step, dzs[kk])
        else:
            proj = rg.Vector3d(u, 0, w)
            cell = min(dxs[i] * step, dzs[kk])
        c = rg.Point3d(o.X + xl[i], o.Y + yl[j], o.Z + zl[kk])
        samples.append((c, full, proj, cell))

    if not samples:
        raise ValueError('No valid cells on this slice.')

    vmax = float(_vmax_) if _vmax_ else max(s[2].Length for s in samples)
    vmax = vmax if vmax > 1e-9 else 1.0

    # ---------- build arrows ----------
    mesh = rg.Mesh()
    vals, pts, vecs, spds = [], [], [], []

    def add_arrow(c, d, side, L, width, spd):
        """flat arrow lying in the section plane, centred at c, direction d (unit)"""
        tail = c - d * (L / 2.0)
        tip = c + d * (L / 2.0)
        hl = min(0.35 * L, 1.2 * width * 2.5)          # arrowhead length
        neck = tip - d * hl
        sw, hw = width * 0.35, width                   # shaft / head width
        vs = mesh.Vertices
        a = vs.Count
        for p in (tail - side * sw, tail + side * sw, neck + side * sw, neck - side * sw,
                  neck + side * hw, tip, neck - side * hw):
            vs.Add(p)
        mesh.Faces.AddFace(a, a + 1, a + 2, a + 3)     # shaft
        mesh.Faces.AddFace(a + 4, a + 5, a + 6)        # head
        vals.extend([spd, spd])

    for c, full, proj, cell in samples:
        spd = proj.Length
        pts.append(c)
        vecs.append(full)
        spds.append(full.Length)
        if spd < 1e-6:
            continue
        d = rg.Vector3d(proj)
        d.Unitize()
        side = rg.Vector3d.CrossProduct(plane_n, d)
        side.Unitize()
        L = 0.9 * cell * scale * min(spd / vmax, 1.5)
        width = 0.18 * cell * scale
        add_arrow(c, d, side, L, width, spd)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
    print('Axis %s, index %d | %d arrows | vmax = %.2f m/s' % (axis, k, len(vals) // 2, vmax))
    return xl, yl, zl, mesh, vals, pts, vecs, spds


if _run:
    x_levels, y_levels, z_levels, arrows, values, points, vectors, speeds = run()
else:
    print('Set _run to True to run.')