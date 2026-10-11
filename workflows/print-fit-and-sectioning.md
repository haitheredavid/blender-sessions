# Print fit and sectioning

Size a 3D-printed enclosure or frame around real parts: a rabbet stack, turn-clip retention, and splitting into pieces for the printer bed. Use it for picture frames, panels, lids, or anything that holds sheet goods and is bigger than the bed.

## When to use
- The print holds stacked sheets (glazing, art, backboard, mat) that must drop in from the back and be retained.
- The part exceeds the bed and must be split.

## Steps
1. **Model in mm** (`blend new <s> --unit mm`), 1 BU = 1 mm, back face on z=0. That is also the print orientation: face up, so a sloped top needs no supports.
2. **Define the stack as constants** in the geometry module and derive everything from them:
   - Sheet sizes: `ART`, `BACKBOARD`, `GLAZING` as (w, h, t). `CLIP_ZONE` for the clips.
   - Rabbet footprint: the largest sheet + 0.5 mm clearance per side.
   - Rabbet depth: `CLIP_ZONE + Σ sheet thicknesses`. The front sheet (glazing) sits against the lip.
   - Sight opening: art − 2 × overlap (1/8" per side hides the paper edge).
   - Hide the backboard by cutting it to the art size.
3. **Make the outer edge clear the rabbet:** `h_outer > rabbet + 2`, or the back pockets break through. Assert it.
4. **Turn clips.**
   - Each clip is a one-ended stadium, 16.5 × 9 × 3 mm, with a countersunk M3 pivot 6 mm outside the rabbet edge, in a 4 mm back pocket. Closed, it points inward and overhangs the stack about 6 mm. Swung 90° toward the corner, it clears the rabbet.
   - The pocket box covers that quarter sweep.
   - Place clips near the corners, where the frame is widest.
   - Pilot holes: Ø2.6 for self-tapping M3 into PLA. Raycast the face to keep ≥ 3 mm of skin above each pilot.
5. **Sectioning, pass 1:** mark seams as thin Work planes and assert each piece's footprint is ≤ the bed. Corner L-pieces split at the mid-sides give 4 pieces up to (W/2 × H/2).
6. **Joinery:** a glued loose tenon inside each seam (below). Measure the walls before choosing a joint that is recessed into a face: the back strip of a sloped frame is often too narrow. Prefer seams in thick sections; the mid-sides of a bowed frame are the *thinnest*.

## bpy
```python
CLIP_ZONE = 4.0
ART = (9 * IN, 12 * IN)
BACKBOARD = (9 * IN, 12 * IN, 3.0)  # cut to art size: invisible
GLAZING = (9 * IN, 12 * IN, 2.0)
rabbet_depth = CLIP_ZONE + BACKBOARD[2] + GLAZING[2]  # 9
rabbet_wh = [max(a, b) + 2 * 0.5 for a, b in zip(BACKBOARD[:2], GLAZING[:2])]

ok, loc, *_ = frame.ray_cast(Vector((x, y, 500)), Vector((0, 0, -1)))
assert loc.z - PILOT_TOP >= 3.0  # skin above the pilot
```
Reference: `models/witch-frame/builders/frame_geo.py`, `20_clips.py`, `joinery.py` (`gable`, `prism`, `seam_wedge`), `40_sections.py` (tenon `fit()`), `45_coupon.py` (clearance coupon), `70_assembly.py` (tenons slide in, pieces close along x then y).

## Live sections + loose tenons (GN)
1. Keep the assembled part in Model (renders, variants). Put printable parts in a **Print** collection (`kit.scene.parts()`). Set `[export] collection = "Print"` and run `blend check <m> --collection Print --strict`.
2. Each piece is an empty mesh with `patterns.section_piece`:
   - Source = the assembled object;
   - Box Min/Max = its quadrant;
   - Cutter = a joinery-recess mesh in Work.

   Pieces follow every edit of the source.
3. **Loose tenon inside each seam** (glued; hidden; uses the full seam profile):
   - Slice the evaluated source with `bmesh.ops.bisect_plane` at 5 stations along the tenon (both ends + clearance, quarters, the seam). Keep the cut edges on the rail's side as 2D segments (distance across the rail, z).
   - Fit the mortise (tenon + clearance) so every sampled point on it is inside the profile (even-odd) and >= WALL (2 mm = 5 lines at 0.4) from every segment. Width = as wide as fits, capped; then grow the height.
   - Cut both mortises with one prism per seam (tenon length + 2 × 0.5 mm end gap, section offset by 0.15). The tenon is the same prism with every edge chamfered 0.4 (beat the elephant's foot, lead in).
   - **Gable roof:** pieces print back face down, so the mortise is a horizontal tunnel. Give the mortise and the tenon a 45° roof that rises w/2 above the walls. Offset the gable outward by the clearance: the walls and floor move by c and the apex by c·√2. Fit the whole gable outline against WALL. Then the roof prints without bridging, and no sagging bridge strand eats the top clearance.
   - Build each prism with `bmesh.ops.convex_hull` over the section's two end rings, then `dissolve_limit` to get flat n-gons, then `bevel` for the chamfer.
   - Assert a minimum tenon thickness, so a frame edit that starves a seam fails loudly.
4. **Seam back chamfer:** cut a 45° wedge (0.4 mm) under each seam plane along the back face, so first-layer squish can't hold the seam open. Use one wedge per rail, so the cutter doesn't self-intersect where the seams cross. Give its top a 0.1 mm land instead of an apex, so no cutter edge lies on the seam plane.
5. **Clearance coupon before the frame:** cut the worst seam (the thinnest tenon) short with `section_piece`. Use 2 × (tenon/2 + end gap + 4 mm) along the seam, trim a few mm above the mortise, and make one coupon per clearance (0.10 / 0.15 / 0.20). Mark each with 1/2/3 notches cut by the same cutter. Keep the coupons in their own collection beside the model and pack them with `blend print-pack <m> --collection Coupon`. Store each tenon's fit on the tenon (`tenon["fit"]`) so the coupon reuses it exactly.
6. Clips and other shared parts can be linked into Print as well as Model (one object, two collections). When rebuilding Print, unlink shared objects; only delete Print-only ones.

## Gotchas
- **A flat mortise roof bridges, and a bridge sags into the clearance.** A 3-6 mm bridge droops about 0.1-0.2 mm, which is as much as the clearance. Use a 45° gable roof on the mortise and the tenon, and re-fit with the apex included.
- **A recess in a narrow face leaves thin fins.** Butterfly keys in an 8 mm back strip left 1.07 mm walls beside a 9 mm-deep rabbet (0.7 at a mouth flare). Measure the walls, then move the joint into the seam faces (loose tenon).
- **A cutter vertex on a section plane gives degenerate boolean faces.** A fillet whose middle vertex landed on x=0 (the seam) left zero-area slivers. Use odd arc segment counts, or offset the cutter off the plane.
- **Clearance is a perpendicular offset.** Adding `grow` to a polygon's half-widths under-clears its angled edges. Offset each edge along its normal and intersect, and grow convex fillets by +d and shrink concave ones by -d.
- **Builders and `blend check/export` read the active scene.** If the window was left on another scene (e.g. Assembly), the Print parts don't evaluate (0 verts) and check finds nothing. Switch `window.scene` to the main scene before building and saving.
- **OBJ export is Y-up** (mm values are correct). Some slicers lay it on its side, so rotate it before slicing.
- **Changing the stack moves the clip and pocket positions.** Update any hard-coded view, camera and section targets too, or derive them from the constants.
- **Stack thicknesses are assumptions** (2 mm acrylic, 3 mm board). Record them in notes and confirm with the user.

## Models
- witch-frame (2026-10-11, print-joinery): gable mortises and tenons (9.9-11.0 tall), a 0.4 seam back chamfer, and an E-seam clearance coupon (3 × 2 offcuts + tenon, 17.6 cm³).
- witch-frame (2026-10-11, key-tolerances): butterfly keys -> loose tenons fitted to each seam profile with 2 mm walls (3.4-6.0 x 8.2-8.4 x 32 mm).
- witch-frame (2026-10-10, joinery): live GN_SectionPiece corner pieces + per-seam-fitted butterfly keys; Print collection export.
- witch-frame (2026-10-10): 11×14" frame for 9×12" art; 9 mm rabbet (glazing, art on board, clip zone), 8 turn clips, 4 corner sections (139.7 × 177.8) for a 256 mm bed.
