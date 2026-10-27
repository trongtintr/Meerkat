"""Meerkat palette: modern colour palettes for heatmaps / streamlines
Runs in GhPython (IronPython 2.7, Rhino 7) and Python 3 (Rhino 8).

Outputs a list of colours that can be connected to any _colors_ input
(envimet_heatmap.py, envimet_streamline_colors.py, LB Legend Parameters _colors_).

Inputs (all optional):
    _palette_ : str / int - palette (default "viridis"). Leave it unconnected: a drop-down
                            list with all 70 palettes is created. Also accepts a name ("_r" =
                            reversed) or an index 0-69 from a Number Slider
    _reverse_ : bool  - reverse the palette (default False)
    _n_       : int   - number of output colours (default 11; resampled smoothly)
    _pt_      : Point3d - base point of the preview swatches (default origin)
Outputs:
    colors    : list of colours (low -> high)
    names     : all available palette names
    preview   : mesh with one coloured strip per palette (name order = names)
"""

# ---- tooltips (shown when hovering inputs / outputs in Grasshopper) ----------------------
COMPONENT_DESC = 'Meerkat palette: modern colour palettes for heatmaps / streamlines'
INPUT_TIPS = {'_palette_': 'palette (default "viridis"). Leave it unconnected: a drop-down list with all 70 '
                  'palettes is created. Also accepts a name ("_r" = reversed) or an index 0-69 '
                  'from a Number Slider [str / int]',
     '_reverse_': 'reverse the palette (default False) [bool]',
     '_n_': 'number of output colours (default 11; resampled smoothly) [int]',
     '_pt_': 'base point of the preview swatches (default origin) [Point3d]'}
OUTPUT_TIPS = {'colors': 'list of colours (low -> high)',
     'names': 'all available palette names',
     'preview': 'mesh with one coloured strip per palette (name order = names)'}


def _apply_tooltips():
    try:
        comp = ghenv.Component
    except Exception:
        return                                        # not running inside Grasshopper
    try:
        if COMPONENT_DESC and comp.Description != COMPONENT_DESC:
            comp.Description = COMPONENT_DESC
        for params, tips in ((comp.Params.Input, INPUT_TIPS), (comp.Params.Output, OUTPUT_TIPS)):
            for p in params:
                tip = tips.get(p.NickName) or tips.get(p.Name)
                if tip and p.Description != tip:
                    p.Description = tip
    except Exception:
        pass


_apply_tooltips()
# ---------------------------------------------------------------------------------------
import Rhino.Geometry as rg
import System.Drawing as sd

