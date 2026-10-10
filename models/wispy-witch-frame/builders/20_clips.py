# Turn clips: 8 recessed pockets on the frame back (two per corner) + the clips themselves.
#
# Stack (z up from the wall/back plane), all cut to the 9x12" art size: glazing z 7-9
# against the lip, art on its 3 mm backboard z 4-7; clips z 1-4 press the backboard's back.
# Each clip pivots on a countersunk M3 screw 6 mm outside the rabbet edge. Closed it points
# inward (overhang ~5.5 mm onto the backboard); swung 90 deg toward the corner it clears
# the rabbet, so the stack drops in. The pocket box covers that sweep.
import math
import sys
from pathlib import Path

import bmesh
import bpy
from kit import materials, mesh, scene
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).parent))
import frame_geo

POCKET_Z = frame_geo.CLIP_ZONE  # pocket depth into the back
CLIP_T = 3.0
CLIP_R = 4.5  # stadium end radius (clip width 9)
CLIP_L = 7.5  # pivot-to-tip-centre: overhang = L + R - PIVOT_OUT
PIVOT_OUT = 6.0  # pivot distance outside the rabbet edge
FROM_CORNER = 22.0  # pivot distance from the rabbet corner along the edge
PILOT_D, PILOT_TOP = 2.6, 10.0  # M3 self-tap pilot, up to z=10 (>= 3.5 mm skin above)
SCREW_D, CSK_D = 3.3, 6.4

frame = bpy.data.objects["Frame"]
rw, rh = frame_geo.rabbet_size()


def pivots():
    """(pivot, inward, toward_corner) per clip, in the XY plane."""
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            # on the top/bottom edge, then on the left/right edge, near corner (sx, sy)
            out.append(
                (
                    Vector((sx * (rw / 2 - FROM_CORNER), sy * (rh / 2 + PIVOT_OUT))),
                    Vector((0, -sy)),
                    Vector((sx, 0)),
                )
            )
            out.append(
                (
                    Vector((sx * (rw / 2 + PIVOT_OUT), sy * (rh / 2 - FROM_CORNER))),
                    Vector((-sx, 0)),
                    Vector((0, sy)),
                )
            )
    return out


def _frame_xform(piv, inward, z):
    """Right-handed matrix mapping local (u along the edge, v outward, z) to world."""
    outward = -inward
    u = Vector((outward.y, -outward.x))
    m = Matrix.Identity(4)
    m.col[0][:3] = (u.x, u.y, 0)
    m.col[1][:3] = (outward.x, outward.y, 0)
    m.col[3][:3] = (piv.x, piv.y, z)
    return m


def _top_z(x, y):
    ok, loc, *_ = frame.ray_cast(Vector((x, y, 500)), Vector((0, 0, -1)))
    return loc.z if ok else None


cut_bm, pilot_bm = bmesh.new(), bmesh.new()
for piv, inward, along in pivots():
    # pocket box: u in [-(R+.5), L+R+.5], v from 1 mm inside the rabbet to R+.5 past pivot
    m = _frame_xform(piv, inward, 0)
    toward = (
        1 if (m.col[0].xy @ along) > 0 else -1
    )  # which local u points to the corner
    u0, u1 = sorted((-toward * (CLIP_R + 0.5), toward * (CLIP_L + CLIP_R + 0.5)))
    v0, v1 = -(PIVOT_OUT + 1.0), CLIP_R + 0.5
    for u, v in ((u0, v1), (u1, v1)):  # outer corners must stay inside the frame
        w = m @ Vector((u, v, 0))
        z = _top_z(w.x, w.y)
        assert z and z > POCKET_Z + 3, f"pocket breaks out near {w.xy[:]}: top {z}"
    zp = _top_z(piv.x, piv.y)
    assert zp - PILOT_TOP >= 3.0, f"pilot skin {zp - PILOT_TOP:.1f} mm too thin"
    box = bmesh.ops.create_cube(cut_bm, size=1)["verts"]
    for vtx in box:
        c = vtx.co
        vtx.co = m @ Vector(
            (
                u0 + (c.x + 0.5) * (u1 - u0),
                v0 + (c.y + 0.5) * (v1 - v0),
                -1 + (c.z + 0.5) * (POCKET_Z + 1),
            )
        )
    cyl = bmesh.ops.create_cone(
        pilot_bm,
        segments=24,
        radius1=PILOT_D / 2,
        radius2=PILOT_D / 2,
        depth=PILOT_TOP + 1,
        cap_ends=True,
    )["verts"]
    bmesh.ops.translate(pilot_bm, verts=cyl, vec=(piv.x, piv.y, (PILOT_TOP - 1) / 2))

cut = mesh.from_bmesh("Cut_ClipPockets", cut_bm, scene.work())
pil = mesh.from_bmesh("Cut_Pilots", pilot_bm, scene.work())
for c in (cut, pil):
    mesh.boolean(frame, c).solver = "EXACT"
mesh.apply_modifiers(frame)
mesh.clean(frame)


def clip_bmesh():
    """Stadium plate, ends at (0,0) and (L,0), with a countersunk pivot hole at the origin."""
    bm = bmesh.new()
    seg = 16
    ring = []
    for i in range(seg + 1):  # tip end, right half-circle
        a = -math.pi / 2 + math.pi * i / seg
        ring.append((CLIP_L + CLIP_R * math.cos(a), CLIP_R * math.sin(a)))
    for i in range(seg + 1):  # pivot end, left half-circle
        a = math.pi / 2 + math.pi * i / seg
        ring.append((CLIP_R * math.cos(a), CLIP_R * math.sin(a)))
    bot = [bm.verts.new((x, y, 0)) for x, y in ring]
    face = bm.faces.new(bot)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, CLIP_T))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


pla = materials.principled("PLA_Matte", "#8A8496", roughness=0.65)
hole_bm = bmesh.new()
bmesh.ops.create_cone(
    hole_bm,
    segments=24,
    radius1=SCREW_D / 2,
    radius2=SCREW_D / 2,
    depth=CLIP_T * 3,
    cap_ends=True,
)
csk = bmesh.ops.create_cone(  # 90-degree countersink opening at the clip's underside (z=0)
    hole_bm,
    segments=24,
    radius1=CSK_D / 2 + 0.6,
    radius2=0.01,
    depth=CSK_D / 2 + 0.6,
    cap_ends=True,
)["verts"]
bmesh.ops.translate(hole_bm, verts=csk, vec=(0, 0, (CSK_D / 2 + 0.6) / 2 - 0.6))
hole = mesh.from_bmesh("Cut_ClipHole", hole_bm, scene.work())

for i, (piv, inward, along) in enumerate(pivots(), 1):
    clip = mesh.from_bmesh(f"Clip_{i:02d}", clip_bmesh())
    mod = mesh.boolean(clip, hole)
    mod.solver, mod.use_self = "EXACT", True
    mesh.apply_modifiers(clip)
    mesh.clean(clip)
    # closed pose: tip points inward over the backboard; underside at z = POCKET_Z - CLIP_T
    m = _frame_xform(piv, inward, POCKET_Z - CLIP_T)
    rot = Matrix.Rotation(-math.pi / 2, 4, "Z")  # local +x (tip) -> -v (inward)
    clip.data.transform(m @ rot)
    clip.data.update()
    for p in clip.data.polygons:
        p.use_smooth = False
    materials.assign(clip, pla)
print("clips ok")
