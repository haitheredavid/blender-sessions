"""Mesh construction and modifier stacks."""

import bmesh
import bpy
from mathutils import Vector

from kit import scene


def from_bmesh(name: str, bm: bmesh.types.BMesh, coll=None) -> bpy.types.Object:
    """Write bm to a new mesh object in coll (default Model). Frees bm."""
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    (coll or scene.model()).objects.link(obj)
    return obj


def box(name: str, size=(1, 1, 1), center=(0, 0, 0), coll=None) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector(c * s + o for c, s, o in zip(v.co, size, center))
    return from_bmesh(name, bm, coll)


def bevel_stack(
    obj: bpy.types.Object,
    width: float = 0.005,
    segments: int = 3,
    angle_deg: float = 30.0,
) -> bpy.types.Object:
    """Hard-surface finish: angle-limited bevel + weighted normals + smooth shading."""
    import math

    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = width
    bev.segments = segments
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(angle_deg)
    bev.harden_normals = True
    obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL").keep_sharp = True
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def boolean(
    obj: bpy.types.Object, cutter: bpy.types.Object, op: str = "DIFFERENCE"
) -> bpy.types.Modifier:
    """Live boolean; the cutter moves to Work and is hidden from render."""
    mod = obj.modifiers.new(f"Bool_{cutter.name}", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    scene.link(cutter, scene.work())
    cutter.display_type = "WIRE"
    cutter.hide_render = True
    return mod


def apply_modifiers(obj: bpy.types.Object) -> None:
    """Bake the evaluated mesh into obj and clear its modifier stack."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def clean(obj: bpy.types.Object, merge: float = 1e-5) -> None:
    """Merge by distance, dissolve degenerates, recalc normals outward."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