# ---- colour palettes (low -> high). Add "_r" to a name to reverse it, e.g. "viridis_r".
# viridis/magma/inferno/plasma/cividis/turbo: matplotlib (CC0 / Apache 2.0);
# rdylbu/spectral/rdbu/ylorrd/blues: ColorBrewer (Apache 2.0, Cynthia Brewer);
# coolwarm: K. Moreland; ladybug: Ladybug Tools default; thermal, wind, dusk, delta: Meerkat;
# puor/brbg/piyg/prgn: ColorBrewer; vlag/icefire: seaborn (BSD); berlin: F. Crameri (via
# matplotlib); bwr: matplotlib.
PALETTES = {
    'ladybug': [(75, 107, 169), (115, 147, 202), (170, 200, 247), (193, 213, 208), (245, 239, 103),
                (252, 230, 74), (239, 156, 21), (234, 123, 0), (234, 74, 0), (234, 38, 0)],
    'viridis': [(68, 1, 84), (72, 36, 117), (65, 68, 135), (53, 95, 141), (42, 120, 142), (33, 145, 140),
                (34, 168, 132), (68, 191, 112), (122, 209, 81), (189, 223, 38), (253, 231, 37)],
    'magma': [(0, 0, 4), (20, 14, 54), (59, 15, 112), (100, 26, 128), (140, 41, 129), (183, 55, 121),
              (222, 73, 104), (247, 112, 92), (254, 159, 109), (254, 207, 146), (252, 253, 191)],
    'inferno': [(0, 0, 4), (22, 11, 57), (66, 10, 104), (106, 23, 110), (147, 38, 103), (188, 55, 84),
                (221, 81, 58), (243, 120, 25), (252, 165, 10), (246, 215, 70), (252, 255, 164)],
    'plasma': [(13, 8, 135), (65, 4, 157), (106, 0, 168), (143, 13, 164), (177, 42, 144), (204, 71, 120),
               (225, 100, 98), (242, 132, 75), (252, 166, 54), (252, 206, 37), (240, 249, 33)],
    'cividis': [(0, 34, 78), (8, 51, 112), (53, 69, 108), (79, 87, 108), (102, 105, 112), (125, 124, 120),
                (148, 142, 119), (174, 163, 113), (200, 184, 102), (229, 207, 82), (254, 232, 56)],
    'turbo': [(48, 18, 59), (69, 89, 203), (62, 155, 254), (25, 213, 205), (70, 248, 132), (164, 252, 60),
              (225, 221, 55), (254, 164, 49), (240, 91, 18), (195, 37, 3), (122, 4, 3)],
    'rdylbu': [(49, 54, 149), (69, 116, 179), (116, 173, 209), (170, 216, 233), (224, 243, 248),
               (255, 254, 190), (254, 224, 144), (253, 173, 96), (244, 109, 67), (214, 47, 39), (165, 0, 38)],
    'spectral': [(94, 79, 162), (51, 135, 188), (102, 194, 165), (170, 220, 164), (230, 245, 152),
                 (255, 254, 190), (254, 224, 139), (253, 173, 96), (244, 109, 67), (212, 61, 79), (158, 1, 66)],
    'coolwarm': [(59, 76, 192), (89, 119, 227), (123, 159, 249), (158, 190, 255), (192, 212, 245),
                 (221, 220, 220), (242, 203, 183), (247, 172, 142), (238, 132, 104), (214, 82, 68), (180, 4, 38)],
    'rdbu': [(5, 48, 97), (32, 101, 171), (67, 147, 195), (144, 196, 221), (209, 229, 240), (247, 246, 246),
             (253, 219, 199), (243, 164, 129), (214, 96, 77), (177, 24, 43), (103, 0, 31)],
    'ylorrd': [(255, 255, 204), (255, 241, 169), (254, 225, 135), (254, 202, 102), (254, 171, 73),
               (253, 140, 60), (252, 91, 46), (237, 46, 33), (212, 16, 32), (176, 0, 38), (128, 0, 38)],
    'blues': [(247, 251, 255), (227, 238, 249), (208, 225, 242), (183, 212, 234), (148, 196, 223),
              (106, 174, 214), (74, 152, 201), (46, 126, 188), (23, 100, 171), (8, 74, 145), (8, 48, 107)],
    'thermal': [(23, 55, 94), (40, 98, 145), (72, 148, 170), (146, 197, 190), (232, 226, 196),
                (244, 190, 124), (229, 128, 77), (196, 64, 56), (128, 20, 46)],
    'wind': [(245, 250, 250), (200, 232, 230), (140, 205, 205), (70, 165, 180), (35, 120, 160),
             (30, 75, 130), (25, 40, 90)],
    'dusk': [(44, 30, 80), (92, 55, 125), (150, 70, 140), (205, 96, 120), (240, 140, 110),
             (250, 196, 132), (252, 240, 170)],
    # ---- diverging (for differences / comparisons around 0): negative = cool, positive = warm
    'delta': [(17, 72, 110), (39, 116, 156), (98, 166, 190), (170, 210, 220), (232, 242, 244),
              (250, 248, 245), (250, 224, 210), (240, 170, 140), (214, 106, 82), (168, 50, 48),
              (110, 18, 34)],
    'vlag': [(35, 105, 189), (91, 132, 189), (135, 160, 196), (175, 188, 209), (217, 220, 229),
             (250, 245, 244), (236, 211, 210), (219, 171, 168), (204, 133, 130), (187, 94, 93),
             (169, 55, 59)],
    'puor': [(45, 0, 75), (83, 38, 135), (128, 115, 172), (177, 170, 209), (216, 218, 235),
             (247, 247, 246), (254, 224, 182), (252, 183, 97), (224, 130, 20), (178, 87, 6),
             (127, 59, 8)],
    'brbg': [(0, 60, 48), (1, 101, 93), (53, 151, 143), (127, 204, 192), (199, 234, 229),
             (245, 245, 244), (246, 232, 195), (222, 193, 123), (191, 129, 45), (139, 80, 10),
             (84, 48, 5)],
    'piyg': [(142, 1, 82), (196, 26, 124), (222, 119, 174), (241, 181, 217), (253, 224, 239),
             (247, 247, 246), (230, 245, 208), (183, 224, 133), (127, 188, 65), (76, 145, 33),
             (39, 100, 25)],
    'prgn': [(64, 0, 75), (117, 41, 130), (153, 112, 171), (193, 164, 206), (231, 212, 232),
             (246, 247, 246), (217, 240, 211), (165, 218, 159), (90, 174, 97), (26, 119, 54),
             (0, 68, 27)],
    'icefire': [(189, 231, 219), (117, 184, 206), (56, 133, 208), (74, 79, 165), (48, 46, 74),
                (31, 30, 30), (74, 37, 46), (147, 46, 68), (211, 73, 54), (241, 143, 81),
                (255, 212, 172)],
    'berlin': [(158, 176, 255), (98, 166, 224), (50, 128, 166), (32, 82, 106), (17, 39, 50),
               (25, 12, 9), (55, 16, 0), (97, 32, 11), (150, 74, 54), (202, 123, 113),
               (255, 173, 173)],
    'bwr': [(0, 0, 255), (50, 50, 255), (102, 102, 255), (152, 152, 255), (204, 204, 255),
            (255, 254, 254), (255, 204, 204), (255, 152, 152), (255, 102, 102), (255, 50, 50),
            (255, 0, 0)],
    # ---- Meerkat originals
    'urban_heat': [(52, 73, 94), (84, 110, 122), (130, 150, 150), (190, 190, 170), (235, 215, 170),
                   (240, 180, 120), (225, 130, 80), (190, 80, 60), (130, 40, 45)],
    'sunrise': [(25, 35, 80), (70, 55, 130), (150, 70, 150), (220, 90, 120), (250, 135, 90),
                (252, 190, 90), (252, 240, 160)],
    'ocean': [(8, 29, 58), (16, 62, 104), (23, 104, 140), (30, 145, 160), (80, 185, 175),
              (160, 220, 200), (230, 248, 240)],
    'forest': [(20, 40, 25), (35, 75, 40), (60, 110, 55), (100, 145, 70), (150, 180, 95),
               (205, 215, 140), (245, 245, 200)],
    'aurora': [(20, 20, 50), (40, 60, 120), (30, 130, 150), (60, 190, 140), (170, 225, 110),
               (245, 240, 140)],
    'neon': [(15, 10, 40), (80, 20, 140), (190, 30, 170), (255, 70, 120), (255, 150, 60),
             (255, 230, 80)],
    'heat_grey': [(225, 225, 225), (200, 200, 200), (170, 170, 170), (200, 150, 130),
                  (225, 110, 80), (200, 50, 40), (140, 20, 30)],
    'utci': [(0, 32, 96), (0, 64, 160), (0, 112, 224), (64, 160, 255), (160, 208, 255),
             (102, 189, 99), (254, 224, 139), (253, 174, 97), (244, 109, 67), (215, 48, 39),
             (140, 10, 30)],
    # ---- more perceptual / sequential / diverging (seaborn BSD, cmocean MIT, ColorBrewer
    #      Apache 2.0, matplotlib)
    'rocket': [(3, 5, 26), (37, 20, 51), (76, 29, 75), (117, 31, 88), (161, 26, 91), (203, 27, 79),
               (232, 63, 63), (243, 113, 77), (246, 156, 115), (247, 198, 166), (250, 235, 221)],
    'mako': [(11, 4, 5), (37, 23, 41), (56, 42, 84), (65, 63, 128), (57, 93, 156), (53, 123, 163),
             (52, 151, 169), (62, 180, 173), (96, 206, 172), (169, 225, 189), (222, 245, 229)],
    'flare': [(75, 35, 98), (98, 41, 106), (122, 46, 112), (146, 51, 113), (170, 58, 110),
              (194, 65, 103), (214, 79, 95), (226, 101, 92), (231, 126, 99), (235, 152, 114),
              (237, 176, 129)],
    'crest': [(44, 49, 114), (40, 67, 123), (33, 85, 132), (28, 102, 137), (36, 118, 139),
              (52, 133, 141), (68, 148, 143), (87, 164, 144), (109, 178, 144), (137, 191, 145),
              (165, 205, 144)],
    'cmo_thermal': [(4, 35, 51), (15, 50, 106), (64, 52, 159), (103, 67, 150), (139, 83, 141),
                    (177, 95, 130), (214, 108, 108), (243, 130, 77), (252, 166, 60),
                    (247, 208, 69), (232, 250, 91)],
    'cmo_solar': [(51, 20, 24), (82, 30, 34), (115, 39, 36), (143, 52, 31), (165, 74, 23),
                  (182, 100, 19), (196, 127, 21), (207, 156, 29), (216, 186, 42), (222, 219, 58),
                  (225, 253, 75)],
    'cmo_matter': [(47, 15, 62), (79, 22, 82), (114, 26, 96), (147, 32, 99), (179, 46, 95),
                   (207, 68, 86), (226, 98, 83), (238, 133, 94), (245, 167, 115), (250, 202, 144),
                   (254, 237, 176)],
    'cmo_amp': [(241, 237, 236), (229, 207, 201), (220, 177, 163), (211, 149, 127), (202, 119, 91),
                (192, 88, 59), (179, 56, 38), (157, 25, 38), (127, 14, 41), (92, 14, 33),
                (60, 9, 18)],
    'cmo_haline': [(42, 24, 108), (41, 39, 162), (13, 78, 150), (24, 102, 140), (45, 124, 137),
                   (60, 147, 135), (74, 170, 129), (101, 193, 114), (148, 211, 93),
                   (208, 224, 109), (253, 239, 154)],
    'cmo_ice': [(4, 6, 19), (27, 27, 55), (48, 47, 95), (61, 67, 137), (62, 94, 169),
                (66, 123, 183), (82, 150, 193), (107, 177, 203), (140, 203, 214), (188, 228, 231),
                (234, 253, 253)],
    'cmo_deep': [(40, 26, 44), (56, 45, 81), (65, 64, 123), (62, 90, 146), (64, 117, 152),
                 (72, 143, 158), (82, 168, 163), (102, 194, 164), (146, 216, 164), (202, 235, 178),
                 (253, 254, 204)],
    'cmo_dense': [(230, 241, 241), (188, 220, 229), (150, 197, 226), (123, 173, 228),
                  (115, 144, 227), (120, 113, 213), (121, 84, 187), (116, 58, 152), (104, 36, 113),
                  (83, 21, 70), (54, 14, 36)],
    'cmo_speed': [(255, 253, 205), (238, 223, 152), (216, 197, 95), (184, 178, 47), (142, 162, 11),
                  (95, 146, 12), (50, 128, 31), (15, 107, 43), (16, 84, 44), (25, 59, 35),
                  (23, 35, 19)],
    'cmo_tempo': [(255, 246, 244), (220, 223, 208), (182, 203, 175), (141, 185, 151),
                  (93, 167, 134), (42, 147, 127), (17, 125, 121), (24, 101, 110), (28, 77, 97),
                  (26, 54, 81), (21, 29, 68)],
    'cmo_algae': [(215, 249, 208), (184, 227, 172), (150, 205, 138), (114, 187, 108),
                  (68, 168, 85), (18, 148, 80), (9, 125, 75), (21, 102, 65), (26, 80, 52),
                  (24, 58, 37), (18, 36, 20)],
    'cmo_rain': [(238, 237, 243), (222, 211, 201), (203, 186, 152), (161, 172, 130),
                 (115, 157, 117), (61, 142, 110), (12, 123, 110), (8, 99, 107), (30, 75, 95),
                 (37, 51, 75), (34, 27, 56)],
    'cmo_turbid': [(233, 246, 171), (219, 217, 135), (207, 188, 102), (196, 161, 77),
                   (181, 135, 64), (161, 112, 59), (138, 94, 58), (112, 77, 55), (86, 62, 48),
                   (59, 47, 39), (34, 31, 27)],
    'cmo_balance': [(24, 28, 67), (41, 62, 151), (22, 112, 188), (89, 156, 187), (170, 194, 203),
                    (241, 236, 235), (220, 178, 164), (202, 118, 91), (179, 56, 38), (126, 14, 41),
                    (60, 9, 18)],
    'cmo_curl': [(21, 29, 68), (28, 77, 96), (17, 125, 121), (92, 167, 134), (182, 203, 176),
                 (253, 245, 244), (230, 184, 162), (211, 118, 105), (174, 64, 96), (117, 25, 93),
                 (52, 13, 53)],
    'cmo_diff': [(8, 35, 64), (33, 77, 106), (90, 116, 135), (141, 156, 167), (198, 202, 207),
                 (246, 241, 240), (206, 199, 184), (161, 150, 121), (122, 109, 65), (75, 71, 28),
                 (28, 34, 7)],
    'cmo_tarn': [(23, 35, 14), (60, 77, 13), (132, 106, 37), (203, 132, 72), (227, 191, 163),
                 (252, 247, 246), (203, 204, 170), (124, 164, 144), (46, 126, 126), (21, 79, 106),
                 (16, 30, 79)],
    'reds': [(255, 245, 240), (254, 229, 216), (253, 202, 181), (252, 171, 143), (252, 138, 106),
             (251, 105, 74), (241, 68, 50), (217, 37, 35), (188, 20, 26), (152, 12, 19),
             (103, 0, 13)],
    'oranges': [(255, 245, 235), (254, 233, 212), (253, 217, 180), (253, 195, 141), (253, 167, 98),
                (253, 140, 59), (243, 112, 27), (226, 85, 8), (197, 65, 2), (158, 51, 3),
                (127, 39, 4)],
    'greens': [(247, 252, 245), (233, 247, 229), (211, 238, 205), (184, 227, 178), (152, 213, 148),
               (115, 196, 118), (75, 176, 98), (47, 151, 78), (21, 127, 59), (0, 100, 40),
               (0, 68, 27)],
    'purples': [(252, 251, 253), (242, 240, 247), (226, 226, 239), (206, 207, 229),
                (182, 182, 216), (158, 154, 200), (134, 131, 189), (114, 98, 172), (97, 64, 155),
                (79, 31, 139), (63, 0, 125)],
    'greys': [(255, 255, 255), (243, 243, 243), (226, 226, 226), (206, 206, 206), (181, 181, 181),
              (149, 149, 149), (122, 122, 122), (95, 95, 95), (64, 64, 64), (29, 29, 29),
              (0, 0, 0)],
    'orrd': [(255, 247, 236), (254, 235, 208), (253, 220, 175), (253, 202, 148), (253, 178, 123),
             (252, 140, 89), (242, 109, 75), (224, 68, 47), (201, 29, 19), (168, 0, 0),
             (127, 0, 0)],
    'ylgnbu': [(255, 255, 217), (241, 250, 186), (214, 239, 179), (171, 222, 183), (115, 200, 189),
               (64, 181, 196), (36, 152, 193), (32, 114, 177), (35, 77, 160), (31, 47, 135),
               (8, 29, 88)],
    'ylgn': [(255, 255, 229), (249, 253, 194), (229, 245, 172), (200, 233, 155), (162, 216, 138),
             (119, 198, 121), (76, 176, 99), (47, 147, 77), (21, 121, 62), (0, 96, 52),
             (0, 69, 41)],
    'gnbu': [(247, 252, 240), (229, 245, 224), (212, 238, 206), (190, 230, 191), (159, 218, 184),
             (122, 204, 196), (87, 184, 208), (56, 155, 198), (29, 126, 183), (8, 95, 163),
             (8, 64, 129)],
    'pubugn': [(255, 247, 251), (240, 231, 242), (219, 216, 234), (192, 201, 226), (153, 185, 217),
               (102, 169, 207), (64, 149, 195), (22, 135, 159), (2, 121, 118), (1, 100, 81),
               (1, 70, 54)],
    'bupu': [(247, 252, 253), (229, 239, 246), (204, 221, 236), (178, 202, 225), (154, 180, 214),
             (140, 149, 198), (140, 116, 181), (138, 81, 165), (133, 45, 144), (118, 12, 113),
             (77, 0, 75)],
    'rdpu': [(255, 247, 243), (253, 229, 226), (252, 208, 204), (251, 182, 188), (249, 148, 177),
             (247, 103, 161), (226, 62, 153), (192, 21, 136), (153, 1, 123), (111, 1, 116),
             (73, 0, 106)],
    'cubehelix': [(0, 0, 0), (26, 20, 47), (22, 61, 78), (30, 101, 66), (84, 121, 47),
                  (161, 121, 74), (208, 126, 147), (207, 157, 219), (193, 202, 243),
                  (211, 238, 239), (255, 255, 255)],
    'managua': [(255, 207, 103), (224, 159, 87), (193, 116, 73), (160, 81, 62), (119, 51, 57),
                (87, 41, 73), (76, 61, 115), (81, 99, 162), (95, 137, 195), (111, 182, 226),
                (129, 231, 255)],
    'vanimo': [(255, 205, 253), (216, 137, 202), (173, 83, 154), (116, 46, 100), (51, 23, 44),
               (26, 21, 19), (35, 44, 20), (65, 90, 31), (98, 135, 47), (138, 188, 83),
               (190, 253, 165)],
    'rdgy': [(26, 26, 26), (76, 76, 76), (135, 135, 135), (185, 185, 185), (224, 224, 224),
             (255, 254, 254), (253, 219, 199), (243, 164, 129), (214, 96, 77), (177, 24, 43),
             (103, 0, 31)],
}


