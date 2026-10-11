# Tenon joinery shared by 40_sections (the frame's seams) and 45_coupon (clearance test
# prints). Sections are 2D (distance across the rail, z); prisms extrude them along the
# seam axis, centred on the seam plane. Not an NN_ builder: build_all skips it.
import math

import bmesh
import bpy
from mathutils import Vector

TENON_LEN = 32.0  # across the seam, half in each piece
TENON_W = 6.0  # max thickness across the rail (fitted down to the strip)
TENON_MIN = (
    3.0  # thinner than this and the seam needs a different joint (E strip: 7.8 mm)
)
TENON_CLEAR = 0.10  # mortise clearance per side (PLA, glued); 2026-10-11 coupon on P1S: 0.10 best, all slide
TENON_END = 0.5  # extra mortise depth at each blind end
TENON_CHAMFER = 0.4  # 45 deg on every tenon edge
WALL = 2.0  # min plastic around a mortise (5 lines at 0.4 mm)
SEAM_CHAMFER = 0.4  # 45 deg relief on the back edge of each seam face (elephant's foot)


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


def _hull_into(bm, pts, chamfer=0.0) -> None:
    tmp = bmesh.new()
    for co in pts:
        tmp.verts.new(co)
    bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    bmesh.ops.dissolve_limit(
        tmp, angle_limit=0.001, verts=tmp.verts[:], edges=tmp.edges[:]
    )
    if chamfer:
        bmesh.ops.bevel(
            tmp, geom=tmp.edges[:], offset=chamfer, segments=1, affect="EDGES"
        )
    me = bpy.data.meshes.new("_hull")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def _co(seam_axis: int, along: float, across: float, z: float) -> Vector:
    co = Vector((0, 0, z))
    co[seam_axis], co[1 - seam_axis] = along, across
    return co


def prism(bm, poly, seam_axis: int, side: int, length: float, chamfer=0.0) -> None:
    """Extrude a convex section (across the rail, z) along the seam axis, centred on the
    seam, into bm; optionally chamfer every edge."""
    pts = [
        _co(seam_axis, t, s * side, z)
        for t in (-length / 2, length / 2)
        for s, z in poly
    ]
    _hull_into(bm, pts, chamfer)


def seam_wedge(bm, seam_axis: int, side: int, a: float, b: float) -> None:
    """45 deg SEAM_CHAMFER wedge under the seam plane, across the rail from a to b
    (distances from the centre on `side`). Its top is a 0.1 mm land, not an edge, so no
    cutter vertex sits on the seam plane (degenerate boolean faces)."""
    d, land = SEAM_CHAMFER, 0.05
    wedge = [(-d - 1, -1), (d + 1, -1), (land, d - land), (-land, d - land)]
    pts = [_co(seam_axis, s, t * side, z) for t in (a, b) for s, z in wedge]
    _hull_into(bm, pts)
