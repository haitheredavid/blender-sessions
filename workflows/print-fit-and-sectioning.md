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
6. **Joinery (next pass):** alignment-pin holes plus glue, or a butterfly key recessed across each seam on the back. Prefer seams in thick sections; mid-sides of a bowed frame are the *thinnest*.

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
Reference: `models/witch-frame/builders/frame_geo.py`, `20_clips.py`, `40_sections.py`.

## Gotchas
- **OBJ export is Y-up** (mm values are correct). Some slicers lay it on its side, so rotate it before slicing.
- **Changing the stack moves the clip and pocket positions.** Update any hard-coded view, camera and section targets too, or derive them from the constants.
- **Stack thicknesses are assumptions** (2 mm acrylic, 3 mm board). Record them in notes and confirm with the user.

## Models
- witch-frame (2026-10-10): 11×14" frame for 9×12" art; 9 mm rabbet (glazing, art on board, clip zone), 8 turn clips, 4 corner sections (139.7 × 177.8) for a 256 mm bed.
