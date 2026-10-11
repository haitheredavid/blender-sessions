# Dimensions and annotation

Live dimension lines (GN) between Control anchors, in the Notes collection. They're shown only in `[[views]]` shots that include Notes. Use them for spec sheets, fit checks and print hand-offs.

## When to use
- To show measured sizes (outer envelope, opening, rabbet) on a render.
- To check a dimension while editing: the label re-measures live.

## Steps
1. `kit.annotate.dim("Outer_W", a, b, suffix=" mm")`:
   - a and b are objects, or points that become `CTL_DIM_<name>_A/_B` empties;
   - offset, text size and thickness default to fractions of the length;
   - `normal` sets the plane (default +Z: a top-view dimension).
2. Snap or parent the anchor empties to model features, so the dimension follows edits.
3. Add a view:
   ```toml
   [[views]]
   name = "dims"
   azimuth = -90
   elevation = 60
   include = ["Notes"]
   ```
   Then run `just views <m>`.
4. Tune one dimension through its `GN_Dimension` modifier inputs: Offset, Text Size, Decimals, Suffix.

## Gotchas
- **New objects have a stale `matrix_world`** until the depsgraph updates. Measure from `.location`, or call `view_layer.update()` first.
- **Labels align with the line's direction.** A line drawn right-to-left reads upside down, so swap a/b.
- **Notes is hidden from check, export and render.** Only `views` with `include = ["Notes"]` show it.

## Models
