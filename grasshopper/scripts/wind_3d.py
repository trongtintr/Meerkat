"""ENVI-met EDX/EDT -> 3D wind (3D arrows or streamlines) for Grasshopper / Ladybug
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8).
Reads "Flow u", "Flow v", "Flow w" (m/s) from atmosphere output.

Performance notes (v2):
  - EDT data is cached between runs (re-read only when the file changes), so tweaking
    parameters is fast after the first run.
  - Interpolation uses plain floats + direct index lookup on uniform X/Y grids.
  - RK2 integration reuses the end-point velocity (2 lookups per step instead of 3).
  - Meshes are built in one batch; arrow/seed counts are capped.

Inputs (only _edx is required; the others can be left off the component):
    _run        : bool         - True = read the file and build; False = do nothing (file not
                                 read, all outputs empty). Boolean Toggle; default True
    _edx        : str          - path to the .EDX file (.EDT with same name, same folder)
    _mode_      : str          - "arrows" (default) or "streamlines"
    _step_      : int          - arrows: sample every n cells in X/Y (default 4)
    _zstep_     : int          - arrows: sample every n levels in Z (default 2)
    _zmax_      : float        - arrows: only draw below this height in m (default 20)
    _max_arrows_: int          - arrows: hard cap on arrow count (default 6000)
    _scale_     : float        - arrow / tube size factor (default 1.0)
    _vmax_      : float        - reference speed (m/s); fix it when comparing scenarios
    _seeds_     : list Point3d - streamline start points (Type hint Point3d, LIST ACCESS)
                                 empty = seed grid at height _seed_z_
    _seed_step_ : int          - default seed grid spacing in cells (default 8)
    _seed_z_    : float        - default seed grid height (m), default 1.5
    _max_len_   : float        - max length of each streamline (m), default 200
    _tubes_     : bool         - streamlines: build coloured tube mesh (default True);
                                 False = curves only (fastest)
    _plane_     : str          - streamlines on a 2D slice instead of full 3D:
                                 "z" = plan at level _k (uses u, v)
                                 "x" = vertical YZ section at column _k (uses v, w)
                                 "y" = vertical XZ section at row _k (uses u, w)
                                 empty = full 3D (default)
    _k          : int          - slice index for _plane_ (see x/y/z_levels), default 0
    _origin_    : Point3d      - model origin in Rhino
Outputs:
    x_levels, y_levels, z_levels : cell-centre coordinates (m) - use to pick _k
    mesh      : 3D arrow mesh or streamline tubes -> _mesh of LB Spatial Heatmap
    values    : wind speed per face               -> _values of LB Spatial Heatmap
    curves    : streamline polylines (streamlines mode)
    points, vectors : 3D wind points and vectors (arrows mode) for Vector Display
"""
import re
import os
import math
import time
import bisect
from array import array
import Rhino.Geometry as rg
import scriptcontext as sc
from System.Collections.Generic import List

t0 = time.time()
NODATA = -999.0


