# Tenon clearance coupon: a cheap test print to tune TENON_CLEAR before the 4 pieces.
#
# Three coupons, one per clearance in CLEARANCES. Each is the real E seam (the thinnest
# tenon, the worst case) cut short: two rail offcuts COUPON_LEN along the seam, trimmed a
# few mm above the mortise's gable, with the frame's own mortise, seam back chamfer and a
# copy of Tenon_E. 1/2/3 notches across the top of each offcut tell them apart. Pick
# the clearance that slides in by hand with glue room, then set joinery.TENON_CLEAR.
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
from joinery import TENON_END, TENON_LEN, WALL, gable, prism, seam_wedge

SEAM = "E"
CLEARANCES = (0.10, 0.15, 0.20)  # per side; one notch per step
COUPON_LEN = TENON_LEN / 2 + TENON_END + 4.0  # each offcut, along the seam
INBOARD = 12.0  # offcut runs this far inboard of the tenon (keeps the rabbet + lip)
OFFSET = Vector((300.0, 0.0, 0.0))  # beside the model, +X
SPACING = 60.0  # between coupons
NOTCH = (1.0, 0.8, 2.5)  # width, depth, pitch

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
top = z1 + (s1 - s0) / 2 + max(CLEARANCES) * math.sqrt(2) + WALL + 2.0


for i, clear in enumerate(CLEARANCES):
    tag = f"C{round(clear * 100):02d}"
    host_at = OFFSET.copy()
    host_at[seam_axis] += (i - 1) * SPACING

    cut = bmesh.new()
    prism(
        cut,
        gable(s0, s1, z0, z1, clear),
        seam_axis,
        side,
        TENON_LEN + 2 * TENON_END,
    )
    seam_wedge(cut, seam_axis, side, a0 - 1, a1 + 1)
    for end in (-1, 1):  # i + 1 notches across the top of each offcut, at its far end
        for k in range(i + 1):
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
    t = bpy.data.objects.new(f"Coupon_{tag}_Tenon", tenon.data)
    t.location = host_at
    t.color = tenon.color
    coll.objects.link(t)

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
for o in coll.objects:
    w, h, d = o.evaluated_get(dg).dimensions
    print(f"coupon: {o.name} {w:.1f} x {h:.1f} x {d:.1f} mm")
