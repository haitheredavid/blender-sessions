# 2026-10-11 ledge-support

## Goal
Frame print: the z 9 rabbet ledge sagged on the coupon (supports off). Carry the bambi support overrides to the frame, or add a 45 deg chamfer under the ledge in the builder

## Steps
<!-- `blend history witch-frame` has the full step log; summarise the arc here. -->
- bambi (`sessions/2026-10-11-witch-frame-coupon`): the first coupon print's flat glazing lip (3.675 mm = OVERLAP + CLEAR, ceiling at z 9 = rabbet) sagged with supports off. Added `[slice.overrides]` (normal(auto) supports, build plate only, 0.2 top gap), resliced, and confirmed in Bambu Studio. The frame pack's pieces each have about 970 mm² of the same ceiling at z 9 (plus about 375 mm² at z 4).
- 12: `45_coupon.py` now builds `COUPONS = (clearance, ledge)` pairs: two 0.10 coupons, `C10_Flat` (lip as the frame has it) and `C10_Chamfer` (a 45° `lip_wedge` unioned into the rabbet corner, so there's no flat ceiling left). Both are manifold; the chamfer adds 0.14 cm³ per offcut. `[print.Coupon]` notes updated, and `print-pack --collection Coupon` rebuilt `print/coupon/` (6 parts, 12.0 cm³).
- bambi round 2: the pack was copied in and sliced with the same overrides: 39 min / 11.4 g. Supports land only under the Flat offcuts.

## Outcome
- **Decision:** both round-2 coupons printed fine; the user picked the flat lip + supports. The frame geometry stays as is; no `lip_wedge` in the frame.
- The coupon pack is ready to print: one plate, Flat vs Chamfer lip at TENON_CLEAR 0.10. The frame (`Print`) is unchanged.
- Open: a full 3.675 mm wedge leaves the 9x12" glazing (2 mm) no flat seat, so the stack would ride down the slope about 3.2 mm. If Chamfer prints better, the frame needs the rabbet deepened by about 3.2 mm or a different seat. Otherwise, the frame's bambi session needs the support overrides.

- Wrap: step 12 already lives in `builders/45_coupon.py`, so nothing needed promoting. `build_all` rebuilt cleanly and Control is unchanged. `check --strict` exits 0 for Print and Coupon. Exports, render.png and the 7 views were re-rendered (Model is unchanged). `[print] orientation` now tells the printing agent to slice with build-plate supports, and the frame pack was repacked (16 parts, 361.9 cm³, 4 plates). Workflow: print-fit-and-sectioning (lip gotcha, step 1 caveat, Models row). No `results.json` yet, so there was no print feedback to walk. `just ci` 46 passed.

## Next
- The frame's full print in bambi: make a `witch-frame` bambi session from `print/` (4 plates) with the same `[slice.overrides]` as the coupon; check that supports appear only under the z 9 lip (and maybe z 4 clip pockets).