def get_palette(name):
    """palette name (optionally with '_r') -> list of (r, g, b); None if unknown"""
    key = str(name or '').strip().lower().replace(' ', '').replace('-', '')
    rev = key.endswith('_r')
    if rev:
        key = key[:-2]
    pal = PALETTES.get(key)
    if pal is None:
        return None
    return list(reversed(pal)) if rev else list(pal)


PALETTE_ORDER = ['ladybug', 'thermal', 'turbo', 'rdylbu', 'spectral', 'coolwarm', 'rdbu',
                 'viridis', 'magma', 'inferno', 'plasma', 'cividis', 'ylorrd', 'dusk',
                 'wind', 'blues',
                 # diverging, index 16-24
                 'delta', 'vlag', 'puor', 'brbg', 'piyg', 'prgn', 'icefire', 'berlin', 'bwr',
                 # Meerkat originals, index 25-32
                 'urban_heat', 'sunrise', 'ocean', 'forest', 'aurora', 'neon', 'heat_grey', 'utci',
                 # perceptual, index 33-36
                 'rocket', 'mako', 'flare', 'crest',
                 # cmocean, index 37-53
                 'cmo_thermal', 'cmo_solar', 'cmo_matter', 'cmo_amp', 'cmo_haline', 'cmo_ice',
                 'cmo_deep', 'cmo_dense', 'cmo_speed', 'cmo_tempo', 'cmo_algae', 'cmo_rain',
                 'cmo_turbid', 'cmo_balance', 'cmo_curl', 'cmo_diff', 'cmo_tarn',
                 # ColorBrewer sequential, index 54-65
                 'reds', 'oranges', 'greens', 'purples', 'greys', 'orrd', 'ylgnbu', 'ylgn', 'gnbu',
                 'pubugn', 'bupu', 'rdpu',
                 # other, index 66-69
                 'cubehelix', 'managua', 'vanimo', 'rdgy']
