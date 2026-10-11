# 2026-10-10 gn-rebuild

## Goal
Rebuild the frame on GN patterns driven by Control curves, with depth/taper/curve variants

## Steps
<!-- `blend history witch-frame` has the full step log; summarise the arc here. -->
- 1: first Speckle checkpoint of the migrated bmesh frame (version 23b410c176).
- 2: Frame rebuilt on the new `frame_loft` pattern: Control `CTL_Outline` (4-pt Bezier), bow/depth/face as GN inputs from params.toml; clip pockets now live booleans (nothing baked). Check clean; 6 variants rendered to out/variants.png.
- 3: base set to the first session's pick (centre of the depth grid, 40 mm cove, plus sharp tips / 15 mm bow / 3 mm wobble seed 3). Wobble ported to GN (`Wobble`, `Seed` inputs). Render + gallery refreshed; Speckle version b8a0881e09 (published headless).

## Outcome
- Frame is fully parametric and hand-editable, matching the first session's pick. The GN wobble has the same character as the bmesh one but not the identical squiggle (different RNG).

## Next
- Joinery for the 4 corner sections (pins or butterfly keys at the mid-side seams).
