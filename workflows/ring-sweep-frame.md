# Ring-sweep frame

A watertight, profiled frame or bezel built as one bmesh: a stack of rings with the same vertex count, bridged in a loop. Use it for a picture frame, mirror surround, bezel, lid rim or any ring-shaped solid with a custom outline and cross-section.

## When to use
- The outer outline is freeform (bowed sides, horn tips, wobble) but the opening is a plain rectangle or ellipse.
- The cross-section varies from outside to inside (sloped or cove face, sightwell, lip, rabbet), and you want it parametric so depth and curve can be explored and changed late.
- You need a printable solid: 0 non-manifold edges, no booleans for the main body.

## Steps
1. **Rings.** Sample every ring with the same count: 4 sides × N, corners shared, CCW. Sample *i* on the outline must correspond to sample *i* on each inner rectangle, side for side. Corners then map to corners, and the face gets hip lines from tip to opening corner for free.
2. **Outline.** Each side runs tip to tip, offset inward by `sag * sin(pi t) ** k`:
   - k < 1 gives sharp horn tips and a flat middle; k > 1 gives soft tips.
   - Optional wobble: low-frequency seeded sines × `sin(pi t)`, so the tips stay put.
3. **Profile.** List the rings in order around the cross-section and bridge each to the next, cyclically:
   - outline z=0 → outline z=h_outer
   - face rings (lerp outline → sight rect; z follows linear, cove `s**p` or convex `1-(1-s)**p`)
   - sight rect z=H → sight rect z=rabbet (sightwell) → rabbet rect z=rabbet (lip) → rabbet rect z=0 → back to the start.
4. **Normals and shading.** `recalc_face_normals`, smooth all faces, and mark edges sharp above about 35°.
5. **Validate in the builder.** Assert the envelope against the brief, the min wall between outline and rabbet (signed distance per outline sample), and that `h_outer > rabbet + 2`.
6. **Back features** (clip pockets, screw pilots) come afterwards as EXACT booleans with disjoint cutter meshes, then are applied. Raycast the top surface at each feature to assert skin thickness first.
7. **Explore with a variant grid** (see [variant-grid-exploration](variant-grid-exploration.md)) before fixing the params.

## bpy
```python
def rect_ring(w, h, n):  # CCW, corners shared
    c = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [
        Vector(c[s]).lerp(Vector(c[(s + 1) % 4]), j / n)
        for s in range(4)
        for j in range(n)
    ]


bm = bmesh.new()
vr = [[bm.verts.new(co) for co in ring] for ring in rings]  # rings: list of [(x, y, z)]
k = len(rings[0])
for r in range(len(vr)):
    A, B = vr[r], vr[(r + 1) % len(vr)]
    for j in range(k):
        bm.faces.new((A[j], A[(j + 1) % k], B[(j + 1) % k], B[j]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# right-handed local frame on an edge (u along the edge, v outward)
u = Vector(
    (outward.y, -outward.x)
)  # NOT "along" from the caller: half the corners mirror
```
Full implementation: `sessions/2026-10-10-wispy-witch-frame/builders/frame_geo.py` (outline, `validate`, `build_bmesh`) and `20_clips.py` (pockets, pilots, clips).

## Gotchas
- **Lerping the face rings** from outline to sight rect works because both are star-shaped around the centre. A concave outline that folds back would self-intersect, so keep the sag modest relative to the side length.
- **The min wall caps the bow.** With a fixed backboard inside a fixed envelope, the bow is at most (envelope − rabbet)/2 − wall. Compute it before promising a dramatic curve.
- **Wobble eats wall.** Validate with the wobble on; drop the sag by about the wobble amplitude.
- **Local frames for features on each edge:** derive the second axis from the first. Building from two independent "along"/"outward" vectors gives left-handed matrices on half the corners, which mirror the cutters and flip normals.
- **Section-cut copies:** offset them *toward* the viewing camera, or the real model sits between the camera and the cut (see [render-views-and-sections](render-views-and-sections.md)).

## Models
- wispy-witch-frame (2026-10-10): 3D-printable frame with bat-wing bowed sides, cove face, 33 mm sightwell, 9 mm rabbet (glazing + art + clip zone) and 8 turn-clip pockets.
