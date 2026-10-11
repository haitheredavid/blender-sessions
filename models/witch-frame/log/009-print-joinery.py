# step 9: gable (45 deg) mortise roof + matching gable tenons, re-fit with WALL clear of apex (N 4.2x10.1, S 6.0x11.0, E 3.4x9.9, W 3.8x9.9 total); 0.4 back chamfer on every seam face; rebuilt via build_all
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
# Pieces print back face down, so the mortise (and the tenon) has a 45 deg gable roof: it
# prints without bridging, and the fit keeps WALL clear of the gable's apex too.
# The back edge of every seam face gets a SEAM_CHAMFER, so first-layer squish can't hold
# the seam open.
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
SEAM_CHAMFER = 0.4  # 45 deg relief on the back edge of each seam face (elephant's foot)
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


def gable(s0, s1, z0, z1, grow=0.0) -> list:
    """Tenon section (s0..s1 wide, walls z0..z1, 45 deg roof to an apex w/2 above z1),
    offset outward by `grow` (true offset: walls and floor by grow, apex by grow * sqrt 2)."""
    m, a = (s0 + s1) / 2, (s1 - s0) / 2 + grow
    apex = z1 + (s1 - s0) / 2 + grow * math.sqrt(2)
    return [
        (m - a, z0 - grow),
        (m + a, z0 - grow),
        (m + a, apex - a),
        (m, apex),
        (m - a, apex - a),
    ]


def mortise_ok(sections, s0, s1, z0, z1) -> bool:
    poly = gable(s0, s1, z0, z1, TENON_CLEAR)
    n = 8
    ring = [
        (ax + (bx - ax) * i / n, az + (bz - az) * i / n)
        for (ax, az), (bx, bz) in zip(poly, poly[1:] + poly[:1])
        for i in range(n)
    ]
    return all(clear_of(p, segs) for segs in sections for p in ring)


def fit(seam_axis: int, side: int) -> tuple[float, float, float, float]:
    """Largest tenon section (s0, s1, z0, z1) clear of the profile along its length:
    as wide as fits (<= TENON_W) with TENON_MIN walls under its gable, then as tall as
    fits. z1 is the top of the walls; the apex is (s1 - s0) / 2 above it."""
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


def prism(bm, poly, seam_axis: int, side: int, length: float, chamfer=0.0) -> None:
    """Extrude a section (across the rail, z) along the seam axis, centred on the seam,
    into bm; optionally chamfer every edge."""
    tmp = bmesh.new()
    for t in (-length / 2, length / 2):
        for s, z in poly:
            co = Vector((0, 0, z))
            co[seam_axis], co[1 - seam_axis] = t, s * side
            tmp.verts.new(co)
    bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    bmesh.ops.dissolve_limit(
        tmp, angle_limit=0.001, verts=tmp.verts[:], edges=tmp.edges[:]
    )
    if chamfer:
        bmesh.ops.bevel(
            tmp, geom=tmp.edges[:], offset=chamfer, segments=1, affect="EDGES"
        )
    me = bpy.data.meshes.new("_prism")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


cut_bm = bmesh.new()
tenons = []
# (name, seam axis, side): N/S tenons cross the x=0 seam in the top/bottom rails;
# E/W cross the y=0 seam in the right/left rails
for name, seam_axis, side in (("N", 0, 1), ("S", 0, -1), ("E", 1, 1), ("W", 1, -1)):
    s0, s1, z0, z1 = fit(seam_axis, side)
    w, h = s1 - s0, z1 - z0
    prism(
        cut_bm,
        gable(s0, s1, z0, z1, TENON_CLEAR),
        seam_axis,
        side,
        TENON_LEN + 2 * TENON_END,
    )
    tb = bmesh.new()
    prism(tb, gable(s0, s1, z0, z1), seam_axis, side, TENON_LEN, TENON_CHAMFER)
    tenon = mesh.from_bmesh(f"Tenon_{name}", tb, parts)
    tenon.color = (0.9, 0.55, 0.2, 1)
    tenons.append((name, w, h + w / 2, z0))
# seam back chamfers: a 45 deg wedge under each seam plane, from the sight opening out
# through the rail (wedges don't cross, so the cutter has no self-intersection). Its top
# is a 0.1 mm land, not an edge, so no cutter vertex sits on the seam plane.
d, land = SEAM_CHAMFER, 0.05
wedge = [(-d - 1, -1), (d + 1, -1), (land, d - land), (-land, d - land)]
for seam_axis, side in ((0, 1), (0, -1), (1, 1), (1, -1)):
    tmp = bmesh.new()
    for t in (dims[1 - seam_axis] / 4 * side, max(dims) * side):
        for s, z in wedge:
            co = Vector((0, 0, z))
            co[seam_axis], co[1 - seam_axis] = s, t
            tmp.verts.new(co)
    bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    me = bpy.data.meshes.new("_wedge")
    tmp.to_mesh(me)
    tmp.free()
    cut_bm.from_mesh(me)
    bpy.data.meshes.remove(me)
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
        f"sections: Tenon_{name} {TENON_LEN:.0f} x {w:.1f} x {h:.1f} mm (gable) at z {z0:.2f}, "
        f">= {WALL} mm walls"
    )
