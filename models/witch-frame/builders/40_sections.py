# Print sectioning + joinery: four corner pieces split at the mid-sides, joined by a
# glued loose tenon inside each seam.
#
# Pieces (Print collection) are live GN_SectionPiece cuts of Frame: edit the frame (its
# Control outline or modifier inputs) and the pieces follow. The seam faces are the full
# frame profile, so the joint hides inside them instead of in the narrow back strip
# (8-11 mm at the mid-sides, too thin for a recess with real walls).
#
# Each tenon is a chamfered bar running across its seam, TENON_LEN/2 into each piece.
# Its section is fitted to the frame profile at the seam, sampled over the tenon's whole
# length: >= WALL of plastic all round the mortise (back face, rabbet, outer edge, cove),
# width capped at TENON_W. One box per seam (Cut_Tenons) cuts both mortises: the tenon
# + TENON_CLEAR per side + TENON_END at each blind end (glue room, nozzle-rounded
# corners). Chamfers on every tenon edge ride over elephant's foot and lead it in.
# Pieces print back face down, so the mortise roof is a short bridge (the tenon width).
import math

import bmesh
import bpy
from kit import mesh, scene
from mathutils import Vector
from patterns import section_piece

BED = 256.0
TENON_LEN = 32.0  # across the seam, half in each piece
TENON_W = 6.0  # max thickness across the rail (fitted down to the strip)
TENON_MIN = (
    3.0  # thinner than this and the seam needs a different joint (E strip: 7.8 mm)
)
TENON_CLEAR = 0.15  # mortise clearance per side (PLA, glued)
TENON_END = 0.5  # extra mortise depth at each blind end
TENON_CHAMFER = 0.4  # 45 deg on every tenon edge
WALL = 2.0  # min plastic around a mortise (5 lines at 0.4 mm)
STEP = 0.1  # fitting resolution

frame = bpy.data.objects["Frame"]
parts = scene.parts()
for o in list(
    parts.objects
):  # rebuild Print: drop our pieces/tenons, unlink shared parts
    if len(o.users_collection) == 1:
        bpy.data.objects.remove(o, do_unlink=True)
    else:
        parts.objects.unlink(o)

dg = bpy.context.evaluated_depsgraph_get()
ev = frame.evaluated_get(dg)
dims = ev.dimensions
src = bmesh.new()
src.from_mesh(ev.data)
src.transform(frame.matrix_world)


def section(seam_axis: int, off: float, side: int) -> list:
    """Frame profile where the plane (seam_axis coord = off) crosses the rail on `side`:
    2D segments in (distance from centre across the rail, z)."""
    bm = src.copy()
    no = Vector((1, 0, 0)) if seam_axis == 0 else Vector((0, 1, 0))
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=no * off, plane_no=no)
    a = 1 - seam_axis  # across-the-rail axis
    out = []
    for e in cut["geom_cut"]:
        if isinstance(e, bmesh.types.BMEdge):
            p, q = (v.co for v in e.verts)
            if p[a] * side > 0 and q[a] * side > 0:
                out.append(((abs(p[a]), p.z), (abs(q[a]), q.z)))
    bm.free()
    return out


def clear_of(pt, segs) -> bool:
    """pt inside the profile (even-odd) and >= WALL from every edge of it."""
    px, pz = pt
    crossings = 0
    for (ax, az), (bx, bz) in segs:
        if (az > pz) != (bz > pz) and px < ax + (pz - az) * (bx - ax) / (bz - az):
            crossings += 1
        dx, dz = bx - ax, bz - az
        ll = dx * dx + dz * dz
        t = (
            0.0
            if ll == 0
            else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / ll))
        )
        if math.hypot(ax + t * dx - px, az + t * dz - pz) < WALL:
            return False
    return crossings % 2 == 1


