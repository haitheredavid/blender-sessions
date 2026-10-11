# Assembly animation: how the printed parts go together, in its own scene "Assembly".
#
# The parts are copies of the Print collection (corner pieces stay live GN cuts of Frame)
# plus the glazing/art/backboard proxies, flipped face-down (back up) the way the frame
# is assembled on a table. Render with:
#   uv run blend animate witch-frame --scene Assembly --collection Assembly --isometric
# Timeline (24 fps): each tenon slides lengthwise into the mortise of one piece and rides
# with it -> pieces close along x (N/S seams) -> then along y (E/W seams) -> glazing, art,
# backboard drop into the rabbet -> clips drop in open and swing closed.
import math

import bpy
from mathutils import Matrix, Vector

SCENE, COLL = "Assembly", "Assembly"
FPS = 24
LIFT = 70.0  # how far drop-in parts start above their seat (mm)
SLIDE = 40.0  # how far a tenon starts out of its mortise, along its length (mm)
SPREAD = 45.0  # how far each corner piece starts out, diagonally (mm)
APPEAR = 8  # drop-in parts show up this many frames before they move
# (first frame, last frame) per beat
TENONS, CLOSE_X, CLOSE_Y, GLAZING, ART, BOARD = (
    (12, 36),
    (44, 70),
    (78, 104),
    (112, 134),
    (132, 154),
    (152, 174),
)
CLIPS_DROP, CLIPS_TURN, HOLD = (182, 204), (208, 228), 252

main = bpy.data.scenes["Scene"]
sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
sc.unit_settings.system = main.unit_settings.system
sc.unit_settings.scale_length = main.unit_settings.scale_length
sc.unit_settings.length_unit = main.unit_settings.length_unit
sc.frame_start, sc.frame_end, sc.render.fps = 1, HOLD, FPS

coll = bpy.data.collections.get(COLL)
if coll is None:
    coll = bpy.data.collections.new(COLL)
if coll.name not in sc.collection.children:
    sc.collection.children.link(coll)
for o in list(coll.objects):  # rebuild: drop the previous copies (and clip mesh copies)
    data = o.data if o.name.startswith("Asm_Clip") else None
    bpy.data.objects.remove(o, do_unlink=True)
    if data is not None and data.users == 0:
        bpy.data.meshes.remove(data)

FLIP = Matrix.Rotation(math.pi, 4, "X")  # face down, back up (z -> -z, y -> -y)


def copy(name: str) -> bpy.types.Object:
    src = bpy.data.objects[name]
    obj = src.copy()  # shares mesh data; GN/boolean modifiers come along
    obj.name = f"Asm_{name}"
    obj.animation_data_clear()
    coll.objects.link(obj)
    obj.matrix_world = FLIP @ src.matrix_world
    return obj


def key_move(obj, start: int, end: int, offset: Vector, appear: bool = False) -> None:
    """Hold at home + offset until `start`, ease to home by `end`. appear=True keeps the
    part hidden until just before its beat, so waiting parts don't cover the earlier ones."""
    home = obj.location.copy()
    obj.location = home + offset
    obj.keyframe_insert("location", frame=1)
    obj.keyframe_insert("location", frame=start)
    obj.location = home
    obj.keyframe_insert("location", frame=end)
    if appear:
        for frame, hidden in ((1, True), (max(1, start - APPEAR), False)):
            obj.hide_render = obj.hide_viewport = hidden
            obj.keyframe_insert("hide_render", frame=frame)
            obj.keyframe_insert("hide_viewport", frame=frame)


def path(obj, keys: list[tuple[int, Vector]], appear: int | None = None) -> None:
    """Key obj.location at each (frame, location); appear hides it until that frame."""
    for frame, loc in keys:
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)
    if appear is not None:
        for frame, hidden in ((1, True), (max(1, appear), False)):
            obj.hide_render = obj.hide_viewport = hidden
            obj.keyframe_insert("hide_render", frame=frame)
            obj.keyframe_insert("hide_viewport", frame=frame)


up = Vector((0, 0, LIFT))
spread = {}  # piece -> its open offset; closes in x first, then y
for name in ("Piece_TR", "Piece_TL", "Piece_BL", "Piece_BR"):
    piece = copy(name)
    sx = 1 if name[-1] == "R" else -1
    sy = -1 if name[-2] == "T" else 1  # flipped: the top rail now sits at -y
    off = Vector((sx, sy, 0)) * SPREAD * 0.7
    spread[name[-2:]] = off
    home = piece.location.copy()
    mid = home + Vector((0, off.y, 0))
    path(piece, [(1, home + off), (CLOSE_X[0], home + off), (CLOSE_X[1], mid),
                 (CLOSE_Y[0], mid), (CLOSE_Y[1], home)])  # fmt: skip

# Each tenon is glued into one piece first (its rider), slid in along its length from
# the seam side, then rides with that piece while the frame closes
for name, rider, axis in (("N", "TL", 0), ("S", "BL", 0), ("E", "TR", 1), ("W", "TL", 1)):
    tenon = copy(f"Tenon_{name}")
    home = tenon.location.copy()
    off = spread[rider]
    along = Vector((1, 0, 0)) if axis == 0 else Vector((0, 1, 0))
    out = along * (-math.copysign(SLIDE, off[axis]))  # away from the rider's mortise
    mid = home + Vector((0, off.y, 0))
    path(tenon, [(1, home + off + out), (TENONS[0], home + off + out),
                 (TENONS[1], home + off), (CLOSE_X[0], home + off), (CLOSE_X[1], mid),
                 (CLOSE_Y[0], mid), (CLOSE_Y[1], home)], appear=TENONS[0] - APPEAR)  # fmt: skip

for name, beat in (
    ("Glazing_Proxy", GLAZING),
    ("Art_Proxy", ART),
    ("Backboard_Proxy", BOARD),
):
    key_move(copy(name), *beat, up * 1.4, appear=True)

for src in sorted(
    (o for o in bpy.data.collections["Print"].objects if o.name.startswith("Clip_")),
    key=lambda o: o.name,
):
    clip = copy(src.name)
    clip.data = src.data.copy()  # own mesh, re-originated on the screw axis
    pivot = FLIP @ Vector(src["pivot"])
    clip.data.transform(Matrix.Translation(-pivot) @ FLIP)
    clip.matrix_world = Matrix.Translation(pivot)
    key_move(clip, *CLIPS_DROP, up * 0.6, appear=True)
    swing = math.radians(src["swing_deg"]) * -1  # mirrored by the flip
    clip.rotation_euler.z = swing  # open: tip toward the corner, clear of the rabbet
    for f in (1, CLIPS_TURN[0]):
        clip.keyframe_insert("rotation_euler", index=2, frame=f)
    clip.rotation_euler.z = 0.0
    clip.keyframe_insert("rotation_euler", index=2, frame=CLIPS_TURN[1])

print(f"assembly: {len(coll.objects)} parts, frames 1-{HOLD} at {FPS} fps")
