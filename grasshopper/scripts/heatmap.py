"""Fast heatmap / contour map for ENVI-met data (replaces LB Spatial Heatmap)
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8).

Colours the mesh from envimet_edx_reader.py and builds a legend. Much faster than
LB Spatial Heatmap: geometry and colours are passed to Rhino in a few bulk calls instead
of being converted to Ladybug geometry and rebuilt vertex by vertex.

Performance notes (v2):
    - .NET arrays are copied to Python lists once (per-element .NET access is very slow
      in Rhino 8 / CPython), colours are sent to Rhino in a single SetColors call
    - per-vertex band / clamped value are computed once instead of once per face
    - faces lying in one colour band (usually most) are coloured with native
      Duplicate/DeleteFaces/Unweld; only band-crossing faces are clipped in Python
    - new geometry is handed to Rhino as one block memory copy (Point3d[] / MeshFace[])
    - isolines are chained through shared mesh edges (exact, pure Python) instead of
      thousands of LineCurves + Curve.JoinCurves
    - mesh / contour geometry is cached: changing only legend inputs does not recompute it
    - smooth / contour weld the (unwelded) reader mesh first, so neighbouring cells share
      vertices -> real gradients and isolines

Display modes (_mode_):
    "cells"   - one flat colour per ENVI-met cell (default, same look as LB Spatial Heatmap)
    "smooth"  - colours interpolated between cells (continuous gradient)
    "contour" - contour map: filled colour bands between _levels_ equal steps + isolines

Inputs (only _mesh and _values are required):
    _run          : bool        - False = do nothing, all outputs empty (default True)
    _mesh         : Mesh        - mesh output of envimet_edx_reader.py
    _values       : list float  - values output of envimet_edx_reader.py (LIST ACCESS),
                                  one value per mesh face
    _filled_      : list bool   - filled output of the reader (LIST ACCESS, optional). Filled
                                  cells (buildings) are left out of the smoothing / contours
                                  and keep their flat colour
    _mode_        : str         - "cells" (default), "smooth" or "contour"
    _levels_      : int         - contour: number of colour bands (default 10)
    _smooth_      : int         - smooth / contour: smoothing passes on the vertex values
                                  (0 = none, default). Each pass averages every vertex with its
                                  neighbours (buildings excluded): smoother isolines, fewer noise
                                  islands. 1-3 light, 5-10 strong. Peaks get slightly flattened
    _vmin_, _vmax_: float       - colour range; connect v_min / v_max of the reader.
                                  Default: min / max of _values
    _colors_      : list Colour - custom gradient (LIST ACCESS); default = Ladybug palette
    _legend_title_: str         - legend_title output of the reader (multi-line text)
    _legend_pt_   : Point3d     - base point of the legend (default: right of the mesh)
    _legend_scale_: float       - size multiplier for legend bar + text (default 1.0)
    _legend_n_    : int         - number of value labels (cells / smooth; default 6).
                                  In contour mode every band boundary is labelled
    _decimals_    : int         - decimals of the legend labels (default 1)
    _global_title_: str         - main title of the map (multi-line ok), placed under the mesh
    _title_pt_    : Point3d     - top-left point of the global title (default: under the mesh,
                                  aligned with its left edge)
    _title_scale_ : float       - size multiplier of the global title (default 1.0)
    _title_xz_    : bool        - True = legend (bar, value labels, legend title) and global title
                                  stand upright in the vertical XZ plane (for sections / 3D views).
                                  tag_pts and title_pts then become PLANES. Default False
    _range_labels_: bool        - True = each label shows a value RANGE ("30.25 - 30.50") at the
                                  middle of its band instead of single tick values (default False).
                                  Contour: one range per band; cells / smooth: _legend_n_ - 1
                                  ranges. Values outside _vmin_/_vmax_ give "< x" / ">= x" ends
    _label_spacing_: float      - contour: distance between value labels along an isoline
                                  (default 0.15 x site diagonal)
    _label_size_  : float       - contour: text height of the isoline labels (default 1.2 % of
                                  the site diagonal)
    _label_min_len_: float      - contour: isolines shorter than this get no label
                                  (default 0.3 x _label_spacing_)
    _label_horizontal_: bool    - contour: True = isoline labels written horizontally (centred on
                                  the line) instead of following the line. Default False
    _peaks_       : bool        - contour: label every closed innermost contour (local peak /
                                  hot spot) with the HIGHEST data value of that zone, placed at
                                  the centre of the zone. Default True
    _peak_value_  : str         - contour: which value the peak label shows
                                  "max"    = highest cell value inside the zone (default)
                                  "centre" = data of the cell at the centre of the zone
    _peak_min_cells_: int       - contour: smallest zone (in cells) for a peak label. If the
                                  innermost contour of a hill is smaller, the next contour out
                                  is used (the label still shows the hill's maximum)
                                  (default 10). Peak labels keep the same minimum distance
                                  as the isoline labels; higher peaks win
    _peak_pos_    : str         - contour: where the peak label goes
                                  "centre" = centre cell of the contour (default)
                                  "max"    = centred on the cell with the maximum value
                                  "above"  = just above the maximum cell (peak_pts marks it)
    _peak_fit_    : bool        - contour: True = drop a peak label whose text does not fit
                                  inside its contour (default False). Peak regions are often only a
                                  few cells wide: use a small _label_size_ with this option.
                                  One-cell-wide strips are never labelled (not a real centre)
Outputs:
    mesh       : coloured mesh
    contours   : contour mode: isolines (joined curves) at the band boundaries
    contour_val: value of each isoline
    legend     : coloured legend bar mesh (stepped in contour mode)
    tag_pts    : positions of all legend texts (value labels + title)   } -> Text Tag 3D
                 (planes in the XZ plane when _title_xz_ is True)
    tag_txt    : the legend texts                                       }
                 (the title is split into one tag per line, stacked from the bottom up,
                  so the last line always sits just above the bar)
    text_size  : suggested text height -> Size input of Text Tag 3D
    title_pts  : positions of the global title lines (top-down)        } -> 2nd Text Tag 3D
                 (planes in the XZ plane when _title_xz_ is True)
    title_txt  : global title, one item per line                        }
    title_size : text height for the global title
    v_range    : (vmin, vmax) used
    iso_planes : contour: one plane per isoline label (along the line, readable) } -> 3rd
    iso_txt    : contour: label text (isoline value)                            }  Text Tag 3D
    iso_size   : contour: text height of the isoline labels                     }
    iso_val    : contour: value of each label
    peak_planes: contour: one plane per peak label (see _peak_pos_)     } -> 4th Text Tag 3D
    peak_txt   : contour: value shown for each peak (see _peak_value_)  }
    peak_val   : contour: that value (number)
    peak_pts   : contour: centre of the cell the value was taken from
"""
import time
import Rhino.Geometry as rg
import System
import System.Drawing as sd
from System.Runtime.InteropServices import GCHandle, GCHandleType, Marshal

try:
    import scriptcontext as sc
except ImportError:
    sc = None

LB_COLORS = [(75, 107, 169), (115, 147, 202), (170, 200, 247), (193, 213, 208),
             (245, 239, 103), (252, 230, 74), (239, 156, 21), (234, 123, 0),
             (234, 74, 0), (234, 38, 0)]
