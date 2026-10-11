"""Create an empty model .blend: metric, 1 Blender unit = 1 m, with the model collections.

Usage: blender -b --factory-startup -P setup_scene.py -- --save path/to/model.blend --result r.json
       [--scale-length 1.0 --length-unit METERS]

Collections: Model (the deliverable), Work (builders/cutters/helpers), Control (user-owned
GN inputs), Notes (dimensions/callouts), Ref (reference images). Only Model renders.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bpy
from _common import CONTROL, MODEL, NOTES, REF, WORK, parse, write_result

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

# Viewport clipping is in Blender units: at mm scale the default 1000 clip end is only
# 1 m, so models vanish when zoomed out. Use 0.1 mm to 10 m in real distance (the same
# 1e5 near/far ratio as the defaults); kit.scene.fit_viewport() re-applies it on rebuild.
k = 1.0 / opts.scale_length
for screen in bpy.data.screens:
    for area in screen.areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.clip_start = 0.0001 * k
                space.clip_end = 10.0 * k

for name in (MODEL, CONTROL, WORK, NOTES, REF):
    scene.collection.children.link(bpy.data.collections.new(name))
# Everything but Model stays visible in the viewport but never renders.
for name in (CONTROL, WORK, NOTES, REF):
    bpy.data.collections[name].hide_render = True

Path(opts.save).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(opts.save).resolve()))
write_result(opts.result, {"saved": opts.save})
