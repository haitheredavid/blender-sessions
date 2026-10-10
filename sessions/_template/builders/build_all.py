# Rebuild the model from scratch. Over MCP (model.blend must be open):
#   exec(open(bpy.path.abspath('//builders/build_all.py')).read(), {'__name__': 'build_all'})
# Runs every builders/NN_*.py in name order (10_base.py, 20_details.py, ...), with the repo's
# lib/ on sys.path and `kit` reloaded so helper edits apply without restarting Blender.
import importlib
import sys
from pathlib import Path

import bpy

HERE = Path(bpy.path.abspath("//builders"))
LIB = HERE.parents[2] / "lib"  # sessions/<s>/builders -> repo/lib
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
for name in sorted(n for n in sys.modules if n == "kit" or n.startswith("kit.")):
    importlib.reload(sys.modules[name])

from kit import scene

scene.clear(scene.model())
scene.clear(scene.work())  # cutters/helpers are rebuilt by the builders too
for step in sorted(HERE.glob("[0-9][0-9]_*.py")):
    exec(step.read_text(), {"__name__": step.stem, "__file__": str(step)})  # noqa: S102
    print(f"build_all: {step.name}")
scene.purge()
scene.save()
print("build_all ok")
