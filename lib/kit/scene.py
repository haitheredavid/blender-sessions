"""Collections, cleanup and object bookkeeping."""

import bpy

MODEL, WORK, REF = "Model", "Work", "Ref"


def collection(
    name: str, parent: bpy.types.Collection | None = None
) -> bpy.types.Collection:
    """Get or create a collection linked under parent (default: the scene root)."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if coll.name not in parent.children:
        parent.children.link(coll)
    return coll


def model() -> bpy.types.Collection:
    return collection(MODEL)


def work() -> bpy.types.Collection:
    coll = collection(WORK)
    coll.hide_render = True
    return coll


def link(obj: bpy.types.Object, coll: bpy.types.Collection) -> bpy.types.Object:
    """Move obj into exactly one collection."""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def clear(coll: bpy.types.Collection) -> None:
    """Delete every object in coll (recursively) so a builder can rebuild from scratch."""
    for obj in list(coll.all_objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    purge()


def purge() -> None:
    """Drop orphan meshes/curves/materials left by rebuilds."""
    for data in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for block in list(data):
            if block.users == 0:
                data.remove(block)


def save() -> None:
    bpy.ops.wm.save_mainfile()
