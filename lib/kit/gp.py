"""Grease pencil (v3, Blender 4.3+): sketch strokes, and turn a sketch into Control curves.

The user (or the agent) sketches in a GP object in Control; to_curve() converts a stroke
into a Control curve that GN patterns read (profile, path, outline). The curve is a copy:
refine it by hand afterwards, the sketch stays as reference.

    gp.sketch("GP_Wing", [[(0, 0, 0), (40, 12, 0), (80, 0, 0)]])
    gp.to_curve("GP_Wing", "CTL_WingEdge", tolerance=0.5, kind="BEZIER")
"""

import bpy
from mathutils import Vector

from kit import control, scene


def ink(name: str = "gp_ink", color=(0.05, 0.05, 0.06, 1.0)) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        bpy.data.materials.create_gpencil_data(mat)
    mat.grease_pencil.color = color
    return mat


def sketch(
    name: str,
    strokes,
    radius: float = 0.5,
    layer: str = "Sketch",
    coll=None,
    cyclic: bool = False,
) -> bpy.types.Object:
    """A GP object (in Control by default) with one stroke per point list. Re-running
    replaces the layer's strokes, so it stays idempotent."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, bpy.data.grease_pencils.new(name))
        (coll or scene.control()).objects.link(obj)
    gp = obj.data
    if not gp.materials:
        gp.materials.append(ink())
    lay = gp.layers.get(layer) if hasattr(gp.layers, "get") else None
    lay = (
        lay
        or next((l for l in gp.layers if l.name == layer), None)
        or gp.layers.new(layer)
    )
    frame = lay.current_frame() or lay.frames.new(bpy.context.scene.frame_current)
    drawing = frame.drawing
    if len(drawing.strokes):
        drawing.remove_strokes()
    drawing.add_strokes([len(s) for s in strokes])
    for st, pts in zip(drawing.strokes, strokes):
        st.cyclic = cyclic
        for p, co in zip(st.points, pts):
            p.position = co if len(co) == 3 else (*co, 0.0)
            p.radius = radius
    return obj


def strokes(obj: bpy.types.Object, layer: str | None = None) -> list[list[Vector]]:
    """World-space point lists of every stroke in the current frame (of one layer)."""
    out = []
    for lay in obj.data.layers:
        if layer and lay.name != layer:
            continue
        frame = lay.current_frame()
        if frame is None:
            continue
        for st in frame.drawing.strokes:
            out.append([obj.matrix_world @ Vector(p.position) for p in st.points])
    return out


def simplify(points: list[Vector], tolerance: float) -> list[Vector]:
    """Ramer-Douglas-Peucker: drop points within tolerance of the line between kept ones."""
    if tolerance <= 0 or len(points) < 3:
        return list(points)
    a, b = points[0], points[-1]
    ab = b - a
    worst, idx = -1.0, 0
    for i, p in enumerate(points[1:-1], 1):
        d = (p - a).cross(ab).length / ab.length if ab.length else (p - a).length
        if d > worst:
            worst, idx = d, i
    if worst <= tolerance:
        return [a, b]
    return simplify(points[: idx + 1], tolerance)[:-1] + simplify(
        points[idx:], tolerance
    )


def to_curve(
    gp_name: str,
    curve_name: str,
    index: int = 0,
    tolerance: float = 0.0,
    kind: str = "BEZIER",
    closed: bool | None = None,
    replace: bool = False,
) -> bpy.types.Object:
    """Copy stroke `index` of a GP object into a Control curve (simplified by tolerance).
    Leaves an existing curve alone unless replace=True, so hand edits survive rebuilds."""
    existing = bpy.data.objects.get(curve_name)
    if existing is not None and not replace:
        return existing
    obj = bpy.data.objects[gp_name]
    pts = simplify(strokes(obj)[index], tolerance)
    if closed is None:
        closed = (pts[0] - pts[-1]).length <= max(tolerance, 1e-6) * 2
        if closed and len(pts) > 2:
            pts = pts[:-1]
    if existing is not None:
        bpy.data.objects.remove(existing, do_unlink=True)
    return control.curve(curve_name, [tuple(p) for p in pts], closed=closed, kind=kind)
