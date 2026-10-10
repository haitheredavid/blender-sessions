"""Mesh health checks on the Model collection, written as JSON.

Usage: blender -b model.blend -P check_mesh.py -- --result r.json

Per object: verts/faces/tris, n-gons, non-manifold edges, loose verts/edges, degenerate
faces, inconsistent normals, unapplied scale/rotation, world-space size.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bmesh
import bpy
from _common import model_objects, parse, write_result

opts = parse(argparse.ArgumentParser())

depsgraph = bpy.context.evaluated_depsgraph_get()
report = {"unit_scale": bpy.context.scene.unit_settings.scale_length, "objects": []}

for obj in model_objects():
    evaluated = obj.evaluated_get(depsgraph)
    bm = bmesh.new()
    bm.from_mesh(evaluated.to_mesh())
    evaluated.to_mesh_clear()
    bm.transform(obj.matrix_world)
    bm.normal_update()

    xs, ys, zs = zip(*(v.co[:] for v in bm.verts)) if bm.verts else ((0,), (0,), (0,))
    # An interior manifold edge whose two faces wind the same way means flipped normals.
    flipped = 0
    for e in bm.edges:
        if len(e.link_loops) == 2:
            a, b = e.link_loops
            if a.vert == b.vert:
                flipped += 1
    scale = obj.matrix_world.to_scale()
    report["objects"].append(
        {
            "name": obj.name,
            "verts": len(bm.verts),
            "faces": len(bm.faces),
            "tris": sum(len(f.verts) - 2 for f in bm.faces),
            "ngons": sum(1 for f in bm.faces if len(f.verts) > 4),
            "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
            "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
            "loose_edges": sum(1 for e in bm.edges if not e.link_faces),
            "degenerate_faces": sum(1 for f in bm.faces if f.calc_area() < 1e-10),
            "flipped_edges": flipped,
            "unapplied_scale": any(abs(s - 1) > 1e-4 for s in obj.scale),
            "unapplied_rotation": any(abs(r) > 1e-4 for r in obj.rotation_euler),
            "negative_scale": any(s < 0 for s in scale),
            "modifiers": [m.type for m in obj.modifiers],
            "size": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
            "bounds_min": [min(xs), min(ys), min(zs)],
        }
    )
    bm.free()

write_result(opts.result, report)
