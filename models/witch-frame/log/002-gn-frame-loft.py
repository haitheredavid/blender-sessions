# step 2: rebuild Frame on GN_FrameLoft with Control outline; clip pockets as live booleans
# Frame: GN_FrameLoft (lib/patterns/frame_loft.py) on a hand-editable Control outline.
#
# CTL_Outline is created once as an 11x14" tip-to-tip rectangle (4-point Bezier, vector
# handles). Reshape it by hand (pull handles to bend the sides) and rebuilds keep it.
# The bat-wing bow, depth and face shape are modifier inputs, set from params.toml.
# Sizes derived from the art (sight opening, rabbet) come from frame_geo.py's constants.
import importlib
import sys
from pathlib import Path

import bpy
from kit import control, gn, materials, params
from patterns import frame_loft

sys.path.insert(0, str(Path(__file__).parent))
import frame_geo

importlib.reload(frame_geo)

W, H = frame_geo.DEFAULTS["width"], frame_geo.DEFAULTS["height"]


def outline(name):
    obj = control.curve(
        name, [(W / 2, H / 2), (-W / 2, H / 2), (-W / 2, -H / 2), (W / 2, -H / 2)],
        kind="BEZIER",
    )  # fmt: skip
    for bp in obj.data.splines[0].bezier_points:
        bp.handle_left_type = bp.handle_right_type = "VECTOR"
    return obj


ctl = control.ensure("CTL_Outline", outline)
sw, sh = frame_geo.sight_size()
rw, rh = frame_geo.rabbet_size()
frame = gn.host("Frame")
frame_loft.apply(
    frame,
    Outline=ctl,
    Sight_Width=sw,
    Sight_Height=sh,
    Rabbet_Width=rw,
    Rabbet_Height=rh,
    Rabbet_Depth=frame_geo.DEFAULTS["rabbet"],
    Material=materials.principled("PLA_Matte", "#8A8496", roughness=0.65),
)
params.apply("base", [frame])  # now, so 20_clips' skin checks see the real shape
bpy.context.view_layer.update()
print(f"Frame: outline {ctl.dimensions.x:.1f} x {ctl.dimensions.y:.1f} mm, "
      f"sight {sw:.1f} x {sh:.1f}, rabbet {rw:.1f} x {rh:.1f}")  # fmt: skip
