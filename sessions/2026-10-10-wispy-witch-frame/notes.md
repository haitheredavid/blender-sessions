# Notes

## Intent
3D-printable shadow-box frame for a 9x12" witch illustration on a 10x13" backboard. Motif from the user's sketch (`sessions/refs/wispy-witch-frame/sketch.jpeg`): sides bow inward, corners flare into sharp overshooting bat-wing tips; face slopes like a hip roof from a thin outer edge into a deep sightwell for shadow. Decisions: rabbet + turn clips, art on backboard (no glazing), 256 mm bed.

## Plan
### Session
- `just new wispy-witch-frame --unit mm` creates `sessions/2026-10-10-wispy-witch-frame/`.
- **Intent:** "3D-printable shadow-box frame for a 9×12" witch illustration: concave bat-wing sides with flared corner tips, a face sloping from a thin outer edge into a deep sightwell, and a rabbet with turn clips for a 10×13" backboard."
- **Tags:** 3d-print, frame, stylized, parametric, halloween.
- **References:** copy the sketch to `sessions/refs/wispy-witch-frame/sketch.jpeg` (gitignored), and import it into the **Ref** collection as an image empty for comparison.

### Fixed dimensions (mm)
| Item | Value |
|---|---|
| Art | 228.6 × 304.8 |
| Backboard | 254 × 330.2 × 3 |
| Sight opening (overlaps the art by 1/8" per side) | 222.25 × 298.45 |
| Rabbet pocket (+0.5 mm clearance per side) | 255 × 331.2, depth 7 |
| Outer tip-to-tip (limit 12×15" = 304.8 × 381) | default 300 × 375 |
| Wall outside the rabbet at mid-side | ≥ 6 |
| Total depth H (1–3" = 25–76) | explored below |

- **Rabbet depth 7:** the backboard sits at z 4–7 against the lip, and the clips sit in z 0.5–4.
- **Wall constraint:** the 6 mm minimum caps the inward bow (sag) at about 16 mm per side. This is the main tension in the brief.

### Parts and technique

### `Frame` (Model): `builders/10_frame.py`
- **Approach:** a parametric ring sweep in bmesh. `build_frame(name, p, offset)` builds one closed, watertight mesh from rings that all have the same vertex count: four sides × N samples, with corners shared.
- **Correspondence:** sample point *i* on the outer outline maps to sample *i* on each inner rectangle, side by side. Corner tips land on the opening's corners, which produces the hip lines from the sketch.
- **Outer outline:** each side runs from tip to tip, offset inward by `sag·sin(πt)^k`. The exponent k sets how flat the middle is.
- **Corner tips:** `flare` sets how far a tip overshoots along the diagonal, and `tip_sharp` sets how pointed it is.
- **Hand-drawn feel:** an optional `wobble` adds low-frequency seeded noise so the outline isn't perfectly symmetric.
- **Rings, from the outside in:**
  1. Outer outline at z=0, then at z=`h_outer` (10 mm), which forms the thin outer wall.
  2. Face rings that interpolate outline → sight rectangle with height `h_outer → H`, following `profile` (linear, cove/concave like a wing membrane, or convex).
  3. Sight rectangle at z=H down to z=7, which forms the sightwell (shadow).
  4. Lip underside, then the rabbet rectangle at z=7 down to z=0.
  5. A bottom loft back to the outer ring.
- **Result:** one manifold solid, with the back flat on z=0. That is also the print orientation, face up, so the sloped top needs no supports.
- **Clip pockets:** 8 pockets, two per side and placed toward the corners where the frame is wide. Each is 4 mm deep and straddles the rabbet edge, cut with a live boolean via `kit.mesh.boolean` (cutters go to Work). It is applied in the final build.
- **Screw pilots:** a Ø2.5 pilot hole for an M3 screw in each pocket.

### `Clip_01..08` (Model): `builders/20_clips.py`
- A one-ended turn button: a 22 × 9 × 3 mm stadium shape with a Ø3.2 pivot hole and a small bevel.
- Rotated parallel to the edge, it stays inside its pocket so the backboard can drop in. Rotated 90°, it overhangs the backboard by about 6 mm.
- Positioned in the closed (retaining) pose.

### Proxies (Ref, not exported): `builders/30_proxies.py`
- `Backboard_Proxy` and `Art_Proxy`: a deep night-blue plane, to judge the sightwell shadow in looks and renders.

### Section seams (Work, pass 1 only): `builders/40_sections.py`
- Four corner L-pieces with seams at the mid-sides. Each is about 150 × 188 mm and fits the 256 bed.
- The seams are shown as thin Work planes, with section bounding boxes checked against the bed.
- The pieces are not cut in this pass. Joinery is left for a later pass; candidates are alignment-pin holes plus glue, or a printed butterfly key across the seam on the back. Both go in the notes.

### Experiments (requirements 3, 4, 6)
- `builders/explore.py` is not NN-prefixed, so `build_all` skips it. It lays out variant grids side by side in an `Explore` collection by calling `build_frame` with different params. Grids are compared with `look` (top-down, and a 3/4 view with a section cut), then cleared.
1. **Edge study** at H=40:
   - sag {8, 12, 16} × tips {soft, sharp overshoot}: 6 variants.
   - Then wobble on/off for the favourite.
2. **Depth and slope study** with the chosen edge:
   - H {25, 40, 55} × profile {linear, cove, convex}: 9 variants.
   - Plus an outer-edge thickness check of 6 vs 10 mm.
- **Review:** I'll share the grid looks and recommend a pick, and you choose. The pick is written into `10_frame.py` defaults, and grid screenshots go to `out/`.

### Materials
- One material, `PLA_Matte`: charcoal #2A2730, roughness 0.65, via `kit.materials.principled`, on the frame and clips.
- `Art_Proxy`: #1C2A4A.

### Workflows
- Applies: `mcp-modeling-loop.md`.
- Likely new (candidates for `/done`):
  - **`ring-sweep-frame`:** corresponding-ring lofting for a watertight, profiled frame or bezel.
  - **`print-sectioning`:** splitting oversized prints at bed limits.

### Verification
- `just check wispy-witch-frame` should report:
  - non_manifold 0, loose geometry 0, degenerate 0, flipped 0.
  - Frame size ≤ 304.8 × 381 × H.
- A builder assert also checks the mid-side wall is ≥ 6 mm and that rabbet ≥ backboard + clearance.
- A clean rebuild via `build_all.py`, then `just render` (fit framing). Judge the sightwell shadow, and verify that the Ref proxies render or decide whether they should.
- `[export] formats = ["obj"]`. Export scale is unverified under mm units, so check that the exported OBJ measures about 300 mm. If it doesn't, flag that the export pipeline needs STL/mm support (a follow-up, not in this session).

## Iterations
- 2026-10-10: pass 1 built.
  - **Geometry.** `Frame` is a parametric ring sweep (`builders/frame_geo.py`): one watertight solid.
  - **Explored.** Edge grid: sag 8/12/15 × soft/sharp tips, plus max envelope with wobble (`out/explore-edge.png`). Depth grid: 25/40/55 × linear/cove/convex (`out/explore-depth.png`).
  - **User picked.** Max 12×15" envelope (304.8 × 381), sharp horn tips (k=0.5), 15 mm bow, 3 mm wobble (seed 3), 40 mm depth, cove face, 10 mm outer edge.
  - **Fit.** Rabbet 255 × 331.2 × 7. The sight opening of 222.25 × 298.45 overlaps the art by 1/8".
  - **Clips.** 8 turn clips (`Clip_01..08`, 16.5 × 9 × 3) sit in 4 mm back pockets two per corner, on M3 countersunk screws with Ø2.6 pilots up to z=10. Each overhangs the backboard by 5.5 mm.
  - **Sectioning.** Seams are marked at mid-sides (`Seam_X/Y` in Work), giving 4 corner pieces of 152.4 × 190.5 × 40 that fit the 256 bed. They are not cut yet.
  - **Compromise.** Within 12×15" the inward bow is capped at about 18 mm (a 6 mm minimum wall outside the rabbet). That is much gentler than the sketch, so the drama comes from the tips, the cove slope and the 33 mm sightwell.
  - **Status.** Check is clean. Export is OBJ+GLB split per object, at mm scale and Y-up.
  - **Tooling fix.** `render_studio.py` now scales the model down into the studio instead of scaling the studio up. Large k broke EEVEE lighting, so mm models rendered black.
- 2026-10-10: render views. Added `blend views` (new repo tooling): `[[views]]` in session.toml → `out/views/<name>.png`, with `upright`, `include` and `zoom`/`target`. Views: hero, front, profile, plan, back, corner, clip.
- 2026-10-10: viewer aids.
  - **Cameras.** `Cam_<view>` objects in `model.blend` (`builders/50_cameras.py`).
  - **Section.** A live section cut (`builders/60_section.py`, red cap faces, plane is movable).
  - **Viewport.** Clip end raised for mm units, and Solid mode shows textures; the art proxy got UVs.
- 2026-10-10: fit to the real art.
  - **Art.** The illustration photo is perspective-cropped to the paper edge, with the white border kept, by `builders/crop_art.py`: edge lines are fitted to the paper and the image is warped to 9×12" at 200 ppi, with the thumb painted out of the border. The result is on `Art_Proxy` as a texture.
  - **Frame.** Shrunk 1" to 11×14" (279.4 × 355.6 × 40).
  - **Stack.** The backboard is cut to the art's 9×12", so it no longer shows. The rabbet is now 229.6 × 305.8 × 9 and holds 2 mm glazing (z 7–9 against the lip), art on a 3 mm board (z 4–7) and the clip zone (z 0–4).
  - **Outer edge.** Raised 10 → 12 mm so it still clears the deeper rabbet.
  - **Unchanged.** Sight opening 222.25 × 298.45 (1/8" over the paper edge) and min wall 8 mm. Corner sections are now 139.7 × 177.8. View, camera and section targets moved to the new clip and corner positions.

- 2026-10-10: closed pass 1 (`/done`).
  - **Check.** Clean: Frame 5129 faces / 10800 tris; 8 clips at 86 faces each. No non-manifold, loose, degenerate or flipped geometry.
  - **Exports.** OBJ + GLB per object: Frame and Clip_01..08, 18 files, mm scale.
  - **Render.** `render.png` is the flat studio still (Model only). The `out/views/hero.png` render, upright with the art in place, is the better showcase.
  - **Open items.**
    - Joinery for the 4 corner sections (seams marked, not cut).
    - Test print of one corner for clip and pilot fit.
    - Glazing/board thickness assumed 2 mm / 3 mm.
    - Optional hollowing to save filament.

## Workflow notes
- **Ring sweep (watertight frame).**
  - Every ring gets the same vertex count (4 sides × N, corners shared), and the rings are bridged cyclically: outline z0 → outline top → face rings → sightwell → lip → rabbet → back.
  - Corresponding samples make the tips run to the opening corners as hip lines for free.
  - One bmesh, no booleans, 0 non-manifold edges.
- **Explore grid.** A non-NN `explore.py` reuses the builder's `build_frame` params, lays variants out in an `Explore` collection with `look` top/3-quarter, and runs `validate()` (min wall) per variant.
- **Clip pockets.** Raycast the frame's top surface at each pocket/pilot to assert skin thickness before cutting. Build the pocket boxes and pilot cylinders as two disjoint cutter meshes (EXACT boolean), then apply.
- **Mirrored-axis bug.** Building local frames from "along the edge" plus "outward" gave left-handed matrices on half the corners. Fix: derive u from outward (u = (v.y, -v.x)) so the frame stays right-handed.
- **mm sessions.** `blend render` used to scale the studio by about 490×, and EEVEE lighting died. It is fixed now (the model is scaled instead). Proxies in Ref don't render; render reads only Model.
- **Joinery candidates (next pass).** Mid-side seams are at the narrowest wall (about 8 mm plus the face). Options: 2× Ø3 alignment-pin holes per seam plus glue, or a printed butterfly key in a back recess across each seam. Consider shifting the seams off-centre (pinwheel) to land in thicker sections.
- **Render views.** For a wall piece, `upright = true` rotates +Z to -Y before framing. `include = ["Ref"]` brings in proxies such as the art and backboard. The zoom crop must be a cube around the target (radius/zoom); per-axis extents cropped the thin depth axis to almost nothing.
- **Photo → art texture.** Paper detection: a warm white needs a loose saturation cutoff (spread < 0.2, min > 0.62); the couch was min about 0.35 and skin had a spread of about 0.3. Scan *inward from the photo edge* for the first long white run. Scanning outward from the art hits white details inside the painting. Fit a line per edge with outlier rejection, intersect the lines, then warp with a homography in numpy.
- **Texture on a kit box.** `mesh.box` has no UVs. Generated coordinates map the box bounds to 0..1, so the top face shows the whole image the right way up.

## Lessons
- **Parametric first, experiments second.** One `build_frame(params)` plus a variant grid answered "try depths/curves" in two `look`s. Every later change (11×14 shrink, deeper rabbet, glazing) was a param edit and a rebuild, with asserts catching wall and skin violations.
- **Encode constraints as asserts in the builder.** Min wall outside the rabbet, envelope ≤ brief, pocket break-out and pilot skin (by raycast) all live in the builder. The 16 mm sag variant was rejected automatically instead of being discovered in a render.
- **Run the brief's constraints numerically before showing variants.** The 12×15 envelope against a 10×13 backboard capped the bow at about 18 mm. Say that up front: the sketch's drama can't fit, so it shifts to the tips, slope and depth.
- **mm units break things built for metres.** Studio render lighting (scaling lights by about 490×), the viewport clip end (1000 BU = 1 m) and camera clip ranges all broke. Test the tooling on an mm session, or scale clip settings at setup (now done in `setup_scene.py`).
- **Cameras must not have the real model between them and a section copy.** The first section camera looked through the original frame. Offset the section copy toward the camera side.
- **Local frames from two edge vectors can be left-handed.** Derive the second axis from the first (u = (v.y, -v.x)), or half the corners mirror and normals flip.
- **Photo detection.** Scan inward from the photo border; art contains white too. Loosen the colour thresholds for warm paper, and check the couch and skin pixel values first (cheap to print).
- **Solid-mode textures need UVs.** Generated coords only work in Material Preview and renders. Add planar UVs to any image proxy.
- **Wasted time.** Writing `render.png` as the only showcase. A flat, art-less studio still undersells a wall piece, and `blend views` with `upright` + `include` should come earlier.
