"""Bake a collection's parts into a print-ready handoff: parts.blend + one STL per part.

Usage: blender -b model.blend -P print_pack.py -- --outdir models/<m>/print
       [--collection Print] [--gap 5] [--bed 256] --result r.json

For a printing agent (e.g. bambi), which exports every visible mesh of a mm .blend:
- every visible mesh in the collection is evaluated (modifiers, GN, booleans applied) into
  a plain mesh with its world transform baked in, keeping materials;
- each part is dropped onto the bed (lowest point at z=0) in its modelled orientation,
  and parts are laid out in non-overlapping rows (gap mm apart) so nothing collides;
- parts.blend contains only those parts, in mm (1 BU = 1 mm), saved as a new file;
- each part is also written as <name>.stl in Blender units (mm).
The source .blend is never saved. The result JSON lists each part's size, volume and
footprint, and flags any part larger than the bed.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bmesh
import bpy
from _common import model_objects, parse, write_result
from mathutils import Matrix, Vector

parser = argparse.ArgumentParser()
parser.add_argument("--outdir", required=True)
parser.add_argument("--collection", default="Print")
parser.add_argument("--gap", type=float, default=5.0)
parser.add_argument("--bed", type=float, default=256.0)
opts = parse(parser)

scene = bpy.context.scene
per_bu = scene.unit_settings.scale_length or 1.0
mm = 0.001 / per_bu  # Blender units per mm in the source file
dg = bpy.context.evaluated_depsgraph_get()
sources = model_objects(collection=opts.collection)
if not sources:
    raise SystemExit(f"no visible meshes in collection {opts.collection!r}")

baked = []
for src in sources:
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), depsgraph=dg)
    me.transform(src.matrix_world)
    if mm != 1.0:  # normalise to 1 BU = 1 mm
        me.transform(Matrix.Scale(1.0 / mm, 4))
    me.name = src.name
    baked.append((src.name, me))

# drop the source scene's objects; only the baked parts go in the pack
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in list(bpy.data.collections):
    bpy.data.collections.remove(coll)
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.001
scene.unit_settings.length_unit = "MILLIMETERS"
parts_coll = bpy.data.collections.new("Parts")
scene.collection.children.link(parts_coll)

# shelf layout: largest footprints first, rows along +X, wrapping at a wide row length
items = []
for name, me in baked:
    xs, ys, zs = zip(*(v.co[:] for v in me.vertices))
    lo, hi = Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))
    items.append((name, me, lo, hi))
items.sort(key=lambda it: -(it[3].x - it[2].x) * (it[3].y - it[2].y))
row_len = max(opts.bed * 2, max(it[3].x - it[2].x for it in items))
x = y = row_h = 0.0
parts = []
for name, me, lo, hi in items:
    w, d, h = hi - lo
    if x and x + w > row_len:
        x, y, row_h = 0.0, y + row_h + opts.gap, 0.0
    me.transform(Matrix.Translation(Vector((x, y, 0)) - lo))  # min corner -> (x, y, 0)
    obj = bpy.data.objects.new(name, me)
    parts_coll.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    volume = abs(bm.calc_volume())
    manifold = all(e.is_manifold for e in bm.edges)
    bm.free()
    parts.append(
        {
            "name": name,
            "size": [round(w, 2), round(d, 2), round(h, 2)],
            "volume_cm3": round(volume / 1000.0, 2),
            "manifold": manifold,
            "fits_bed": max(w, d) <= opts.bed and h <= opts.bed,
        }
    )
    x += w + opts.gap
    row_h = max(row_h, d)

out = Path(opts.outdir).resolve()
stl_dir = out / "stl"
stl_dir.mkdir(parents=True, exist_ok=True)
for old in stl_dir.glob("*.stl"):
    old.unlink()
for obj in parts_coll.objects:
    for o in scene.objects:
        o.select_set(o == obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(stl_dir / f"{bpy.path.clean_name(obj.name)}.stl"),
        export_selected_objects=True,
        apply_modifiers=True,
        ascii_format=False,
    )
for screen in bpy.data.screens:  # 0.1 mm - 10 m view clip for the mm pack
    for area in screen.areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.clip_start, space.clip_end = 0.1, 10000.0
bpy.ops.wm.save_as_mainfile(filepath=str(out / "parts.blend"), copy=True)
write_result(
    opts.result,
    {"blend": str(out / "parts.blend"), "stl_dir": str(stl_dir), "parts": parts},
)
