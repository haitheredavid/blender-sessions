# step 6: odd fillet segments so no recess vertex sits on the seam plane: clears 2 degenerate boolean faces (TL, BL)
# Rebuild Print joinery (40_sections) with filleted, true-offset keys/recesses, then the
# Assembly scene (70) whose copies share the key meshes and the Cut_Keys cutter.
import importlib
import sys
from pathlib import Path

import bpy

assert bpy.data.filepath.endswith("models/witch-frame/model.blend"), bpy.data.filepath
HERE = Path(bpy.path.abspath("//builders"))
LIB = str(HERE.parents[2] / "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
for n in sorted(m for m in sys.modules if m.split(".")[0] in ("kit", "patterns")):
    importlib.reload(sys.modules[n])
win = bpy.context.window
prev = win.scene
win.scene = bpy.data.scenes["Scene"]
try:
    old = bpy.data.objects.get("Cut_Keys")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    for f in ("40_sections.py", "70_assembly.py"):
        p = HERE / f
        exec(p.read_text(), {"__name__": p.stem, "__file__": str(p)})  # noqa: S102
finally:
    win.scene = prev