DIVERGING = set(['delta', 'vlag', 'puor', 'brbg', 'piyg', 'prgn', 'icefire', 'berlin', 'bwr',
                 'rdbu', 'coolwarm', 'rdylbu', 'spectral', 'cmo_balance', 'cmo_curl',
                 'cmo_diff', 'cmo_tarn', 'managua', 'vanimo', 'rdgy'])


def palette_from_input(v, default):
    """accepts a name ("viridis", "viridis_r") or an index (0, 1, ... from a slider)"""
    if v is None or str(v).strip() == '':
        return default
    try:
        i = int(float(v))
        return PALETTE_ORDER[i % len(PALETTE_ORDER)]
    except (ValueError, TypeError):
        return str(v)


def auto_value_list(input_name, items, width=150):
    """If the input is not connected, drop a Value List (drop-down) with the given items
    next to it and wire it up - so options are picked from a menu instead of typed."""
    try:
        import System
        import Grasshopper as gh
        comp = ghenv.Component
    except Exception:
        return                                          # not running inside Grasshopper
    param = None
    for p in comp.Params.Input:
        if p.NickName == input_name or p.Name == input_name:
            param = p
    if param is None or param.SourceCount > 0:
        return
    doc = comp.OnPingDocument()
    if doc is None:
        return

    def make(d):
        if param.SourceCount > 0:
            return
        vl = gh.Kernel.Special.GH_ValueList()
        vl.CreateAttributes()
        vl.ListItems.Clear()
        for it in items:
            vl.ListItems.Add(gh.Kernel.Special.GH_ValueListItem(it, '"%s"' % it))
        vl.ListMode = gh.Kernel.Special.GH_ValueListMode.DropDown
        vl.NickName = input_name.strip('_')
        grip = param.Attributes.InputGrip
        vl.Attributes.Pivot = System.Drawing.PointF(grip.X - width - 30, grip.Y - 11)
        d.AddObject(vl, False)
        param.AddSource(vl)
        param.ExpireSolution(False)

    doc.ScheduleSolution(5, gh.Kernel.GH_Document.GH_ScheduleDelegate(make))



