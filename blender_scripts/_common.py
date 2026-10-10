"""Shared helpers for blender_scripts/ (bpy only; never import blend here).

Scripts add their own folder to sys.path and `from _common import ...`.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

MODEL = "Model"  # the deliverable: exported, checked and rendered
WORK = "Work"  # builders, cutters, helpers: excluded from outputs
REF = "Ref"  # reference images / blockouts: excluded from outputs
CONTROL = "Control"  # user-owned GN inputs (curves, empties, sketches): excluded
NOTES = "Notes"  # dimension lines / callouts: excluded unless a view includes them


def parse(parser: argparse.ArgumentParser) -> argparse.Namespace:
    parser.add_argument("--result", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def write_result(path: str, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2))


def model_objects(scene: bpy.types.Scene | None = None, types=("MESH",)) -> list:
    """Visible objects of `types` in the Model collection (and its children).

    Falls back to every visible object of those types when the scene has no Model
    collection, so older or hand-made files still work.
    """
    scene = scene or bpy.context.scene
    layer = scene.view_layers[0]
    coll = bpy.data.collections.get(MODEL)
    pool = coll.all_objects if coll and coll.all_objects else scene.objects
    return [o for o in pool if o.type in types and o.visible_get(view_layer=layer)]


def collection_objects(
    name: str, scene: bpy.types.Scene | None = None, types=("MESH",)
) -> list:
    """Visible objects of `types` in collection `name` (and its children); [] if missing."""
    scene = scene or bpy.context.scene
    layer = scene.view_layers[0]
    coll = bpy.data.collections.get(name)
    if coll is None:
        return []
    return [
        o
        for o in coll.all_objects
        if o.type in types and o.visible_get(view_layer=layer)
    ]
