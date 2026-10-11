"""Export the Model collection to GLB / FBX / OBJ / STL / 3MF (modifiers applied).

Usage: blender -b model.blend -P export.py -- --outdir exports --name NAME
       [--formats glb,fbx,obj,stl,3mf] [--split] [--collection Print] --result r.json

Default: one file per format with every Model object in it. --split writes one file per
object (NAME is ignored; files are named after the objects). STL is written in Blender
units (an mm model gives mm), which is what slicers expect. 3MF needs a 3MF exporter
add-on enabled in Blender; it fails with a clear message otherwise.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bpy
from _common import model_objects, parse, write_result

parser = argparse.ArgumentParser()
parser.add_argument("--outdir", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--formats", default="glb")
parser.add_argument("--split", action="store_true")
parser.add_argument("--collection", default="")  # default Model; Print for parts
opts = parse(parser)

outdir = Path(opts.outdir)
outdir.mkdir(parents=True, exist_ok=True)
formats = [f.strip() for f in opts.formats.split(",") if f.strip()]
# Export the meshes plus anything parented/rigged with them (empties, armatures, lights).
objects = model_objects(
    types=("MESH", "CURVE", "EMPTY", "ARMATURE"), collection=opts.collection
)


def select_only(objs) -> None:
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def export(fmt: str, path: Path) -> None:
    if fmt == "glb":
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_yup=True,
        )
    elif fmt == "fbx":
        bpy.ops.export_scene.fbx(
            filepath=str(path),
            use_selection=True,
            use_mesh_modifiers=True,
            apply_scale_options="FBX_SCALE_UNITS",
            axis_forward="-Z",
            axis_up="Y",
        )
    elif fmt == "obj":
        bpy.ops.wm.obj_export(
            filepath=str(path),
            export_selected_objects=True,
            apply_modifiers=True,
            export_materials=True,
            forward_axis="NEGATIVE_Z",
            up_axis="Y",
        )
    elif fmt == "stl":
        bpy.ops.wm.stl_export(
            filepath=str(path),
            export_selected_objects=True,
            apply_modifiers=True,
            ascii_format=False,
        )
    elif fmt == "3mf":
        op = getattr(bpy.ops.export_mesh, "threemf", None)
        if op is None or not op.poll():
            raise SystemExit("3mf: enable a 3MF exporter add-on in Blender first")
        op(filepath=str(path), use_selection=True)
    else:
        raise SystemExit(f"unknown format {fmt!r}")


written = []
if objects:
    groups = (
        [(bpy.path.clean_name(o.name), [o]) for o in objects if o.type == "MESH"]
        if opts.split
        else [(opts.name, objects)]
    )
    for stem, objs in groups:
        select_only(objs)
        for fmt in formats:
            path = outdir / f"{stem}.{fmt}"
            export(fmt, path)
            written.append(str(path))

write_result(
    opts.result,
    {"written": written, "objects": [o.name for o in objects], "formats": formats},
)