def opt(name, default=None):
    v = globals().get(name, default)
    return default if v is None or v == [] else v


def resample(pal, n):
    out = []
    for s in range(n):
        t = s / float(max(n - 1, 1)) * (len(pal) - 1)
        i = min(int(t), len(pal) - 2)
        f = t - i
        a, b = pal[i], pal[i + 1]
        out.append(sd.Color.FromArgb(int(round(a[0] + (b[0] - a[0]) * f)),
                                     int(round(a[1] + (b[1] - a[1]) * f)),
                                     int(round(a[2] + (b[2] - a[2]) * f))))
    return out


auto_value_list('_palette_', PALETTE_ORDER)
name = palette_from_input(opt('_palette_', None), 'viridis')
n = max(2, int(opt('_n_', 11)))
o = opt('_pt_', rg.Point3d(0, 0, 0))
pal = get_palette(name)
if pal is None:
    raise ValueError('Unknown palette "%s". Use one of: %s (add "_r" to reverse).'
                     % (name, ', '.join(sorted(PALETTES))))
if bool(opt('_reverse_', False)):
    pal = list(reversed(pal))
colors = resample(pal, n)
names = list(PALETTE_ORDER)

# preview: one horizontal strip per palette, 10 x 1 units, 0.4 gap
preview = rg.Mesh()
steps = 32
for r, nm in enumerate(names):  # strip r = slider index r
    cs = resample(PALETTES[nm], steps + 1)
    y0 = o.Y - r * 1.4
    for s in range(steps):
        a = preview.Vertices.Count
        x0, x1 = o.X + 10.0 * s / steps, o.X + 10.0 * (s + 1) / steps
        for (x, y), c in (((x0, y0), cs[s]), ((x1, y0), cs[s + 1]),
                          ((x1, y0 + 1), cs[s + 1]), ((x0, y0 + 1), cs[s])):
            preview.Vertices.Add(x, y, o.Z)
            preview.VertexColors.Add(c)
        preview.Faces.AddFace(a, a + 1, a + 2, a + 3)
preview.Normals.ComputeNormals()
print('%s -> %d colours' % (name, n))