TIPS_IN = {
    '_run': 'bool - False = do nothing, all outputs empty. Default True.',
    '_mesh': 'Mesh - mesh output of the ENVI-met reader (one face per cell).',
    '_values': 'list float - values output of the reader, one value per mesh face.\nSet this input to LIST ACCESS.',
    '_filled_': 'list bool (optional) - filled output of the reader (LIST ACCESS).\nFilled cells (buildings) keep a flat colour and are left out of smoothing / contours.',
    '_mode_': 'str - display mode:\n"cells" = one flat colour per cell (default)\n"smooth" = colours interpolated between cells\n"contour" = filled colour bands + isolines',
    '_levels_': 'int - contour mode: number of equal colour bands between _vmin_ and _vmax_. Default 10.',
    '_smooth_': 'int - smooth / contour: smoothing passes on the vertex values (0 = none, default).\nSmoother isolines, fewer noise islands. 1-3 light, 5-10 strong.\nPeaks get slightly flattened - use 0 when exact values matter.',
    '_vmin_': 'float (optional) - lower end of the colour range. Connect v_min of the reader.\nDefault: minimum of _values.',
    '_vmax_': 'float (optional) - upper end of the colour range. Connect v_max of the reader.\nDefault: maximum of _values.',
    '_colors_': 'list Colour (optional, LIST ACCESS) - custom gradient from low to high.\nDefault: Ladybug palette.',
    '_legend_title_': 'str (optional) - legend title, multi-line. Connect legend_title of the reader.\nLines are stacked bottom-up above the legend bar.',
    '_legend_pt_': 'Point3d (optional) - base point (bottom-left) of the legend. Default: right of the mesh.',
    '_legend_scale_': 'float (optional) - size multiplier for legend bar + texts. Default 1.0.',
    '_legend_n_': 'int (optional) - cells / smooth: number of value labels. Default 6.\nIn contour mode every band boundary is labelled.',
    '_decimals_': 'int (optional) - decimals of the legend labels. Default 1.',
    '_range_labels_': 'bool (optional) - True = labels show value RANGES ("30.25 - 30.50") at the middle\nof each band instead of single tick values; values outside the range give "< x" / ">= x". Default False.',
    '_global_title_': 'str (optional) - main title of the map (multi-line ok), placed under the mesh.',
    '_title_pt_': 'Point3d (optional) - top-left point of the global title. Default: under the mesh, left aligned.',
    '_title_scale_': 'float (optional) - size multiplier of the global title. Default 1.0.',
    '_title_xz_': 'bool (optional) - True = the legend (bar, value labels, legend title) and the global\n'
                  'title stand upright in the vertical XZ plane (text faces -Y, reads along +X, up = +Z),\n'
                  'e.g. for XZ sections or 3D views. tag_pts / title_pts then output PLANES - connect\n'
                  'them to the Location of Text Tag 3D as before. Default False (flat in XY).',
    '_label_spacing_': 'float (optional) - contour: distance between value labels along an isoline\n'
                       '(model units). Long lines get several labels. Default 0.15 x site diagonal.\n'
                       'Labels of different lines keep at least 0.35 x this distance apart.',
    '_label_size_': 'float (optional) - contour: text height of the isoline labels.\n'
                    'Default 1.2 % of the site diagonal.',
    '_label_min_len_': 'float (optional) - contour: isolines shorter than this get no label\n'
                       '(hides labels on small noise islands). Default 0.3 x _label_spacing_.',
    '_label_horizontal_': 'bool (optional) - contour: True = isoline labels are written horizontally\n'
                          '(centred on the line) instead of following the line direction. Default False.\n'
                          'Use this instead of converting iso_planes with an XY Plane component.',
    '_peaks_': 'bool (optional) - contour: label every closed innermost contour (local peak /\n'
               'hot spot) with the HIGHEST real cell value of that zone, placed at the centre of\n'
               'the zone (see _peak_value_ / _peak_pos_). Zones touching the outer edge of the\n'
               'site are skipped; zones next to buildings are kept. Default True.',
    '_peak_value_': 'str (optional) - contour: which value the peak label shows:\n'
                    '"max" = highest cell value inside the zone (default)\n'
                    '"centre" = data of the cell at the centre of the zone',
    '_peak_min_cells_': 'int (optional) - contour: smallest zone (number of cells) for a peak label.\n'
                        'If the innermost contour of a hill is smaller (or only one cell wide), the\n'
                        'next contour out is used; the label still shows the hill maximum. Default 10.\n'
                        'Peak labels keep the isoline-label distance from each other; higher peaks win.',
    '_peak_pos_': 'str (optional) - contour: where the peak label goes:\n'
                  '"centre" = centre cell of the contour, farthest from its isoline (default)\n'
                  '"max" = centred on the cell with the maximum value\n'
                  '"above" = just above the maximum cell (show peak_pts as a dot to mark it)',
    '_peak_fit_': 'bool (optional) - contour: True = drop a peak label whose text does not fit inside\n'
                  'its contour, so labels never cross isolines (default False = keep all).\n'
                  'Peak regions are often only a few cells wide - use a small _label_size_ with it.\n'
                  'One-cell-wide strips never get a peak label (they have no real centre).',
}
TIPS_OUT = {
    'mesh': 'Coloured mesh (cells / smooth / contour bands).',
    'contours': 'contour mode: isolines (joined polylines) at the band boundaries; empty in other modes.',
    'contour_val': 'Value of each isoline (same order as contours).',
    'legend': 'Coloured legend bar mesh (stepped in contour mode).',
    'tag_pts': 'Positions of the legend texts (value labels + title lines) -> Location of Text Tag 3D.\n'
               'Points (flat XY) or planes (upright XZ, _title_xz_ = True).',
    'tag_txt': 'Legend texts -> Text of Text Tag 3D.',
    'text_size': 'Suggested text height for the legend -> Size of Text Tag 3D.',
    'v_range': '(vmin, vmax) actually used for the colours.',
    'title_pts': 'Positions of the global title lines -> Location of a 2nd Text Tag 3D.\n'
                 'Points (flat XY) or planes (upright XZ, _title_xz_ = True).',
    'title_txt': 'Global title, one item per line -> Text of the 2nd Text Tag 3D.',
    'title_size': 'Text height of the global title -> Size of the 2nd Text Tag 3D.',
    'iso_planes': 'contour: one plane per isoline label, aligned with the line and turned so the\n'
                  'text always reads left-to-right -> Location of a 3rd Text Tag 3D.\n'
                  'Connect the planes DIRECTLY (not through XY Plane): the origin is the text corner,\n'
                  'computed for this orientation. Labels whose text would leave the domain are dropped.',
    'iso_txt': 'contour: label texts (isoline values, _decimals_) -> Text of the 3rd Text Tag 3D.',
    'iso_size': 'contour: text height of the isoline labels -> Size of the 3rd Text Tag 3D.',
    'iso_val': 'contour: value of each label (same order as iso_planes).',
    'peak_planes': 'contour: one plane per peak label, placed as set by _peak_pos_\n'
                   '(kept inside the domain). Connect directly, not through XY Plane\n'
                   '-> Location of a 4th Text Tag 3D (style it differently from the isoline labels).',
    'peak_txt': 'contour: value of each peak label (centre cell or max, see _peak_value_)\n'
                '-> Text of the 4th Text Tag 3D.',
    'peak_val': 'contour: value of each peak label (number).',
    'peak_pts': 'contour: centre of the cell the peak value was taken from.',
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


OUTS = ('mesh', 'contours', 'contour_val', 'legend', 'tag_pts', 'tag_txt', 'text_size',
        'v_range', 'title_pts', 'title_txt', 'title_size',
        'iso_planes', 'iso_txt', 'iso_size', 'iso_val',
        'peak_planes', 'peak_txt', 'peak_val', 'peak_pts')


USED = []                                                # (input, value, from GH or default)


def opt(name, default=None):
    """value of a component input; the default is used ONLY when the input is missing
    on the component or has no data. Every lookup is logged in the 'out' report"""
    v = globals().get(name, None)
    if v is None or v == []:
        USED.append((name, default, 'default'))
        return default
    USED.append((name, v, 'input'))
    return v


def as_int(v):
    """int from int / float / text such as "14" or "14.0" (Panel input)"""
    return int(round(float(str(v).strip()))) if not isinstance(v, (int, float)) else int(round(v))


def as_float(v):
    return float(str(v).strip()) if not isinstance(v, (int, float)) else float(v)


def as_bool(v):
    """bool from bool / number / text: "False", "0", "no", "" -> False"""
    if isinstance(v, str):
        return v.strip().lower() not in ('false', '0', 'no', 'off', 'none', '')
    return bool(v)


def report_inputs():
    lines = ['inputs:']
    for name, v, src in USED:
        if name in ('_mesh', '_values', '_filled_', '_colors_'):
            if src == 'input':
                try:
                    shown = '%d items' % len(v)
                except TypeError:
                    shown = type(v).__name__
            else:
                shown = '-'
        else:
            shown = str(v).replace('\r', ' ').replace('\n', ' | ')
            if len(shown) > 40:
                shown = shown[:37] + '...'
        lines.append('  %-18s %-8s %s' % (name, src, shown))
    print('\n'.join(lines))


run = as_bool(opt('_run', True))
mesh_in = opt('_mesh', None)
vals_in = opt('_values', None)
filled_in = opt('_filled_', None)
mode = str(opt('_mode_', 'cells')).strip().lower()
if mode not in ('smooth', 'contour'):
    mode = 'cells'
levels = max(2, as_int(opt('_levels_', 10)))
smooth_it = min(50, max(0, as_int(opt('_smooth_', 0))))
vmin_in, vmax_in = opt('_vmin_', None), opt('_vmax_', None)
cols_in = opt('_colors_', None)
title_in = opt('_legend_title_', None)
legend_pt = opt('_legend_pt_', None)
legend_scale = as_float(opt('_legend_scale_', 1.0))
legend_n = max(2, as_int(opt('_legend_n_', 6)))
dec = as_int(opt('_decimals_', 1))
range_labels = as_bool(opt('_range_labels_', False))
gtitle_in = opt('_global_title_', None)
gtitle_pt = opt('_title_pt_', None)
gtitle_scale = as_float(opt('_title_scale_', 1.0))
title_xz = as_bool(opt('_title_xz_', False))
label_spacing_in = opt('_label_spacing_', None)
label_size_in = opt('_label_size_', None)
label_min_len_in = opt('_label_min_len_', None)
peaks_on = as_bool(opt('_peaks_', True))
label_horizontal = as_bool(opt('_label_horizontal_', False))
peak_min_cells = max(1, as_int(opt('_peak_min_cells_', 10)))
peak_pos = str(opt('_peak_pos_', 'centre')).strip().lower()
if peak_pos not in ('centre', 'center', 'max', 'above'):
    peak_pos = 'centre'
peak_fit = as_bool(opt('_peak_fit_', False))
peak_value = str(opt('_peak_value_', 'max')).strip().lower()
if peak_value not in ('centre', 'center', 'max'):
    peak_value = 'max'


def to_color_array(py_list):
    """Python list of Color -> .NET Color[] in one conversion"""
    return System.Array[sd.Color](py_list)


def _struct_array(T, flat, per, net_type, make):
    """flat Python numbers -> .NET struct array (Point3d = 3 doubles, MeshFace = 4 ints)
    with one block memory copy instead of one .NET call per element"""
    n = len(flat) // per
    arr = System.Array.CreateInstance(T, n)
    if not n:
        return arr
    try:
        src = System.Array[net_type](flat)
        h = GCHandle.Alloc(arr, GCHandleType.Pinned)
        try:
            Marshal.Copy(src, 0, h.AddrOfPinnedObject(), len(flat))
        finally:
            h.Free()
    except Exception:                                    # safe fallback, slower
        for i in range(n):
            arr[i] = make(*flat[per * i:per * i + per])
    return arr


def point_array(flat_xyz):
    return _struct_array(rg.Point3d, flat_xyz, 3, System.Double, rg.Point3d)


def face_array(flat_abcd):
    return _struct_array(rg.MeshFace, flat_abcd, 4, System.Int32, rg.MeshFace)


def mesh_from_flat(flat_xyz, flat_abcd):
    mm = rg.Mesh()
    mm.Vertices.AddVertices(point_array(flat_xyz))
    mm.Faces.AddFaces(face_array(flat_abcd))
    return mm


def make_lut(pal):
    """256-step colour lookup table"""
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


def build_mesh(values, filled, vmin, vmax, lut, bb, diag):
    nf = len(values)
    span = 255.0 / (vmax - vmin)

    # smooth / contour need neighbouring cells to SHARE vertices. The reader mesh is
    # unwelded (4 own vertices per cell) -> weld identical vertices natively first
    # (face order is kept, so values[f] still belongs to face f)
    if mode == 'cells':
        base = mesh_in
    else:
        base = mesh_in.DuplicateMesh()
        base.VertexColors.Clear()
        base.Vertices.CombineIdentical(True, True)
    nv = base.Vertices.Count

    def cols_of(vals):
        return [lut[0 if s < 0 else (255 if s > 255 else s)]
                for s in [int((v - vmin) * span + 0.5) for v in vals]]

    fi = list(base.Faces.ToIntArray(False))              # 4 vertex ids per face, one copy
    fcol = cols_of(values)                               # flat colour per face
    contours, contour_val = [], []
    iso_raw = []                                         # (flat xyz, value) per isoline
    peaks = []      # (centre x, y, z, room, max x, y, z, room, max value, n vertices, cell,
    #                  centre-cell value)

    def vertex_values():
        """average of the (non-filled) faces around each vertex"""
        acc, cnt = [0.0] * nv, [0] * nv
        for f in range(nf):
            if filled[f]:
                continue
            v = values[f]
            b = 4 * f
            a0, a1, a2, a3 = fi[b], fi[b + 1], fi[b + 2], fi[b + 3]
            acc[a0] += v
            acc[a1] += v
            acc[a2] += v
            cnt[a0] += 1
            cnt[a1] += 1
            cnt[a2] += 1
            if a3 != a2:
                acc[a3] += v
                cnt[a3] += 1
        vv = [acc[q] / cnt[q] if cnt[q] else None for q in range(nv)]
        if smooth_it:
            vv = smooth_values(vv)
        return vv

    def smooth_values(vv):
        """Laplacian smoothing over the cell edges of non-filled faces"""
        edges = set()
        for f in range(nf):
            if filled[f]:
                continue
            b = 4 * f
            a0, a1, a2, a3 = fi[b], fi[b + 1], fi[b + 2], fi[b + 3]
            ring = (a0, a1, a2, a3) if a3 != a2 else (a0, a1, a2)
            n = len(ring)
            for i in range(n):
                p, q = ring[i], ring[(i + 1) % n]
                edges.add((p, q) if p < q else (q, p))
        ea = [e[0] for e in edges]
        eb = [e[1] for e in edges]
        ne = len(ea)
        for _ in range(smooth_it):
            acc = [0.0 if v is None else v for v in vv]
            cnt = [1] * nv
            for i in range(ne):
                a, b = ea[i], eb[i]
                acc[a] += vv[b]
                acc[b] += vv[a]
                cnt[a] += 1
                cnt[b] += 1
            vv = [None if vv[q] is None else acc[q] / cnt[q] for q in range(nv)]
        return vv

    # ================= CELLS =================
    if mode == 'cells':
        m = mesh_in.DuplicateMesh()
        m.VertexColors.Clear()
        m.Unweld(0, True)
        fu = list(m.Faces.ToIntArray(False))
        vc = [lut[0]] * m.Vertices.Count
        for f in range(nf):
            b = 4 * f
            c = fcol[f]
            vc[fu[b]] = vc[fu[b + 1]] = vc[fu[b + 2]] = vc[fu[b + 3]] = c
        m.VertexColors.SetColors(to_color_array(vc))

    # ================= SMOOTH =================
    elif mode == 'smooth':
        vv = vertex_values()
        vcol = cols_of([vmin if v is None else v for v in vv])
        m = base.DuplicateMesh()
        m.VertexColors.Clear()
        if any(filled):                                  # keep buildings flat: split them off
            m.Unweld(0, True)
            fu = list(m.Faces.ToIntArray(False))
            vc = [lut[0]] * m.Vertices.Count
            for f in range(nf):
                b = 4 * f
                if filled[f]:
                    c = fcol[f]
                    vc[fu[b]] = vc[fu[b + 1]] = vc[fu[b + 2]] = vc[fu[b + 3]] = c
                else:                                    # own face guarantees a vertex value
                    vc[fu[b]] = vcol[fi[b]]
                    vc[fu[b + 1]] = vcol[fi[b + 1]]
                    vc[fu[b + 2]] = vcol[fi[b + 2]]
                    vc[fu[b + 3]] = vcol[fi[b + 3]]
            m.VertexColors.SetColors(to_color_array(vc))
        else:
            m.VertexColors.SetColors(to_color_array(vcol))

    # ================= CONTOUR =================
    else:
        vv = vertex_values()
        xyz = list(base.Vertices.ToFloatArray())         # x0, y0, z0, x1, ... one copy
        PT = [(xyz[3 * q], xyz[3 * q + 1], xyz[3 * q + 2]) for q in range(nv)]
        step = (vmax - vmin) / float(levels)
        inv = 1.0 / step
        L1 = levels - 1
        bounds = [vmin + step * i for i in range(levels + 1)]
        band_col = cols_of([vmin + step * (i + 0.5) for i in range(levels)])

        # per-vertex clamped value and band, computed once
        cv = [None if v is None else (vmin if v < vmin else (vmax if v > vmax else v))
              for v in vv]
        vb = [None if v is None else min(L1, int((v - vmin) * inv)) for v in cv]

        vflat, fflat, cols = [], [], []                  # pure Python buffers
        vext, fext, cext = vflat.extend, fflat.extend, cols.extend
        iso_adj = [{} for _ in range(levels + 1)]        # per level: edge key -> neighbour keys
        iso_pt = [{} for _ in range(levels + 1)]         # per level: edge key -> point

        def add_poly(pts, c):
            n = len(pts)
            if n < 3:
                return
            a = len(vflat) // 3
            for p in pts:
                vext(p)
            cext([c] * n)
            if n == 4:
                fext((a, a + 1, a + 2, a + 3))
            elif n == 3:
                fext((a, a + 1, a + 2, a + 2))
            else:
                for t in range(1, n - 1):                # fan
                    fext((a, a + t, a + t + 1, a + t + 1))

        def lerp(p, va, q, vb_, lv):
            t = (lv - va) / (vb_ - va)
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t,
                    p[2] + (q[2] - p[2]) * t)

        def clip(poly, lv, keep_above):
            """clip polygon [(pt, v)] against scalar level"""
            out = []
            n = len(poly)
            for i in range(n):
                p, vp = poly[i]
                q, vq = poly[(i + 1) % n]
                ip = (vp >= lv) if keep_above else (vp <= lv)
                iq = (vq >= lv) if keep_above else (vq <= lv)
                if ip:
                    out.append((p, vp))
                if ip != iq:
                    out.append((lerp(p, vp, q, vq, lv), lv))
            return out

        def triangle(ia, ib, ic, b0, b1):
            """only called for triangles crossing at least one band boundary"""
            tri = [(PT[ia], cv[ia]), (PT[ib], cv[ib]), (PT[ic], cv[ic])]
            for bi in range(b0, b1 + 1):                 # one polygon per crossed band
                poly = tri
                if bi > 0:
                    poly = clip(poly, bounds[bi], True)
                if bi < L1 and poly:
                    poly = clip(poly, bounds[bi + 1], False)
                add_poly([t[0] for t in poly], band_col[bi])
            ids = (ia, ib, ic)
            for li in range(b0 + 1, b1 + 1):             # isolines: edge-to-edge segments
                lv = bounds[li]
                pts = iso_pt[li]
                ks = []
                for e in range(3):
                    a, b = ids[e], ids[(e + 1) % 3]
                    if (cv[a] < lv) != (cv[b] < lv):
                        k = (a, b) if a < b else (b, a)  # shared mesh edge = exact join key
                        ks.append(k)
                        if k not in pts:
                            pts[k] = lerp(PT[k[0]], cv[k[0]], PT[k[1]], cv[k[1]], lv)
                if len(ks) == 2:
                    adj = iso_adj[li]
                    adj.setdefault(ks[0], []).append(ks[1])
                    adj.setdefault(ks[1], []).append(ks[0])

        def chains(adj):
            """walk the edge graph of one level into open / closed polylines"""
            seen = set()
            out = []
            ends = [k for k, n in adj.items() if len(n) == 1]
            for s in ends + list(adj.keys()):            # open chains first, then loops
                if s in seen:
                    continue
                path, cur = [s], s
                seen.add(s)
                while True:
                    nxt = None
                    for n in adj[cur]:
                        if n not in seen:
                            nxt = n
                            break
                    if nxt is None:
                        break
                    path.append(nxt)
                    seen.add(nxt)
                    cur = nxt
                out.append((path, len(path) > 2 and s in adj[cur]))
            return out

        # classify faces: drawn as-is (filled / no value / one band) or split into bands
        face_c = []                                      # colour of each as-is face, in order
        split = []                                       # faces crossing band boundaries
        for f in range(nf):
            b = 4 * f
            k0, k1, k2, k3 = vb[fi[b]], vb[fi[b + 1]], vb[fi[b + 2]], vb[fi[b + 3]]
            if filled[f] or k0 is None or k1 is None or k2 is None or k3 is None:
                face_c.append(fcol[f])
            elif k0 == k1 == k2 == k3:                   # whole face in one band
                face_c.append(band_col[k0])
            else:
                split.append(f)

        # part 1 (usually most faces): native copy -> delete split faces -> unweld
        m = base.DuplicateMesh()
        m.VertexColors.Clear()
        if split:
            m.Faces.DeleteFaces(System.Array[System.Int32](split), True)
        if m.Faces.Count:
            m.Unweld(0, True)
            fu = list(m.Faces.ToIntArray(False))
            vc = [lut[0]] * m.Vertices.Count
            for k in range(len(face_c)):
                b = 4 * k
                c = face_c[k]
                vc[fu[b]] = vc[fu[b + 1]] = vc[fu[b + 2]] = vc[fu[b + 3]] = c
            m.VertexColors.SetColors(to_color_array(vc))

        # part 2: band-crossing faces, clipped in Python (+ isoline segments)
        for f in split:
            b = 4 * f
            i0, i1, i2, i3 = fi[b], fi[b + 1], fi[b + 2], fi[b + 3]
            k0, k1, k2, k3 = vb[i0], vb[i1], vb[i2], vb[i3]
            lo, hi = min(k0, k1, k2), max(k0, k1, k2)
            if lo == hi:
                add_poly((PT[i0], PT[i1], PT[i2]), band_col[lo])
            else:
                triangle(i0, i1, i2, lo, hi)
            if i2 != i3:
                lo, hi = min(k0, k2, k3), max(k0, k2, k3)
                if lo == hi:
                    add_poly((PT[i0], PT[i2], PT[i3]), band_col[lo])
                else:
                    triangle(i0, i2, i3, lo, hi)
        if fflat:
            m2 = mesh_from_flat(vflat, fflat)
            m2.VertexColors.SetColors(to_color_array(cols))
            if m.Faces.Count:
                m.Append(m2)
            else:
                m = m2

        # ---- peaks: innermost closed contours around a local maximum
        # vertices are grouped into connected regions of the same band; a region whose
        # neighbours are all in LOWER bands and that does not touch the site edge / a building
        # is the inside of an innermost closed contour -> label its maximum cell value
        ecount = {}
        for f in range(nf):
            b = 4 * f
            i0, i1, i2, i3 = fi[b], fi[b + 1], fi[b + 2], fi[b + 3]
            if filled[f] or vb[i0] is None or vb[i1] is None or vb[i2] is None or vb[i3] is None:
                continue
            ring = (i0, i1, i2, i3) if i2 != i3 else (i0, i1, i2)
            n = len(ring)
            for e in range(n):
                a, c = ring[e], ring[(e + 1) % n]
                k = (a, c) if a < c else (c, a)
                ecount[k] = ecount.get(k, 0) + 1
        nbr = [[] for _ in range(nv)]
        nbr8 = [[] for _ in range(nv)]                   # edges + face diagonals (distances)
        for f in range(nf):
            b = 4 * f
            i0, i1, i2, i3 = fi[b], fi[b + 1], fi[b + 2], fi[b + 3]
            if i2 != i3 and not filled[f]:
                nbr8[i0].append(i2)
                nbr8[i2].append(i0)
                nbr8[i1].append(i3)
                nbr8[i3].append(i1)
        border = bytearray(nv)
        for (a, c), cnt in ecount.items():
            nbr[a].append(c)
            nbr[c].append(a)
            nbr8[a].append(c)
            nbr8[c].append(a)
            if cnt == 1:                                 # edge of the valid area
                border[a] = border[c] = 1
        # border vertices on the outer edge of the SITE (closes no contour); the other border
        # vertices are building walls, which are allowed to bound a zone
        tolb = 1e-6 * diag
        ext = [(bb.Min.X, bb.Max.X), (bb.Min.Y, bb.Max.Y), (bb.Min.Z, bb.Max.Z)]
        flat_ax = [hi_ - lo_ <= tolb for lo_, hi_ in ext]
        dom_edge = bytearray(nv)
        for v in range(nv):
            if border[v]:
                p_ = PT[v]
                for c_ in range(3):
                    if not flat_ax[c_] and (abs(p_[c_] - ext[c_][0]) <= tolb or
                                           abs(p_[c_] - ext[c_][1]) <= tolb):
                        dom_edge[v] = 1
                        break
        comp = [-1] * nv
        peak_comp = {}                                   # component id -> [n vertices, best val, face]
        ncomp = 0
        for v0 in range(nv):
            if comp[v0] != -1 or vb[v0] is None or not nbr[v0]:
                continue
            band = vb[v0]
            comp[v0] = ncomp
            stack, members, is_peak, has_nbr = [v0], [], True, False
            while stack:
                v = stack.pop()
                members.append(v)
                if dom_edge[v]:                          # touches the site edge: not closed
                    is_peak = False
                for w in nbr[v]:
                    bw = vb[w]
                    if bw == band:
                        if comp[w] == -1:
                            comp[w] = ncomp
                            stack.append(w)
                    else:
                        has_nbr = True
                        if bw > band:
                            is_peak = False
            if is_peak and has_nbr:
                peak_comp[ncomp] = [members, None, -1]
            ncomp += 1
        if peak_comp:
            # A hill = one core (innermost closed contour). Its ZONE is the smallest closed
            # contour around the core that is big enough to be a real area: start at the
            # core's band and step out one contour level at a time while the zone is too
            # small / too thin. The zone = connected set of vertices >= that level.
            import heapq
            b0 = 0                                       # typical cell width (first valid quad)
            while b0 < nf and filled[b0]:
                b0 += 1
            b0 = 4 * min(b0, nf - 1)
            pa, pb = PT[fi[b0]], PT[fi[b0 + 1]]
            cell_w = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2 + (pa[2] - pb[2]) ** 2) ** 0.5

            vfaces = [[] for _ in range(nv)]             # valid cells around each vertex
            for f in range(nf):
                if filled[f]:
                    continue
                b = 4 * f
                ids = (fi[b], fi[b + 1], fi[b + 2], fi[b + 3]) if fi[b + 2] != fi[b + 3] else \
                      (fi[b], fi[b + 1], fi[b + 2])
                if any(vb[q] is None for q in ids):
                    continue
                for q in ids:
                    vfaces[q].append(f)

            def corners(ff):
                bq = 4 * ff
                return (fi[bq], fi[bq + 1], fi[bq + 2], fi[bq + 3]) if fi[bq + 2] != fi[bq + 3] \
                    else (fi[bq], fi[bq + 1], fi[bq + 2])

            def zone_at(seed, level):
                """connected vertices with band >= level around seed; None if it reaches the
                outer edge of the site (contour not closed). Building walls may bound it"""
                zone, stack = {seed: 1}, [seed]
                while stack:
                    v = stack.pop()
                    if dom_edge[v]:                      # reaches the site edge
                        return None
                    for w in nbr[v]:
                        if w not in zone and vb[w] is not None and vb[w] >= level:
                            zone[w] = 1
                            stack.append(w)
                return zone

            def analyse(zone):
                """cells fully inside, max cell, distance to the zone edge, centre cell"""
                cells = set()
                for v in zone:
                    for ff in vfaces[v]:
                        cells.add(ff)
                cells = [ff for ff in cells if all(r in zone for r in corners(ff))]
                if not cells:
                    return None
                fmax = max(cells, key=lambda ff: values[ff])
                cs = corners(fmax)
                mx = sum(PT[r][0] for r in cs) / len(cs)
                my = sum(PT[r][1] for r in cs) / len(cs)
                mz = sum(PT[r][2] for r in cs) / len(cs)
                dist = {}
                for v in zone:                           # isoline crosses edge v-w ~ half way
                    if border[v]:                        # building wall bounds the zone too
                        dist[v] = 0.0
                    for w in nbr[v]:
                        if w not in zone:
                            p0, p1 = PT[v], PT[w]
                            d0 = 0.5 * ((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2 +
                                        (p0[2] - p1[2]) ** 2) ** 0.5
                            if d0 < dist.get(v, 1e300):
                                dist[v] = d0
                heap = [(d, v) for v, d in dist.items()]
                heapq.heapify(heap)
                while heap:
                    d, v = heapq.heappop(heap)
                    if d > dist[v]:
                        continue
                    p0 = PT[v]
                    for w in nbr8[v]:
                        if w not in zone:
                            continue
                        p1 = PT[w]
                        nd = d + ((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2 +
                                  (p0[2] - p1[2]) ** 2) ** 0.5
                        if nd < dist.get(w, 1e300):
                            dist[w] = nd
                            heapq.heappush(heap, (nd, w))
                best_key = None                          # centre cell = deepest cell of the zone
                for ff in cells:
                    cs = corners(ff)
                    d = sum(dist.get(r, 0.0) for r in cs) / len(cs)
                    x = sum(PT[r][0] for r in cs) / len(cs)
                    y = sum(PT[r][1] for r in cs) / len(cs)
                    z = sum(PT[r][2] for r in cs) / len(cs)
                    k = (round(d, 6), -((x - mx) ** 2 + (y - my) ** 2 + (z - mz) ** 2))
                    if best_key is None or k > best_key:
                        best_key, fc, cpt, room_c = k, ff, (x, y, z), d
                cs = corners(fmax)
                room_m = sum(dist.get(r, 0.0) for r in cs) / len(cs)
                return (cpt[0], cpt[1], cpt[2], room_c, mx, my, mz, room_m,
                        values[fmax], len(zone), cell_w, values[fc])

            done = {}                                    # zones already labelled (shared hills)
            for cid, (members, _b, _f) in peak_comp.items():
                seed = members[0]
                level = top = vb[seed]
                while level >= 0:
                    zone = zone_at(seed, level)
                    if zone is None:                     # contour no longer closed: give up
                        break
                    if any(vb[v] > top for v in zone):   # merged with a higher hill: that hill
                        break                            # gets its own label, not this one
                    key = (level, min(zone))
                    if key in done:                      # same zone as a higher hill: skip
                        break
                    res = analyse(zone) if len(zone) >= peak_min_cells else None
                    if res is not None and res[3] >= 0.75 * cell_w:
                        done[key] = 1
                        peaks.append(res)
                        break
                    level -= 1                           # too small / thin: next contour out

        # ---- isolines: chain segments through shared mesh edges (no JoinCurves needed)
        for li in range(1, levels):
            pts = iso_pt[li]
            for path, closed in chains(iso_adj[li]):
                if len(path) < 2:
                    continue
                buf = []
                for k in path:
                    buf.extend(pts[k])
                if closed:
                    buf.extend(pts[path[0]])
                pl = rg.Polyline(len(buf) // 3)
                pl.AddRange(point_array(buf))
                contours.append(rg.PolylineCurve(pl))
                contour_val.append(bounds[li])
                iso_raw.append((buf, bounds[li]))

    m.Normals.ComputeNormals()
    return m, contours, contour_val, iso_raw, peaks


def build_iso_labels(iso_raw, peaks, bb, diag):
    """value labels along the isolines: evenly spaced, aligned with the line,
    always readable, labels of different lines kept apart"""
    size = float(label_size_in) if label_size_in else 0.012 * diag
    spacing = float(label_spacing_in) if label_spacing_in else 0.15 * diag
    spacing = max(spacing, 1e-6)
    min_len = float(label_min_len_in) if label_min_len_in is not None else 0.3 * spacing
    planes, txts, vals = [], [], []
    pk_planes, pk_txt, pk_val, pk_pts = [], [], [], []
    if not iso_raw and not peaks:
        return planes, txts, size, vals, pk_planes, pk_txt, pk_val, pk_pts

    # plane of the map: plan (z flat) or vertical section (x or y flat)
    ex, ey, ez = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y, bb.Max.Z - bb.Min.Z
    if ez <= ex and ez <= ey:
        nrm, up = (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)       # plan: text up = +Y
    elif ey <= ex:
        nrm, up = (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)      # XZ section, seen from the front
    else:
        nrm, up = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)       # YZ section, seen from the right
    fmt = '%.' + str(max(0, dec)) + 'f'
    gap = max(0.35 * spacing, 4.0 * size)                # min distance between any two labels
    gap2 = gap * gap
    grid = {}

    def free(px, py, pz):
        ki, kj, kk = int(px // gap), int(py // gap), int(pz // gap)
        for a in (ki - 1, ki, ki + 1):
            for b in (kj - 1, kj, kj + 1):
                for c in (kk - 1, kk, kk + 1):
                    for (qx, qy, qz) in grid.get((a, b, c), ()):
                        if (px - qx) ** 2 + (py - qy) ** 2 + (pz - qz) ** 2 < gap2:
                            return False
        grid.setdefault((ki, kj, kk), []).append((px, py, pz))
        return True

    # horizontal reading direction of the map (peak labels, _label_horizontal_)
    hx = (0.0, 1.0, 0.0) if nrm[0] else (1.0, 0.0, 0.0)
    hy = up
    tol = 1e-6 * diag
    lo = (bb.Min.X - tol, bb.Min.Y - tol, bb.Min.Z - tol)
    hi = (bb.Max.X + tol, bb.Max.Y + tol, bb.Max.Z + tol)

    def fits(o, X, Y, w, h):
        """True if the whole text box (origin o, width w along X, height h along Y)
        lies inside the simulation domain"""
        mg = 0.3 * h                                     # safety margin around the text;
        # vertical extent -h..2h covers both bottom- and top-anchored text displays
        for a, b in ((-mg, -h - mg), (w + mg, -h - mg), (-mg, h + mg), (w + mg, h + mg)):
            for c in range(3):
                v = o[c] + X[c] * a + Y[c] * b
                if v < lo[c] or v > hi[c]:
                    return False
        return True

    def clamp_box(o, X, Y, w, h):
        """shift a text box (axis-aligned X / Y) back inside the domain"""
        mg = 0.5 * h
        o = list(o)
        for c in range(3):
            ext = abs(X[c]) * w + abs(Y[c]) * h
            if o[c] + ext + mg * (abs(X[c]) + abs(Y[c])) > hi[c]:
                o[c] = hi[c] - ext - mg * (abs(X[c]) + abs(Y[c]))
            if o[c] - mg * (abs(X[c]) + abs(Y[c])) < lo[c]:
                o[c] = lo[c] + mg * (abs(X[c]) + abs(Y[c]))
        return o

    # typical cell width (for the thin-strip test of the peaks)
    cell_w = max(peaks[0][10], 1e-9) if peaks else 1e-9

    # peaks first (one label at the maximum of each innermost closed contour)
    if peaks_on:
        use_max = peak_value == 'max'
        for (cx, cy, cz, room_c, mx, my, mz, room_m, vmax_c, ncell, _cw, vcen) in \
                sorted(peaks, key=lambda p: -(p[8] if use_max else p[11])):
            if ncell < peak_min_cells:
                continue
            val = vmax_c if use_max else vcen            # value shown on the label
            txt = fmt % val
            half_w = 0.33 * size * len(txt)
            if peak_pos == 'max':
                px, py, pz, room, dy_ = mx, my, mz, room_m, 0.0
            elif peak_pos == 'above':                    # text sits just above the max cell
                px, py, pz, room, dy_ = mx, my, mz, None, 0.9 * size
            else:
                px, py, pz, room, dy_ = cx, cy, cz, room_c, 0.0
            if room_c < 0.75 * cell_w:                   # one-cell-wide strip: no real centre
                continue
            # text must fit inside its contour: half diagonal of the text box <= room
            if peak_fit and room is not None and \
                    (half_w * half_w + 0.25 * size * size) ** 0.5 > room:
                continue
            if not free(px, py, pz):                     # higher peaks win, no overlaps
                continue
            o = (px - hx[0] * half_w - hy[0] * (0.5 * size - dy_),
                 py - hx[1] * half_w - hy[1] * (0.5 * size - dy_),
                 pz - hx[2] * half_w - hy[2] * (0.5 * size - dy_))
            ox, oy, oz = clamp_box(o, hx, hy, 2 * half_w, size)
            pk_planes.append(rg.Plane(rg.Point3d(ox, oy, oz), rg.Vector3d(*hx), rg.Vector3d(*hy)))
            pk_txt.append(txt)
            pk_val.append(val)
            pk_pts.append(rg.Point3d(mx, my, mz) if use_max else rg.Point3d(cx, cy, cz))

    # longest lines first, so they get their labels before short neighbours
    order = []
    for buf, val in iso_raw:
        n = len(buf) // 3
        cum = [0.0]
        for i in range(n - 1):
            q = 3 * i
            cum.append(cum[-1] + ((buf[q + 3] - buf[q]) ** 2 + (buf[q + 4] - buf[q + 1]) ** 2 +
                                  (buf[q + 5] - buf[q + 2]) ** 2) ** 0.5)
        if cum[-1] >= min_len and n >= 2:
            order.append((cum[-1], buf, cum, val))
    order.sort(key=lambda x: -x[0])

    for L, buf, cum, val in order:
        txt = fmt % val
        half_w = 0.33 * size * len(txt)                   # ~ half text width
        k = max(1, int(L // spacing))
        i = 0
        for j in range(k):
            s_at = (j + 0.5) * L / k
            while i < len(cum) - 2 and cum[i + 1] < s_at:
                i += 1
            q = 3 * i
            seg = cum[i + 1] - cum[i]
            t = (s_at - cum[i]) / seg if seg > 1e-12 else 0.0
            dx, dy, dz = buf[q + 3] - buf[q], buf[q + 4] - buf[q + 1], buf[q + 5] - buf[q + 2]
            px, py, pz = buf[q] + dx * t, buf[q + 1] + dy * t, buf[q + 2] + dz * t
            ln = (dx * dx + dy * dy + dz * dz) ** 0.5
            if ln < 1e-12:
                continue
            if label_horizontal:                         # straight text, centred on the line
                dx, dy, dz = hx
                yx, yy, yz = hy
            else:                                        # text follows the line
                dx, dy, dz = dx / ln, dy / ln, dz / ln
                yx = nrm[1] * dz - nrm[2] * dy            # y = normal x tangent
                yy = nrm[2] * dx - nrm[0] * dz
                yz = nrm[0] * dy - nrm[1] * dx
                if yx * up[0] + yy * up[1] + yz * up[2] < 0:   # keep the text readable
                    dx, dy, dz, yx, yy, yz = -dx, -dy, -dz, -yx, -yy, -yz
            ox = px - dx * half_w - yx * 0.5 * size      # centre the text on the line
            oy = py - dy * half_w - yy * 0.5 * size
            oz = pz - dz * half_w - yz * 0.5 * size
            if not fits((ox, oy, oz), (dx, dy, dz), (yx, yy, yz), 2 * half_w, size):
                continue                                 # text would stick out of the domain
            if not free(px, py, pz):
                continue
            planes.append(rg.Plane(rg.Point3d(ox, oy, oz), rg.Vector3d(dx, dy, dz),
                                   rg.Vector3d(yx, yy, yz)))
            txts.append(txt)
            vals.append(val)
    return planes, txts, size, vals, pk_planes, pk_txt, pk_val, pk_pts


def build_legend(vmin, vmax, lut, bb, diag, dmin, dmax):
    span = 255.0 / (vmax - vmin)

    def col(v):
        s = int((v - vmin) * span + 0.5)
        return lut[0 if s < 0 else (255 if s > 255 else s)]

    h = 0.4 * diag * legend_scale
    w = 0.075 * h
    text_size = 0.5 * w
    if legend_pt:
        lp = legend_pt
    elif title_xz:                                     # upright legend, bottom at the map base
        lp = rg.Point3d(bb.Max.X + 0.05 * diag, bb.Min.Y,
                        bb.Min.Z if is_xz_section(bb) else bb.Max.Z)
    else:
        lp = rg.Point3d(bb.Max.X + 0.05 * diag, bb.Min.Y, bb.Max.Z)

    def P(u, v):
        """legend coordinates (u = right, v = up) -> world point, flat XY or upright XZ"""
        if title_xz:
            return rg.Point3d(lp.X + u, lp.Y, lp.Z + v)
        return rg.Point3d(lp.X + u, lp.Y + v, lp.Z)

    contour_mode = mode == 'contour'
    nseg = levels if contour_mode else 32
    legend = rg.Mesh()
    lcols = []
    for s in range(nseg):
        y0 = h * s / float(nseg)
        y1 = h * (s + 1) / float(nseg)
        if contour_mode:
            c0 = c1 = col(vmin + (vmax - vmin) * (s + 0.5) / nseg)
        else:
            c0 = col(vmin + (vmax - vmin) * s / float(nseg))
            c1 = col(vmin + (vmax - vmin) * (s + 1) / float(nseg))
        a = legend.Vertices.Count
        legend.Vertices.Add(P(0.0, y0))
        legend.Vertices.Add(P(w, y0))
        legend.Vertices.Add(P(w, y1))
        legend.Vertices.Add(P(0.0, y1))
        lcols.extend((c0, c0, c1, c1))
        legend.Faces.AddFace(a, a + 1, a + 2, a + 3)
    legend.VertexColors.SetColors(to_color_array(lcols))
    legend.Normals.ComputeNormals()

    fmt = '%.' + str(max(0, dec)) + 'f'
    nlab = levels + 1 if contour_mode else legend_n        # number of tick values
    tag_pts, tag_txt = [], []
    lx = 1.5 * w                                           # local u of the value labels
    if range_labels:
        nr = nlab - 1                                      # one range per interval
        tol = 1e-9 * (vmax - vmin)
        for s in range(nr):
            a = vmin + (vmax - vmin) * s / float(nr)
            b = vmin + (vmax - vmin) * (s + 1) / float(nr)
            if s == 0 and dmin < vmin - tol:
                txt = '< ' + fmt % b
            elif s == nr - 1 and dmax > vmax + tol:
                txt = '>= ' + fmt % a
            else:
                txt = fmt % a + ' - ' + fmt % b
            t = (s + 0.5) / nr                             # middle of the interval
            tag_pts.append(P(lx, h * t - 0.5 * text_size))
            tag_txt.append(txt)
    else:
        for s in range(nlab):
            t = s / float(nlab - 1)
            tag_pts.append(P(lx, h * t - 0.5 * text_size))
            tag_txt.append(fmt % (vmin + (vmax - vmin) * t))

    # title: one tag per line, bottom-up (last line sits just above the bar)
    if title_in:
        lines = split_lines(title_in)
        line_h = 1.5 * text_size
        y = h + 1.0 * text_size                            # baseline of the bottom line
        for ln in reversed(lines):
            if ln.strip():
                tag_pts.append(P(0.0, y))
                tag_txt.append(ln)
            y += line_h
    return legend, tag_pts, tag_txt, text_size


def split_lines(txt):
    lines = str(txt).replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def build_global_title(bb, diag):
    """global title under the mesh: one tag per line, first line on top"""
    size = 0.025 * diag * gtitle_scale
    if not gtitle_in:
        return [], [], size
    line_h = 1.5 * size
    lines = split_lines(gtitle_in)
    pts, txt = [], []
    if title_xz:                                         # upright: lines stacked along -Z
        if gtitle_pt:
            x, y, z = gtitle_pt.X, gtitle_pt.Y, gtitle_pt.Z - size     # baseline of line 1
        elif is_xz_section(bb):                          # under the section
            x, y, z = bb.Min.X, bb.Min.Y, bb.Min.Z - 0.04 * diag - size
        else:                                            # plan: in front of the map, last line
            x, y = bb.Min.X, bb.Min.Y - 0.04 * diag      # standing on the map level
            z = bb.Max.Z + (len(lines) - 1) * line_h
        for ln in lines:
            if ln.strip():
                pts.append(rg.Point3d(x, y, z))
                txt.append(ln)
            z -= line_h
        return pts, txt, size
    if gtitle_pt:
        x, y, z = gtitle_pt.X, gtitle_pt.Y - size, gtitle_pt.Z      # baseline of line 1
    else:
        x, y, z = bb.Min.X, bb.Min.Y - 0.04 * diag - size, bb.Max.Z
    for ln in lines:
        if ln.strip():
            pts.append(rg.Point3d(x, y, z))
            txt.append(ln)
        y -= line_h
    return pts, txt, size


def is_xz_section(bb):
    """True if the map itself is a vertical XZ section (flat in Y)"""
    ex, ey, ez = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y, bb.Max.Z - bb.Min.Z
    return ey <= 1e-6 * (ex + ez + 1.0) and ez > ey


def to_xz_planes(pts):
    """text locations -> planes in the vertical XZ plane (x = reading direction, y = up)"""
    return [rg.Plane(p, rg.Vector3d.XAxis, rg.Vector3d.ZAxis) for p in pts]


def cache_slot():
    """per-component sticky key (None if not available)"""
    try:
        return 'envimet_heatmap_' + str(ghenv.Component.InstanceGuid)  # noqa: F821
    except Exception:
        return None


def build():
    t_start = time.time()
    if mesh_in is None or not vals_in:
        raise ValueError('Connect _mesh and _values (set _values to List Access).')
    values = [float(v) for v in vals_in]
    nf = mesh_in.Faces.Count
    if len(values) != nf:
        raise ValueError('%d values for %d mesh faces - connect mesh and values from the '
                         'same reader component.' % (len(values), nf))
    if filled_in and len(filled_in) == nf:
        filled = [bool(f) for f in filled_in]
    else:
        if filled_in:
            print('WARNING: _filled_ has %d items for %d faces - ignored' % (len(filled_in), nf))
        filled = [False] * nf

    vmin = float(vmin_in) if vmin_in is not None else min(values)
    vmax = float(vmax_in) if vmax_in is not None else max(values)
    if vmax - vmin < 1e-9:
        vmax = vmin + 1e-6

    pal = [(c.R, c.G, c.B) for c in cols_in] if cols_in else LB_COLORS
    if len(pal) < 2:
        pal = LB_COLORS
    lut = make_lut(pal)

    bb = mesh_in.GetBoundingBox(True)
    diag = bb.Diagonal.Length or 1.0

    # ---- geometry (cached: legend-only changes skip this)
    key = ('v9', mode, levels if mode == 'contour' else 0,
           smooth_it if mode != 'cells' else 0, vmin, vmax, tuple(pal), nf,
           mesh_in.Vertices.Count, str(bb.Min), str(bb.Max),
           hash(tuple(values)), hash(tuple(filled)))
    slot = cache_slot()
    cached = sc.sticky.get(slot) if (sc is not None and slot) else None
    if cached is not None and cached[0] == key:
        m, contours, contour_val, iso_raw, peaks = cached[1:6]
        src = 'cached'
    else:
        m, contours, contour_val, iso_raw, peaks = build_mesh(values, filled, vmin, vmax, lut,
                                                               bb, diag)
        if sc is not None and slot:
            sc.sticky[slot] = (key, m, contours, contour_val, iso_raw, peaks)
        src = 'computed'

    legend, tag_pts, tag_txt, text_size = build_legend(vmin, vmax, lut, bb, diag,
                                                       min(values), max(values))
    title_pts, title_txt, title_size = build_global_title(bb, diag)
    if title_xz:                                         # Text Tag 3D needs planes to stand up
        tag_pts = to_xz_planes(tag_pts)
        title_pts = to_xz_planes(title_pts)
    (iso_planes, iso_txt, iso_size, iso_val,
     peak_planes, peak_txt, peak_val, peak_pts) = build_iso_labels(iso_raw, peaks, bb, diag)

    print('%s%s | %d cells | range %.2f - %.2f%s | %s in %.0f ms' % (
        mode, (' (smooth x%d)' % smooth_it) if smooth_it and mode != 'cells' else '',
        nf, vmin, vmax,
        (' | %d isolines, %d labels, %d peaks' % (len(contours), len(iso_txt), len(peak_txt)))
        if mode == 'contour' else '',
        src, (time.time() - t_start) * 1000.0))
    return dict(mesh=m, contours=contours, contour_val=contour_val, legend=legend,
                tag_pts=tag_pts, tag_txt=tag_txt, text_size=text_size, v_range=(vmin, vmax),
                title_pts=title_pts, title_txt=title_txt, title_size=title_size,
                iso_planes=iso_planes, iso_txt=iso_txt, iso_size=iso_size, iso_val=iso_val,
                peak_planes=peak_planes, peak_txt=peak_txt, peak_val=peak_val, peak_pts=peak_pts)


set_tooltips(TIPS_IN, TIPS_OUT,
             'Meerkat - fast heatmap / contour map with legend for ENVI-met data')
report_inputs()
if run:
    result = build()
else:
    print('_run is False - nothing computed, outputs empty')
    result = dict((n, None) for n in OUTS)
mesh, contours, contour_val = result['mesh'], result['contours'], result['contour_val']
legend, tag_pts, tag_txt = result['legend'], result['tag_pts'], result['tag_txt']
text_size, v_range = result['text_size'], result['v_range']
title_pts, title_txt, title_size = result['title_pts'], result['title_txt'], result['title_size']
iso_planes, iso_txt, iso_size, iso_val = (result['iso_planes'], result['iso_txt'],
                                          result['iso_size'], result['iso_val'])
peak_planes, peak_txt, peak_val, peak_pts = (result['peak_planes'], result['peak_txt'],
                                             result['peak_val'], result['peak_pts'])