# Print sectioning, pass 1: mark seams only (Work). Four corner L-pieces split at the
# mid-sides; each must fit the 256 mm bed. Joinery comes in a later pass.
import bpy
from kit import mesh, scene

BED = 256.0
SEAM_T = 0.4

frame = bpy.data.objects["Frame"]
verts = frame.evaluated_get(
    bpy.context.evaluated_depsgraph_get()
).data.vertices  # GN mesh
xs = [v.co.x for v in verts]
ys = [v.co.y for v in verts]
zs = [v.co.z for v in verts]
w, h, d = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)

for name, size in (
    ("Seam_X", (SEAM_T, h + 20, d + 10)),
    ("Seam_Y", (w + 20, SEAM_T, d + 10)),
):
    seam = mesh.box(name, size, (0, 0, d / 2), scene.work())
    seam.display_type = "WIRE"
    seam.hide_render = True

piece = (w / 2, h / 2)  # each corner piece's footprint (seams at x=0, y=0)
assert max(piece) <= BED, f"corner piece {piece} does not fit {BED} bed"
print(
    f"sections: 4 corner pieces {piece[0]:.1f} x {piece[1]:.1f} x {d:.1f} mm (bed {BED})"
)
