# Print handoff (to bambi)

Turn a finished model into a self-contained print pack that a printing agent (bambi: Bambu Studio + P1S) can slice without knowing how the model was built.

## When to use
- The model has a Print collection (parts split for the bed, joinery cut) and checks clean with `blend check <m> --collection Print --strict`.

## Steps
1. Fill `[print]` in `model.toml`: collection, bed (256 for the P1S), printer, material, orientation, hardware, assembly steps.
2. Save the `.blend`, then run `just print-pack <m>`. It writes `models/<m>/print/`:
   - `parts.blend`: only the parts, modifiers baked, 1 BU = 1 mm, each on z=0, no overlaps. bambi exports every visible mesh of its session `.blend`, so this file is what bambi should open as its model.
   - `stl/<part>.stl`: per-part STLs in mm.
   - `manifest.json` and `README.md`: units, bed, material, part sizes, volumes, watertight flags, conservative suggested plates, hardware and assembly.
3. The command exits non-zero if any part isn't watertight or doesn't fit the bed.
4. **Lay parts flat:** `[print] flat = ["Tenon_*"]` (fnmatch globs) rotates the matching parts so their largest planar face (total area per normal) is on the bed. Use it for loose tenons, keys and pins that are modelled in place.
5. **Extra packs:** use `blend print-pack <m> --collection Coupon` for test prints and spares. It writes to `print/coupon/`. A `[print.Coupon]` table replaces orientation, flat, hardware and assembly, and keeps the printer, bed and material.
6. **On the bambi side:**
   - create the session (`bambi new <m>`);
   - replace its `model.blend` with `print/parts.blend` (or import the STLs);
   - set `[slice] arrange = true`, then `bambi build`.
   - Slice one plate per suggested group, or let Bambu nest the parts.

## Gotchas
- **Units:** the pack is always normalised to mm, whatever the source file's units. STL has no units: slicers read the numbers as mm.
- **Viewport clipping in mm files:** Blender's view clip defaults are in BU (0.01-1000), so in mm files the far clip is 1 m. `kit.scene.fit_viewport()` (run by `build_all`) sets 0.1 mm to 10 m.
- **Plate suggestions** pack bounding rectangles, so L-shaped pieces that could nest still get a plate each. Treat them as an upper bound.

## Models
- witch-frame (2026-10-11): the tenons are laid flat via `flat`, plus a separate clearance-coupon pack (9 parts, 1 plate).
- witch-frame (2026-10-10): 4 corner pieces, 4 butterfly keys and 8 turn clips, 363.7 cm³, 4 suggested plates.
