"""Create an empty session .blend: metric, 1 Blender unit = 1 m, with session collections.

Usage: blender -b --factory-startup -P setup_scene.py -- --save path/to/model.blend --result r.json
       [--scale-length 1.0 --length-unit METERS]

Collections: Model (the deliverable), Work (builders/cutters/helpers, hidden from
outputs), Ref (reference images, blockouts).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bpy
from _common import MODEL, REF, WORK, parse, write_result

parser = argparse.ArgumentParser()
parser.add_argument("--save", required=True)
parser.add_argument("--scale-length", type=float, default=1.0)
parser.add_argument("--length-unit", default="METERS")
opts = parse(parser)

# Start from an empty scene.
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for coll in list(bpy.data.collections):
    bpy.data.collections.remove(coll)

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = opts.scale_length
try:
    scene.unit_settings.length_unit = opts.length_unit
except TypeError:
    pass

for name in (MODEL, WORK, REF):
    scene.collection.children.link(bpy.data.collections.new(name))
# Work and Ref stay visible in the viewport but never render.
for name in (WORK, REF):
    bpy.data.collections[name].hide_render = True

Path(opts.save).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(opts.save).resolve()))
write_result(opts.result, {"saved": opts.save})
