# step 7: butterfly keys -> glued loose tenons inside the seams, fitted to the seam profile with >=2 mm walls (N 4.2x8.2, S 6.0x8.4, E 3.4x8.3, W 3.8x8.2, 32 long); assembly closes x then y
# Rebuild Print joinery (40_sections) as glued loose tenons inside the seams, then the
# Assembly scene (70): tenons drop in, pieces close along x then y.
import importlib, sys
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
    for n in ("Cut_Keys", "Cut_Tenons"):
        if old := bpy.data.objects.get(n):
            bpy.data.objects.remove(old, do_unlink=True)
    for f in ("40_sections.py", "70_assembly.py"):
        p = HERE / f
        exec(p.read_text(), {"__name__": p.stem, "__file__": str(p)})
finally:
    win.scene = prev
