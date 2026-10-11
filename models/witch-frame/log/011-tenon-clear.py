# step 11: TENON_CLEAR 0.15 -> 0.10 from P1S coupon (all 3 slide by hand, 1 notch best fit); tenons regrow N 4.3, E 3.5; check --strict clean; print pack regenerated
# builders/joinery.py: TENON_CLEAR 0.15 -> 0.10 (coupon fit test on P1S), then rebuild
from pathlib import Path

import bpy

assert bpy.data.filepath.endswith("models/witch-frame/model.blend"), bpy.data.filepath
build_all = Path(bpy.path.abspath("//builders/build_all.py"))
exec(build_all.read_text(), {"__name__": "build_all"})  # noqa: S102