TIPS_IN = {
    '_run': 'bool - True = read the file and build; False = do nothing\n'
            '(file not read, all outputs empty). Connect a Boolean Toggle. Default True.',
    '_edx': 'str - full path to the ENVI-met ATMOSPHERE .EDX file (Flow u / v / w).\n'
            'The .EDT file must have the same name and folder. Data is cached until the file changes.',
    '_mode_': 'str (optional) - "arrows" = 3D arrows on a sampled grid (default)\n'
              '"streamlines" = traced flow lines (full 3D or on a slice, see _plane_).',
    '_step_': 'int (optional) - arrows: sample every n-th cell in X / Y. Default 4.',
    '_zstep_': 'int (optional) - arrows: sample every n-th level in Z. Default 2.',
    '_zmax_': 'float (optional) - arrows: only draw arrows below this height (m). Default 20.',
    '_max_arrows_': 'int (optional) - arrows: hard cap on the number of arrows;\n'
                    'samples are thinned evenly above it. Default 6000.',
    '_scale_': 'float (optional) - size multiplier for arrows / tubes. Default 1.0.',
    '_vmax_': 'float (optional) - arrows: reference speed (m/s); an arrow of this speed is\n'
              '~0.9 x sample spacing long (capped at 1.5x). Fix it when comparing scenarios;\n'
              'empty = maximum of the sampled cells.',
    '_seeds_': 'list Point3d (optional, LIST ACCESS) - streamline start points (Rhino coordinates).\n'
               'With _plane_ set they are projected onto the slice.\n'
               'Empty = seed grid every _seed_step_ cells at height _seed_z_.',
    '_seed_step_': 'int (optional) - spacing of the default seed grid in cells. Default 8.\n'
                   'On x / y slices the vertical seed spacing is _seed_step_ / 4 levels.',
    '_seed_z_': 'float (optional) - height (m) of the default 3D seed grid. Default 1.5.',
    '_max_len_': 'float (optional) - max length of each streamline (m). Default 200.\n'
                 'Lines also stop at buildings, the domain edge or below 0.05 m/s.',
    '_tubes_': 'bool (optional) - streamlines: True = build a coloured tube mesh (default);\n'
               'False = curves only (fastest).',
    '_plane_': 'str (optional) - streamlines on a 2D slice instead of full 3D:\n'
               '"z" = plan at level _k (u, v)\n"x" = vertical YZ section at column _k (v, w)\n'
               '"y" = vertical XZ section at row _k (u, w)\nempty = full 3D (default).',
    '_k': 'int (optional) - slice index for _plane_ (see x_levels / y_levels / z_levels). Default 0.',
    '_origin_': 'Point3d (optional) - position of the ENVI-met model origin in Rhino. Default (0,0,0).',
}
TIPS_OUT = {
    'x_levels': 'Cell-centre x coordinates (m) - pick _k for _plane_ = "x".',
    'y_levels': 'Cell-centre y coordinates (m) - pick _k for _plane_ = "y".',
    'z_levels': 'Cell-centre heights (m) - pick _k for _plane_ = "z".',
    'mesh': '3D arrow mesh (arrows) or streamline tubes (streamlines)\n'
            '-> _mesh of the Heatmap / LB Spatial Heatmap.',
    'values': 'Wind speed (m/s) per mesh face -> _values of the Heatmap / LB Spatial Heatmap (List Access).',
    'curves': 'streamlines mode: one polyline per streamline (Rhino coordinates).',
    'points': 'arrows mode: position of every sampled cell (incl. calm cells without an arrow).',
    'vectors': 'arrows mode: 3D wind vector (u, v, w) in m/s at each point -> Vector Display.',
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
             'Meerkat - 3D wind from ENVI-met: 3D arrows or streamlines (full 3D or on a slice)')


def opt(name, default=None):
    v = globals().get(name, default)
    return default if v is None or v == [] else v


run = bool(opt('_run', True))
mode = str(opt('_mode_', 'arrows')).strip().lower()
step = max(1, int(opt('_step_', 4)))
zstep = max(1, int(opt('_zstep_', 2)))
zmax = float(opt('_zmax_', 20.0))
max_arrows = int(opt('_max_arrows_', 6000))
scale = float(opt('_scale_', 1.0))
vmax_in = opt('_vmax_', None)
seeds_in = opt('_seeds_', None)
seed_step = max(1, int(opt('_seed_step_', 8)))
seed_z = float(opt('_seed_z_', 1.5))
max_len = float(opt('_max_len_', 200.0))
tubes = bool(opt('_tubes_', True))
o = opt('_origin_', rg.Point3d(0, 0, 0))
plane = str(opt('_plane_', '')).strip().lower()
plane = plane if plane in ('x', 'y', 'z') else None
kidx = int(opt('_k', 0))
if seeds_in is not None and not isinstance(seeds_in, (list, tuple)):
    seeds_in = [seeds_in]
ox, oy, oz = o.X, o.Y, o.Z


# =============== 1. LOAD DATA (cached) ===============
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


def load(edx):
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
    edt = os.path.splitext(edx)[0] + '.EDT'
    if not os.path.exists(edt):
        edt = os.path.splitext(edx)[0] + '.edt'
    U = read(edt, find('flowu') * n3, n3)
    V = read(edt, find('flowv') * n3, n3)
    W = read(edt, find('floww') * n3, n3)
    S = bytearray(n3)                                   # 1 = building / no-data
    lim = NODATA + 1
    for q in range(n3):
        if U[q] <= lim or V[q] <= lim or W[q] <= lim:
            S[q] = 1
    d['U'], d['V'], d['W'], d['S'] = U, V, W, S
    return d


