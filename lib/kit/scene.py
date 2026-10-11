"""Collections, cleanup and object bookkeeping."""

import bpy

MODEL, WORK, REF = "Model", "Work", "Ref"
CONTROL, NOTES = "Control", "Notes"  # user-owned inputs; annotations (views only)
PARTS = (
    "Print"  # fabrication parts (sections, keys); `blend export` [export] collection
)


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


def control() -> bpy.types.Collection:
    """User-owned inputs (curves, empties, GP sketches). Builders never clear it."""
    coll = collection(CONTROL)
    coll.hide_render = True
    return coll


def notes() -> bpy.types.Collection:
    """Dimension lines and callouts; rendered only by views that include it."""
    coll = collection(NOTES)
    coll.hide_render = True
    return coll


def parts() -> bpy.types.Collection:
    """Printable parts (sections, keys, clips). Not rendered; export/check target it
    with [export] collection = "Print" / `blend check --collection Print`."""
    coll = collection(PARTS)
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


def fit_viewport(near_m: float = 0.0001, far_m: float = 10.0) -> None:
    """Set every 3D view's clip range in real distance (default 0.1 mm to 10 m), scaled
    by the file's unit scale. Blender's defaults are in Blender units (0.01-1000 BU), so
    in an mm file they're 0.01 mm-1 m: the far side of a model clips away when zooming
    out. Runs in build_all and works headless (screens are saved with the file)."""
    per_bu = bpy.context.scene.unit_settings.scale_length or 1.0  # metres per BU
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.clip_start = near_m / per_bu
                    space.clip_end = far_m / per_bu


def save() -> None:
    bpy.ops.wm.save_mainfile()