def mortise_ok(sections, s0, s1, z0, z1) -> bool:
    g0, g1, h0, h1 = (
        s0 - TENON_CLEAR,
        s1 + TENON_CLEAR,
        z0 - TENON_CLEAR,
        z1 + TENON_CLEAR,
    )
    n = 8
    ring = [(g0 + (g1 - g0) * i / n, h) for i in range(n + 1) for h in (h0, h1)]
    ring += [(g, h0 + (h1 - h0) * i / n) for i in range(1, n) for g in (g0, g1)]
    return all(clear_of(p, segs) for segs in sections for p in ring)


def fit(seam_axis: int, side: int) -> tuple[float, float, float, float]:
    """Largest tenon section (s0, s1, z0, z1) clear of the profile along its length:
    centred on the back strip, as wide as fits (<= TENON_W), then as tall as fits."""
    half = TENON_LEN / 2 + TENON_END + TENON_CLEAR
    sections = [
        section(seam_axis, o, side) for o in (-half, -half / 2, 0, half / 2, half)
    ]
    z0 = WALL + TENON_CLEAR + STEP / 2  # floor clear of the back face
    back = [pt[0] for segs in sections for sg in segs for pt in sg if pt[1] < 0.01]
    lo, hi = min(back), max(back)  # widest the back strip gets; walls trim it below
    best = None
    s = lo
    while s < hi:
        w = TENON_MIN
        if mortise_ok(sections, s, s + w, z0, z0 + TENON_MIN):
            while w + STEP <= TENON_W and mortise_ok(
                sections, s, s + w + STEP, z0, z0 + TENON_MIN
            ):
                w += STEP
            if best is None or w > best[1] - best[0] + 1e-6:
                best = (s, s + w)
        s += STEP
    assert best, (
        f"seam {seam_axis}/{side}: no {TENON_MIN} mm tenon with {WALL} mm walls"
    )
    s0, s1 = best
    h = TENON_MIN
    while mortise_ok(sections, s0, s1, z0, z0 + h + STEP):
        h += STEP
    return s0, s1, z0, z0 + h


def bar(bm, centre: Vector, size: Vector, chamfer: float = 0.0) -> None:
    """Axis box into bm, optionally with every edge chamfered."""
    new = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    for v in new:
        v.co = centre + Vector(c * d for c, d in zip(v.co, size))
    if chamfer:
        edges = list({e for v in new for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=chamfer, segments=1, affect="EDGES")


cut_bm = bmesh.new()
tenons = []
# (name, seam axis, side): N/S tenons cross the x=0 seam in the top/bottom rails;
# E/W cross the y=0 seam in the right/left rails
for name, seam_axis, side in (("N", 0, 1), ("S", 0, -1), ("E", 1, 1), ("W", 1, -1)):
    s0, s1, z0, z1 = fit(seam_axis, side)
    across = (s0 + s1) / 2 * side
    c = (
        Vector((0, across, (z0 + z1) / 2))
        if seam_axis == 0
        else Vector((across, 0, (z0 + z1) / 2))
    )

    w, h = s1 - s0, z1 - z0
    # bar sizes as (along the tenon, across the rail, z); the tenon runs along the seam axis
    lw = (0, 1) if seam_axis == 0 else (1, 0)
    mortise, tenon_size = Vector((0, 0, h + 2 * TENON_CLEAR)), Vector((0, 0, h))
    mortise[lw[0]], mortise[lw[1]] = TENON_LEN + 2 * TENON_END, w + 2 * TENON_CLEAR
    tenon_size[lw[0]], tenon_size[lw[1]] = TENON_LEN, w
    bar(cut_bm, c, mortise)
    tb = bmesh.new()
    bar(tb, c, tenon_size, TENON_CHAMFER)
    tenon = mesh.from_bmesh(f"Tenon_{name}", tb, parts)
    tenon.color = (0.9, 0.55, 0.2, 1)
    tenons.append((name, w, h, z0))
src.free()

cutter = mesh.from_bmesh("Cut_Tenons", cut_bm, scene.work())
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
for name, w, h, z0 in tenons:
    print(
        f"sections: Tenon_{name} {TENON_LEN:.0f} x {w:.1f} x {h:.1f} mm at z {z0:.2f}, "
        f">= {WALL} mm walls"
    )