def build():
    edt_path = os.path.splitext(_edx)[0] + '.EDT'
    if not os.path.exists(edt_path):
        edt_path = os.path.splitext(_edx)[0] + '.edt'
    key = (_edx, os.path.getmtime(_edx), os.path.getmtime(edt_path))
    cache = sc.sticky.get('envimet_wind3d_cache')
    if not cache or cache.get('key') != key:
        cache = load(_edx)
        cache['key'] = key
        sc.sticky['envimet_wind3d_cache'] = cache

    nx, ny, nz = cache['nx'], cache['ny'], cache['nz']
    dxs, dys, dzs = cache['dxs'], cache['dys'], cache['dzs']
    U, V, W, S = cache['U'], cache['V'], cache['W'], cache['S']
    xc, yc, zc = centers(dxs), centers(dys), centers(dzs)
    x_levels, y_levels, z_levels = xc, yc, zc
    n2 = nx * ny
    t_load = time.time() - t0


    # =============== 2. FAST TRILINEAR INTERPOLATION ===============
    def make_locator(cs, sp):
        n = len(cs)
        c0, c1 = cs[0], cs[-1]
        if max(sp) - min(sp) < 1e-6:                        # uniform grid: direct index
            inv = 1.0 / sp[0]

            def loc(x):
                f = (x - c0) * inv
                if f < 0.0 or f > n - 1:
                    return -1, 0.0
                i = int(f)
                if i >= n - 1:
                    i = n - 2
                return i, f - i
        else:                                               # non-uniform: bisect
            def loc(x):
                if x < c0 or x > c1:
                    return -1, 0.0
                i = bisect.bisect_right(cs, x) - 1
                if i >= n - 1:
                    i = n - 2
                if i < 0:
                    i = 0
                return i, (x - cs[i]) / (cs[i + 1] - cs[i])
        return loc


    locx, locy, locz = make_locator(xc, dxs), make_locator(yc, dys), make_locator(zc, dzs)
    z_floor = zc[0]


    def velocity(x, y, z):
        """model coordinates -> (u, v, w) or None if outside domain / inside a building"""
        if z < z_floor:
            z = z_floor
        i, tx = locx(x)
        if i < 0:
            return None
        j, ty = locy(y)
        if j < 0:
            return None
        k, tz = locz(z)
        if k < 0:
            return None
        b = k * n2 + j * nx + i
        sx, sy, sz = 1.0 - tx, 1.0 - ty, 1.0 - tz
        corners = ((b, sx * sy * sz), (b + 1, tx * sy * sz),
                   (b + nx, sx * ty * sz), (b + nx + 1, tx * ty * sz),
                   (b + n2, sx * sy * tz), (b + n2 + 1, tx * sy * tz),
                   (b + n2 + nx, sx * ty * tz), (b + n2 + nx + 1, tx * ty * tz))
        u = v = w = 0.0
        for q, wt in corners:
            if wt > 0.0:
                if S[q]:
                    return None
                u += wt * U[q]
                v += wt * V[q]
                w += wt * W[q]
        return u, v, w


    # =============== 3. BATCH MESH BUILDER ===============
    verts = List[rg.Point3d]()
    faces = List[rg.MeshFace]()
    values = []


    def frame(dx, dy, dz):
        if abs(dz) < 0.9:                                   # e1 = d x Z
            e1 = (dy, -dx, 0.0)
        else:                                               # e1 = d x X
            e1 = (0.0, dz, -dy)
        l = math.sqrt(e1[0] ** 2 + e1[1] ** 2 + e1[2] ** 2)
        e1 = (e1[0] / l, e1[1] / l, e1[2] / l)
        e2 = (dy * e1[2] - dz * e1[1], dz * e1[0] - dx * e1[2], dx * e1[1] - dy * e1[0])
        return e1, e2


    def add_ring(cx, cy, cz, e1, e2, r, n):
        for s in range(n):
            a = 2.0 * math.pi * s / n
            ca, sa = r * math.cos(a), r * math.sin(a)
            verts.Add(rg.Point3d(cx + e1[0] * ca + e2[0] * sa,
                                 cy + e1[1] * ca + e2[1] * sa,
                                 cz + e1[2] * ca + e2[2] * sa))


    def add_arrow3d(c, d, L, r, spd, n=4):
        e1, e2 = frame(*d)
        hl = min(0.4 * L, 4.0 * r)
        tail = (c[0] - d[0] * L / 2, c[1] - d[1] * L / 2, c[2] - d[2] * L / 2)
        tip = (c[0] + d[0] * L / 2, c[1] + d[1] * L / 2, c[2] + d[2] * L / 2)
        neck = (tip[0] - d[0] * hl, tip[1] - d[1] * hl, tip[2] - d[2] * hl)
        a = verts.Count
        add_ring(tail[0], tail[1], tail[2], e1, e2, r, n)
        add_ring(neck[0], neck[1], neck[2], e1, e2, r, n)
        add_ring(neck[0], neck[1], neck[2], e1, e2, 2.5 * r, n)
        verts.Add(rg.Point3d(*tip))
        t = a + 3 * n
        for s in range(n):
            s1 = (s + 1) % n
            faces.Add(rg.MeshFace(a + s, a + s1, a + n + s1, a + n + s))
            faces.Add(rg.MeshFace(a + n + s, a + n + s1, a + 2 * n + s1, a + 2 * n + s))
            faces.Add(rg.MeshFace(a + 2 * n + s, a + 2 * n + s1, t))
        values.extend([spd] * (3 * n))


    def add_tube(pts, spds, r, n=3):
        for m in range(len(pts) - 1):
            p0, p1 = pts[m], pts[m + 1]
            dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
            l = math.sqrt(dx * dx + dy * dy + dz * dz)
            if l < 1e-9:
                continue
            e1, e2 = frame(dx / l, dy / l, dz / l)
            a = verts.Count
            add_ring(p0[0], p0[1], p0[2], e1, e2, r, n)
            add_ring(p1[0], p1[1], p1[2], e1, e2, r, n)
            for s in range(n):
                s1 = (s + 1) % n
                faces.Add(rg.MeshFace(a + s, a + s1, a + n + s1, a + n + s))
            values.extend([(spds[m] + spds[m + 1]) / 2.0] * n)


    points, vectors, curves = [], [], []
    cell = min(min(dxs), min(dys))

    # =============== 4a. MODE: 3D ARROWS ===============
    if mode.startswith('arrow'):
        samples = []
        for k in range(0, nz, zstep):
            if zc[k] > zmax:
                break
            for j in range(0, ny, step):
                row = k * n2 + j * nx
                for i in range(0, nx, step):
                    q = row + i
                    if S[q]:
                        continue
                    samples.append((xc[i], yc[j], zc[k], U[q], V[q], W[q]))
        if not samples:
            raise ValueError('No valid cells.')
        if len(samples) > max_arrows:                       # thin out evenly
            m = int(math.ceil(len(samples) / float(max_arrows)))
            samples = samples[::m]
        spd_all = [math.sqrt(u * u + v * v + w * w) for _, _, _, u, v, w in samples]
        vmax = float(vmax_in) if vmax_in else max(spd_all)
        vmax = vmax if vmax > 1e-9 else 1.0
        base = cell * step
        r = 0.05 * base * scale
        for (x, y, z, u, v, w), spd in zip(samples, spd_all):
            c = (x + ox, y + oy, z + oz)
            points.append(rg.Point3d(*c))
            vectors.append(rg.Vector3d(u, v, w))
            if spd < 1e-6:
                continue
            L = 0.9 * base * scale * min(spd / vmax, 1.5)
            add_arrow3d(c, (u / spd, v / spd, w / spd), L, r, spd)

    # =============== 4b. MODE: STREAMLINES ===============
    else:
        if plane is None:                                   # ---- full 3D ----
            vfun = velocity
            if seeds_in:
                seeds = [(p.X - ox, p.Y - oy, p.Z - oz) for p in seeds_in]
            else:
                seeds = [(xc[i], yc[j], seed_z)
                         for j in range(0, ny, seed_step) for i in range(0, nx, seed_step)]
        else:                                               # ---- 2D slice ----
            limit = {'x': nx, 'y': ny, 'z': nz}[plane]
            if not 0 <= kidx < limit:
                raise ValueError('_k must be in range 0..%d for _plane_ %s' % (limit - 1, plane))
            zs = max(1, seed_step // 4)                     # vertical seed spacing (levels)
            if plane == 'z':
                zf = zc[kidx]

                def vfun(x, y, z):
                    r = velocity(x, y, zf)
                    return None if r is None else (r[0], r[1], 0.0)
                fix = lambda p: (p[0], p[1], zf)
                grid = [(xc[i], yc[j], zf)
                        for j in range(0, ny, seed_step) for i in range(0, nx, seed_step)]
            elif plane == 'x':
                xf = xc[kidx]

                def vfun(x, y, z):
                    r = velocity(xf, y, z)
                    return None if r is None else (0.0, r[1], r[2])
                fix = lambda p: (xf, p[1], p[2])
                grid = [(xf, yc[j], zc[kk])
                        for kk in range(0, nz, zs) for j in range(0, ny, seed_step)]
            else:
                yf = yc[kidx]

                def vfun(x, y, z):
                    r = velocity(x, yf, z)
                    return None if r is None else (r[0], 0.0, r[2])
                fix = lambda p: (p[0], yf, p[2])
                grid = [(xc[i], yf, zc[kk])
                        for kk in range(0, nz, zs) for i in range(0, nx, seed_step)]
            if seeds_in:                                    # project user seeds onto the slice
                seeds = [fix((p.X - ox, p.Y - oy, p.Z - oz)) for p in seeds_in]
            else:
                seeds = grid
        ds = 0.75 * cell                                    # integration step (m)
        nmax = int(max_len / ds)
        vmin = 0.05
        r_tube = 0.08 * cell * scale
        dec = 3                                             # keep every 3rd point for tubes
        for (x, y, z) in seeds:
            vel = vfun(x, y, z)
            if vel is None:
                continue
            pts, spds = [(x, y, z)], [math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2)]
            for _ in range(nmax):                           # arc-length RK2
                s = spds[-1]
                if s < vmin:
                    break
                h = 0.5 * ds / s
                vm = vfun(x + vel[0] * h, y + vel[1] * h, z + vel[2] * h)
                if vm is None:
                    break
                sm = math.sqrt(vm[0] ** 2 + vm[1] ** 2 + vm[2] ** 2)
                if sm < vmin:
                    break
                h = ds / sm
                x, y, z = x + vm[0] * h, y + vm[1] * h, z + vm[2] * h
                vel = vfun(x, y, z)
                if vel is None:
                    break
                pts.append((x, y, z))
                spds.append(math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2))
            if len(pts) < 3:
                continue
            pts = [(p[0] + ox, p[1] + oy, p[2] + oz) for p in pts]
            pl = List[rg.Point3d]()
            for p in pts:
                pl.Add(rg.Point3d(*p))
            curves.append(rg.PolylineCurve(pl))
            if tubes:
                keep = list(range(0, len(pts), dec))
                if keep[-1] != len(pts) - 1:
                    keep.append(len(pts) - 1)
                add_tube([pts[i] for i in keep], [spds[i] for i in keep], r_tube)

    mesh = rg.Mesh()
    mesh.Vertices.AddVertices(verts)
    mesh.Faces.AddFaces(faces)
    mesh.Normals.ComputeNormals()
    print('%s%s | %d faces | %d streamlines | load %.1fs | total %.1fs'
          % (mode, (' on %s-slice %d' % (plane, kidx)) if plane and not mode.startswith('arrow') else '', mesh.Faces.Count, len(curves), t_load, time.time() - t0))
    return dict(x_levels=x_levels, y_levels=y_levels, z_levels=z_levels, mesh=mesh,
                values=values, curves=curves, points=points, vectors=vectors)


OUTS = ('x_levels', 'y_levels', 'z_levels', 'mesh', 'values', 'curves', 'points', 'vectors')
if run:
    result = build()
else:
    print('_run is False - nothing read, outputs empty')
    result = dict((n, None) for n in OUTS)
x_levels, y_levels, z_levels = result['x_levels'], result['y_levels'], result['z_levels']
mesh, values, curves = result['mesh'], result['values'], result['curves']
points, vectors = result['points'], result['vectors']