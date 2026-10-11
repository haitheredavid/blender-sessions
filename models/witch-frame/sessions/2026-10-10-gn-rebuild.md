# 2026-10-10 gn-rebuild

## Goal
Rebuild the frame on GN patterns driven by Control curves, with depth/taper/curve variants

## Steps
<!-- `blend history witch-frame` has the full step log; summarise the arc here. -->
- 1: first Speckle checkpoint of the migrated bmesh frame (version 23b410c176).
- 2: Frame rebuilt on the new `frame_loft` pattern: Control `CTL_Outline` (4-pt Bezier), bow/depth/face as GN inputs from params.toml; clip pockets now live booleans (nothing baked). Check clean; 6 variants rendered to out/variants.png.

## Outcome
- Frame is fully parametric and hand-editable. Lost vs the bmesh build: the 3 mm hand-drawn `wobble` (no GN equivalent yet; can be drawn into CTL_Outline by hand or added as a noise input).

## Next
- User picks a variant from out/variants.png → update params.toml [base], checkpoint.
- Joinery for the 4 corner sections (pins or butterfly keys at the mid-side seams).
