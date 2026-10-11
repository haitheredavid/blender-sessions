# 2026-10-10 key-tolerances

## Goal
Print-ready butterfly joinery: true-offset clearances, filleted key/recess forms, lead-in chamfers, clean booleans

## Steps
<!-- `blend history witch-frame` has the full step log; summarise the arc here. -->
- Audit of step 4: clearance was a `grow` on half-widths, not a perpendicular offset (the angled flanks got less than 0.15); every corner was sharp (FDM rounds inside corners, so keys bind at the tips); there was no elephant's-foot or lead-in relief.
- 5: `40_sections.py` keys and recesses now come from one bow-tie profile: fillets (tips R0.8, waist R1.5), true polygon offset for the recess (tips R0.95, waist R1.35), lofted from rings. Recess: 0.4 mouth flare, straight walls, floor at 5. Key: 0.4 chamfer on its bed face, 0.3 lead chamfer on top, 0.2 short of flush. Measured gap 0.149-0.150 mm all round.
- 6: the waist fillet's middle vertex sat exactly on the x=0 seam plane, which left 2 degenerate boolean faces (TL, BL). Odd `ARC_SEGS` (5) clears them.
- Measured the butterfly walls: E/W only 1.07 mm on the rabbet side (0.72 at the mouth flare), a free-standing 5 mm fin. The back strip at the mid-sides (7.8-10.8 mm) can't host a recess with real walls.
- 7: switched to glued loose tenons inside the seam faces. `fit()` slices the frame profile at 5 stations along each tenon and grows the largest mortise with >= 2 mm walls (WALL): N 4.2 x 8.2, S 6.0 x 8.4, E 3.4 x 8.3, W 3.8 x 8.2, 32 long, 0.15 clearance, 0.5 end gap, 0.4 chamfer on every edge. Measured walls 2.01-2.05. The cove face drops too low for anything above the rabbet, so every tenon sits in the back strip at z 2.2-10.6. TENON_MIN went down to 3.0 for the E strip. `70_assembly` closes the pieces along x, then y (252 frames). The print notes in model.toml are updated.
- 8: in the assembly animation each tenon slides lengthwise into one piece (N/W into TL, S into BL, E into TR) and rides with it while the frame closes.
- Gotcha: the window scene was Assembly (from the animation). Builders and `blend check` read the active scene, so the file is saved with Scene active again.

## Outcome
- Print: 4 pieces 139.7 x 177.8 x 40, 4 tenons (above), 8 clips. The back face is clean (no key recesses). `check --collection Print --strict` is clean: watertight, 0 degenerate faces. The Assembly scene was rebuilt on the tenons.
- Tunables at the top of `40_sections.py`: TENON_LEN, TENON_W, TENON_MIN, TENON_CLEAR, TENON_END, TENON_CHAMFER, WALL.
- The butterfly keys (steps 5-6) are superseded. Their filleted-offset profile code is in log/005.
- Wrap: `build_all` rebuilt cleanly and Control is unchanged. `check` is clean (Model and Print). Exports: 16 parts x stl/obj/glb; the stale Key_* exports are removed. render.png, views, turntable, isometric assembly animation and print pack were re-rendered. Speckle version 90e438930b on step 8. workflows/print-fit-and-sectioning.md now covers the loose tenon fit and 4 new gotchas.
- Model marked done at the user's request (`--done`); the print-joinery follow-up below is still open.

## Next
- Test-print a seam coupon (two offcuts + tenon) to tune TENON_CLEAR (0.10 / 0.15 / 0.20).
- Print joinery session: lay the tenons flat for export, gable mortise roof (re-fit), 0.4 back chamfer on the seam faces, clearance coupon; then print-pack again.
