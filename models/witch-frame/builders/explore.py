# Variant grids for comparing edge/depth options; not run by build_all (no NN_ prefix).
# Over MCP, after build_all has put lib/ on sys.path:
#   g = {"__name__": "explore", "__file__": bpy.path.abspath("//builders/explore.py")}
#   exec(open(g["__file__"]).read(), g); g["grid"](g["EDGE"])
import importlib
import sys
from pathlib import Path

import bpy
from kit import materials, mesh, scene

sys.path.insert(0, str(Path(__file__).parent))
import frame_geo

importlib.reload(frame_geo)

# rows x cols of param overrides
EDGE = [
    [{"sag": s, "k": 1.3} for s in (8, 12, 15)],
    [{"sag": s, "k": 0.5} for s in (8, 12, 15)],
]
DEPTH = [
    [{"depth": d, "profile": pr} for d in (25, 40, 55)]
    for pr in ("linear", "cove", "convex")
]


def grid(rows, base=None, gap=60.0):
    coll = scene.collection("Explore")
    scene.clear(coll)
    mat = materials.principled("Explore_Grey", "#9A97A0", roughness=0.6)
    base = base or {}
    for r, row in enumerate(rows):
        for c, over in enumerate(row):
            p = frame_geo.params(**{**base, **over})
            try:
                wall = frame_geo.validate(p)
            except AssertionError as e:
                print(f"r{r}c{c} {over}: INVALID {e}")
                continue
            name = f"V_r{r}c{c}"
            obj = mesh.from_bmesh(name, frame_geo.build_bmesh(p), coll)
            obj.location = (c * (p["width"] + gap), -r * (p["height"] + gap), 0)
            materials.assign(obj, mat)
            print(f"{name} {over} wall={wall:.1f}")
    bpy.data.collections["Model"].hide_viewport = True
    return coll


def clear():
    scene.clear(scene.collection("Explore"))
    bpy.data.collections["Model"].hide_viewport = False
