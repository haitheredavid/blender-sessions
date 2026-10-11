# step 4: 4 live GN_SectionPiece corner pieces + butterfly keys fitted to the back strip at each mid-side seam; Print collection; STL export
# Print sectioning + joinery: four corner pieces split at the mid-sides, joined by
# butterfly keys glued into recesses across each seam on the back face.
#
# Pieces (Print collection) are live GN_SectionPiece cuts of Frame: edit the frame (its
# Control outline or modifier inputs) and the pieces follow. Each key runs along its rail,
# straddling the seam; its width is fitted to the back-face strip there (rabbet edge to
# the bowed outline, 8-11 mm), keeping >= MARGIN of wall on both sides (asserted by ray).
# Keys print flat; each recess is KEY_CLEAR bigger per side, and keys sit KEY_PROUD below
# flush so they never stop the frame lying flat on the wall.
import bmesh
import bpy
from kit import mesh, scene
from mathutils import Vector
from patterns import section_piece

BED = 256.0
KEY_LEN = 32.0  # along the rail, half each side of the seam
KEY_WING = (
    6.0  # max width across the rail at the key's ends (narrowed to fit the strip)
)
KEY_WAIST = 0.58  # waist / wing
KEY_DEPTH = 5.0  # recess depth into the back face
KEY_CLEAR = 0.15  # recess clearance per side (PLA, glued)
KEY_PROUD = 0.2  # key thickness = depth - this
MARGIN = 1.0  # min wall beside a recess

frame = bpy.data.objects["Frame"]
parts = scene.parts()
for o in list(
    parts.objects
):  # rebuild Print: drop our pieces/keys, unlink shared parts
    if len(o.users_collection) == 1:
        bpy.data.objects.remove(o, do_unlink=True)
    else:
        parts.objects.unlink(o)

dg = bpy.context.evaluated_depsgraph_get()
ev = frame.evaluated_get(dg)
back = [frame.matrix_world @ v.co for v in ev.data.vertices]
back = [p for p in back if p.z < 0.5]
dims = ev.dimensions


def strip(axis: int, sign: int) -> tuple[float, float]:
    """Back-face strip across the rail where seam axis=0 meets side `sign`: (inner,
    outer) distance from centre over the key's length (rabbet edge to nearest outline)."""
    along = 1 - axis  # the rail runs along this axis; the seam is at along == 0
    near = [p for p in back if abs(p[along]) <= KEY_LEN / 2 + 2 and p[axis] * sign > 0]
    edge = sorted(abs(p[axis]) for p in near)
    inner = edge[0]  # rabbet rectangle
    outer = min(d for d in edge if d > inner + 1.0)  # outline ring (nearest point)
    return inner, outer


def butterfly(bm, centre, axis, wing, grow=0.0, z0=0.0, z1=1.0):
    """Bow-tie prism straddling the seam: length along the rail (the non-`axis`
    direction), width across it (along `axis`)."""
    half_l, half_w, half_n = (
        KEY_LEN / 2 + grow,
        wing / 2 + grow,
        wing * KEY_WAIST / 2 + grow,
    )
    outline2d = [(-half_l, -half_w), (0, -half_n), (half_l, -half_w),
                 (half_l, half_w), (0, half_n), (-half_l, half_w)]  # fmt: skip
    ring = []
    for u, v in outline2d:  # u along the rail, v across it
        x, y = (v, u) if axis == 0 else (u, v)
        ring.append(Vector((centre.x + x, centre.y + y)))
    bot = [bm.verts.new((p.x, p.y, z0)) for p in ring]
    top = [bm.verts.new((p.x, p.y, z1)) for p in ring]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    return ring


def backed(x: float, y: float) -> bool:
    """True if the frame's back face (z ~ 0) is solid at (x, y)."""
    ok, loc, *_ = frame.ray_cast(Vector((x, y, -5)), Vector((0, 0, 1)), depsgraph=dg)
    return ok and loc.z < 0.5


cut_bm = bmesh.new()
keys = []
# (name, axis across the rail, side): N/S keys cross the x=0 seam on the top/bottom
# rails; E/W keys cross the y=0 seam on the right/left rails
for name, axis, sign in (("N", 1, 1), ("S", 1, -1), ("E", 0, 1), ("W", 0, -1)):
    inner, outer = strip(axis, sign)
    wing = min(KEY_WING, outer - inner - 2 * (KEY_CLEAR + MARGIN))
    assert wing >= 3.5, f"key {name}: strip {outer - inner:.1f} mm too narrow for a key"
    c = (inner + outer) / 2 * sign
    centre = Vector((0, c)) if axis == 1 else Vector((c, 0))
    ring = butterfly(cut_bm, centre, axis, wing, KEY_CLEAR, -1.0, KEY_DEPTH)
    for p in ring:  # every recess corner, pushed out by MARGIN, must still be backed
        q = p + (p - centre).normalized() * MARGIN
        assert backed(q.x, q.y), f"key {name}: recess breaks out near {q[:]}"
    kb = bmesh.new()
    butterfly(kb, centre, axis, wing, 0.0, 0.0, KEY_DEPTH - KEY_PROUD)
    key = mesh.from_bmesh(f"Key_{name}", kb, parts)
    key.color = (0.9, 0.55, 0.2, 1)
    keys.append((name, wing, outer - inner))

cutter = mesh.from_bmesh("Cut_Keys", cut_bm, scene.work())
cutter.display_type = "WIRE"
cutter.hide_render = True

big = max(dims) * 2
for name, (sx, sy) in (
    ("TR", (1, 1)),
    ("TL", (-1, 1)),
    ("BL", (-1, -1)),
    ("BR", (1, -1)),
):
    lo = Vector((min(0, sx * big), min(0, sy * big), -1))
    hi = Vector((max(0, sx * big), max(0, sy * big), dims.z + 10))
    piece = mesh.from_bmesh(f"Piece_{name}", bmesh.new(), parts)
    section_piece.apply(piece, Source=frame, Box_Min=lo, Box_Max=hi, Cutter=cutter)
for clip in (o for o in scene.model().objects if o.name.startswith("Clip_")):
    parts.objects.link(clip)

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
for o in parts.objects:
    if o.name.startswith("Piece_"):
        w, h, d = o.evaluated_get(dg).dimensions
        assert max(w, h) <= BED, (
            f"{o.name} {w:.1f} x {h:.1f} does not fit the {BED} bed"
        )
        print(f"sections: {o.name} {w:.1f} x {h:.1f} x {d:.1f} mm")
for name, wing, avail in keys:
    print(
        f"sections: Key_{name} {KEY_LEN:.0f} x {wing:.1f} mm in a {avail:.1f} mm strip"
    )
