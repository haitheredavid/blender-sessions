# Frame: the parametric ring sweep from frame_geo.py. Tune FRAME, then rebuild.
import importlib
import sys
from pathlib import Path

from kit import materials, mesh

sys.path.insert(0, str(Path(__file__).parent))
import frame_geo

importlib.reload(frame_geo)

# Chosen from the explore.py grids (out/explore-edge.png, out/explore-depth.png): sharp
# horn tips, 15 mm bow + light wobble, 40 mm cove face. Shrunk to 11x14" so the frame hugs
# the 9x12" art (backboard cut to art size, rabbet deepened for 2 mm glazing).
FRAME = frame_geo.params(
    sag=15.0,
    k=0.5,
    wobble=3.0,
    seed=3,
    depth=40.0,
    profile="cove",
)

wall = frame_geo.validate(FRAME)
frame = mesh.from_bmesh("Frame", frame_geo.build_bmesh(FRAME))
pla = materials.principled("PLA_Matte", "#8A8496", roughness=0.65)
materials.assign(frame, pla)
print(f"Frame ok, min wall {wall:.1f} mm")
