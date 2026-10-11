# step 8: assembly: tenons slide lengthwise into their rider piece (N/W->TL, S->BL, E->TR) instead of dropping, then ride with it while pieces close
# Rebuild the Assembly scene (70): tenons slide lengthwise into their rider piece's
# mortise, then ride with it while the pieces close along x, then y.
from pathlib import Path

import bpy

assert bpy.data.filepath.endswith("models/witch-frame/model.blend"), bpy.data.filepath
p = Path(bpy.path.abspath("//builders/70_assembly.py"))
exec(p.read_text(), {"__name__": p.stem, "__file__": str(p)})  # noqa: S102
