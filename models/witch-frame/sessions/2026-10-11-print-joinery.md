# 2026-10-11 print-joinery

## Goal
Print the tenon joinery: lay tenons flat for export, gable mortise roof (re-fit), 0.4 back chamfer on seam faces, TENON_CLEAR coupon (0.10/0.15/0.20); then print-pack

## Steps
<!-- `blend history witch-frame` has the full step log; summarise the arc here. -->
- 9: mortises and tenons now share a 45 deg gable roof (true offset: apex + 0.15 * sqrt 2), so the mortise roof prints without bridging. `fit()` samples the whole gable outline against WALL. Widths are unchanged (N 4.2, S 6.0, E 3.4, W 3.8); the total heights grew to 10.1 / 11.0 / 9.9 / 9.9 because the cove left room above the old flat roof. Each seam face gets a 0.4 mm 45 deg back chamfer (one wedge per rail, 0.1 land so no cutter vertex sits on the seam plane). Probed: chamfer z = 0.35 to 0 over 0.4 mm on TR and BR. Tenon-to-mortise gap is 0.15-0.5.
- 10: the tenon helpers (constants, `gable`, `prism`, `seam_wedge`) moved to `builders/joinery.py`. New `45_coupon.py` builds 3 E-seam coupons (the thinnest tenon) in a Coupon collection at +X. Each has two 20.5 mm offcuts trimmed at z 16.4 and a Tenon_E copy, at clearances 0.10 / 0.15 / 0.20, marked with 1 / 2 / 3 top notches. The tenons store `fit` and `seam` props for the coupon.
- Print pack: `[print] flat = [...]` makes `print_pack.py --flat` lay matching parts on their largest face (tenons now lie on a side face). `blend print-pack --collection Coupon` packs into `print/coupon/`; a `[print.Coupon]` table overrides orientation, flat and assembly. There is a new test for the per-collection options.

## Outcome
- `check --strict` is clean for Print and Coupon. Frame pack: 16 parts, 361.7 cm³, 4 plates; tenons are 32 x 9.6-10.7 x 3.4-6.0 lying flat. Coupon pack: 9 parts, 17.6 cm³, 1 plate (`print/coupon/`). `just ci` is green.
- The assembly notes now say the tenon's gable edge goes up and to print the coupon first.
- Wrap: the builders already were the source, so no steps needed promoting. `build_all` rebuilt cleanly and Control is unchanged. `check` is clean. Exports: 16 parts x stl/obj/glb. render.png and views were re-rendered (Model is unchanged; the joinery lives in Print). The isometric assembly animation was re-rendered with the gable tenons. Workflows touched: print-fit-and-sectioning (gable roof, seam chamfer, coupon, bridge-sag gotcha) and print-handoff (`flat`, `--collection`).
- Open: TENON_CLEAR is still 0.15 until the coupon is printed. The coupon only tests E (gable 3.4); the S tenon (6.0) bridges and shrinks differently, but it uses the same clearance.

## Next
- Print `print/coupon/`, pick the clearance (1/2/3 notches = 0.10/0.15/0.20), set `joinery.TENON_CLEAR`, `build_all`, then `blend print-pack witch-frame` and print the frame (4 plates).
