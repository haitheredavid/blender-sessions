# step 12: coupon round 2: only C10 (0.10), twice: Flat ledge (as frame, sliced w/ supports) + Chamfer (45 deg wedge fills rabbet corner under the 3.675 mm lip at z 9, self-supporting); manifold, no flat-down faces left on Chamfer
import importlib
import sys
from pathlib import Path

import bpy

assert bpy.data.filepath.endswith("models/witch-frame/model.blend"), bpy.data.filepath
HERE = Path(bpy.path.abspath("//builders"))
LIB = HERE.parents[2] / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
for name in sorted(n for n in sys.modules if n.split(".")[0] in ("kit", "patterns")):
    importlib.reload(sys.modules[name])
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import frame_geo

importlib.reload(frame_geo)
for o in [
    o for o in bpy.data.objects if o.name.startswith(("Cut_Coupon_", "Add_Coupon_"))
]:
    bpy.data.objects.remove(o)
step = HERE / "45_coupon.py"
exec(step.read_text(), {"__name__": step.stem, "__file__": str(step)})  # noqa: S102
