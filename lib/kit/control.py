"""Control: user-owned input geometry (curves, empties) that GN modifiers read.

Builders call ensure() so a Control object is created once with sensible defaults and
then left alone: the user reshapes it by hand and rebuilds keep the edit.

    outline = control.ensure("CTL_Outline", lambda n: control.rect(n, 280, 356, radius=12))
"""

import bpy
from mathutils import Vector

from kit import scene


def ensure(name: str, factory) -> bpy.types.Object:
    """Return Control object `name`, calling factory(name) only if it doesn't exist yet."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = factory(name)
        scene.link(obj, scene.control())
    return obj


def curve(
    name: str,
    points,
    closed: bool = True,
    kind: str = "POLY",
    location=(0, 0, 0),
) -> bpy.types.Object:
    """A curve object through `points` (2D or 3D). kind POLY keeps corners exact;
    BEZIER gets AUTO handles so the user can pull it into curves by hand."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    pts = [Vector((*p, 0.0)) if len(p) == 2 else Vector(p) for p in points]
    if kind == "BEZIER":
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(pts) - 1)
        for bp, co in zip(sp.bezier_points, pts):
            bp.co = co
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, co in zip(sp.points, pts):
            p.co = (*co, 1.0)
    sp.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, cu)
    obj.location = location
    scene.link(obj, scene.control())
    return obj


def rect(
    name: str, width: float, height: float, radius: float = 0.0, segments: int = 4
):
    """A closed rectangle centred on the origin in XY; radius > 0 rounds the corners."""
    w, h = width / 2, height / 2
    if radius <= 0:
        return curve(name, [(-w, -h), (w, -h), (w, h), (-w, h)])
    import math

    pts = []
    for cx, cy, a0 in ((w - radius, -h + radius, -90), (w - radius, h - radius, 0),
                       (-w + radius, h - radius, 90), (-w + radius, -h + radius, 180)):  # fmt: skip
        for i in range(segments + 1):
            a = math.radians(a0 + 90 * i / segments)
            pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return curve(name, pts)


def profile(name: str, points, closed: bool = True) -> bpy.types.Object:
    """A cross-section in XY for sweeps: X is across the path (outward +), Y is up."""
    return curve(name, points, closed=closed)


def empty(name: str, location=(0, 0, 0), size: float = 1.0) -> bpy.types.Object:
    """A plain-axes empty, e.g. a dimension anchor or a pivot."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = location
    scene.link(obj, scene.control())
    return obj
