"""Animation: keyframe GN inputs (parameter sweeps), exploded views, and frame ranges.

Render with `blend animate <m>` (studio lighting, the scene's frame range).

    anim.sweep(body.modifiers["GN_OutlineExtrude"], "Height", [20, 60, 20], step=48)
    anim.explode(scene.model().objects, distance=40, start=1, end=48)
"""

import bpy
from mathutils import Vector

from kit import gn


def key_input(mod, name: str, frame: int, value) -> None:
    """Keyframe a GN modifier input by socket name (Blender 5: properties.inputs.<id>)."""
    gn.set_input(mod, name, value)
    ident = gn.socket_id(mod.node_group, name)
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props, "inputs"):
        getattr(props.inputs, ident).keyframe_insert("value", frame=frame)
    else:  # Blender 4.x: ID property on the modifier
        mod.id_data.keyframe_insert(f'modifiers["{mod.name}"]["{ident}"]', frame=frame)


def sweep(mod, name: str, values, start: int = 1, step: int = 24) -> tuple[int, int]:
    """Keyframe values at start, start+step, ...; sets the scene range to cover them."""
    end = start
    for i, v in enumerate(values):
        end = start + i * step
        key_input(mod, name, end, v)
    frame_range(start, end)
    return start, end


def explode(
    objects,
    distance: float,
    start: int = 1,
    end: int = 48,
    center=None,
    axis=None,
) -> tuple[int, int]:
    """Spread objects away from center (default: the group's centre), keyed from start
    (assembled) to end (exploded). Each moves in proportion to its offset from center,
    the farthest by `distance`; axis limits the motion to that direction."""
    objects = list(objects)
    bpy.context.view_layer.update()  # new/moved objects have a stale matrix_world
    pos = {o: o.matrix_world.translation.copy() for o in objects}
    if center is None:
        center = sum(pos.values(), Vector()) / len(objects)
    center = Vector(center)

    def offset(o):
        d = pos[o] - center
        if axis is not None:
            a = Vector(axis).normalized()
            d = a * d.dot(a)
        return d

    far = max((offset(o).length for o in objects), default=0.0) or 1.0
    for o in objects:
        home = o.location.copy()
        o.keyframe_insert("location", frame=start)
        o.location = home + offset(o) * (distance / far)
        o.keyframe_insert("location", frame=end)
        o.location = home
    frame_range(start, end)
    return start, end


def frame_range(start: int, end: int, fps: int | None = None) -> None:
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = start, end
    if fps:
        sc.render.fps = fps
