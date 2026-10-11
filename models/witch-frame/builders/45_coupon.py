# Seam coupon: a cheap test print of the real E seam (the thinnest tenon, the worst case)
# before the 4 pieces. Each coupon is two rail offcuts COUPON_LEN along the seam, trimmed a
# few mm above the mortise's gable, with the frame's own mortise, seam back chamfer, rabbet
# and glazing lip, plus a copy of Tenon_E. Notches across the top count the clearance step
# (1 = 0.10, 2 = 0.15, 3 = 0.20).
#
# COUPONS lists (clearance, ledge). Round 1 (0.10/0.15/0.20, flat) picked TENON_CLEAR 0.10,
# but the lip's flat 3.7 mm ceiling at z = RABBET sagged with supports off. Round 2 prints
# 0.10 twice: "Flat" as the frame is (sliced with supports), and "Chamfer" with a 45 deg
# wedge filling the rabbet corner under the lip so it prints self-supporting. A full wedge
# takes the glazing's seat, so that one is only a print test.
#
# Coupon collection: beside the model (+X), not rendered. Pack it on its own with
# `blend print-pack witch-frame --collection Coupon` (print/coupon/).
import importlib
import math
import sys
from pathlib import Path

import bmesh
import bpy
from kit import mesh, scene
from mathutils import Vector
from patterns import section_piece

sys.path.insert(0, str(Path(__file__).parent))
import joinery

importlib.reload(joinery)
import frame_geo
from joinery import (
    TENON_END,
    TENON_LEN,
    WALL,
    _co,
    _hull_into,
    gable,
    prism,
    seam_wedge,
)

SEAM = "E"
STEPS = (0.10, 0.15, 0.20)  # clearance per side; notches = index + 1
COUPONS = ((0.10, "Flat"), (0.10, "Chamfer"))  # (clearance, ledge)
COUPON_LEN = TENON_LEN / 2 + TENON_END + 4.0  # each offcut, along the seam
INBOARD = 12.0  # offcut runs this far inboard of the tenon (keeps the rabbet + lip)
OFFSET = Vector((300.0, 0.0, 0.0))  # beside the model, +X
SPACING = 60.0  # between coupons
NOTCH = (1.0, 0.8, 2.5)  # width, depth, pitch
RABBET = frame_geo.DEFAULTS["rabbet"]  # z of the lip's ceiling (glazing seat)

frame = bpy.data.objects["Frame"]
tenon = bpy.data.objects[f"Tenon_{SEAM}"]
s0, s1, z0, z1 = tenon["fit"]
seam_axis, side = tenon["seam"]
across = 1 - seam_axis
coll = scene.collection("Coupon")
coll.hide_render = True
scene.clear(coll)

dims = frame.evaluated_get(bpy.context.evaluated_depsgraph_get()).dimensions
a0, a1 = s0 - INBOARD, dims[across] / 2 + 1.0  # across the rail, from the centre
top = z1 + (s1 - s0) / 2 + max(c for c, _ in COUPONS) * math.sqrt(2) + WALL + 2.0
r_sight = frame_geo.sight_size()[across] / 2  # lip edge
r_rabbet = frame_geo.rabbet_size()[across] / 2  # rabbet wall


def lip_wedge(name, b0, b1, at):
    """45 deg wedge in the rabbet corner under the lip, b0..b1 along the seam: from the
    sight edge at z RABBET down the full lip width to the rabbet wall. It runs 0.5 into
    the wall and the lip so the union overlaps solid."""
    e, lip = 0.5, r_rabbet - r_sight
    sec = [(r_sight, RABBET), (r_rabbet, RABBET - lip), (r_rabbet + e, RABBET - lip),
           (r_rabbet + e, RABBET + e), (r_sight + e, RABBET + e)]  # fmt: skip
    bm = bmesh.new()
    _hull_into(bm, [_co(seam_axis, t, d * side, z) for t in (b0, b1) for d, z in sec])
    w = mesh.from_bmesh(name, bm, scene.work())
    w.location = at
    return w


for i, (clear, ledge) in enumerate(COUPONS):
    tag = f"C{round(clear * 100):02d}_{ledge}"
    notches = STEPS.index(clear) + 1
    host_at = OFFSET.copy()
    host_at[seam_axis] += (i - (len(COUPONS) - 1) / 2) * SPACING

    cut = bmesh.new()
    prism(
        cut,
        gable(s0, s1, z0, z1, clear),
        seam_axis,
        side,
        TENON_LEN + 2 * TENON_END,
    )
    seam_wedge(cut, seam_axis, side, a0 - 1, a1 + 1)
    for end in (-1, 1):  # notches across the top of each offcut, at its far end
        for k in range(notches):
            at = end * (COUPON_LEN - 2.0 - k * NOTCH[2])
            for v in bmesh.ops.create_cube(cut, size=1.0)["verts"]:  # corners at +-0.5
                c = Vector((0, 0, top + (1 - NOTCH[1]) / 2 + v.co.z * (NOTCH[1] + 1)))
                c[seam_axis] = at + v.co[seam_axis] * NOTCH[0]
                c[across] = ((a0 + a1) / 2 + v.co[across] * (a1 - a0 + 2)) * side
                v.co = c
    cutter = mesh.from_bmesh(f"Cut_Coupon_{tag}", cut, scene.work())
    cutter.display_type = "WIRE"
    cutter.hide_render = True

    for half, (b0, b1) in (("A", (-COUPON_LEN, 0)), ("B", (0, COUPON_LEN))):
        lo, hi = Vector((0, 0, -1)), Vector((0, 0, top))
        lo[seam_axis], hi[seam_axis] = b0, b1
        lo[across], hi[across] = sorted((a0 * side, a1 * side))
        piece = mesh.from_bmesh(f"Coupon_{tag}_{half}", bmesh.new(), coll)
        piece.location = host_at
        section_piece.apply(piece, Source=frame, Box_Min=lo, Box_Max=hi, Cutter=cutter)
        if ledge == "Chamfer":
            wedge = lip_wedge(f"Add_Coupon_{tag}_{half}", b0, b1, host_at)
            mesh.boolean(piece, wedge, op="UNION")
    t = bpy.data.objects.new(f"Coupon_{tag}_Tenon", tenon.data)
    t.location = host_at
    t.color = tenon.color
    coll.objects.link(t)

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
for o in coll.objects:
    w, h, d = o.evaluated_get(dg).dimensions
    print(f"coupon: {o.name} {w:.1f} x {h:.1f} x {d:.1f} mm")
