# Modeling Guide

Conventions for how a model is built so it stays editable by hand and rebuildable by code.

## Space and units

- Z up. The model rests on z=0.
- 1 BU = 1 m by default. Use `--unit mm` for precise or printable work; `[units]` in `model.toml` records it.
- Model at real-world size. Convert spec units once in params (`kit.params.inch(9)` → model units), never by eye.

## Collections (ownership contract)

| Collection | Owner | Builders | Rendered |
|---|---|---|---|
| **Control** | user | create only if missing (`kit.control.ensure`); never clear | no |
| **Model** | procedure | cleared and rebuilt freely | yes (check/export/render read it) |
| **Work** | procedure | cleared and rebuilt; cutters, helpers, explore grids | no |
| **Notes** | procedure | dimension lines, GP callouts | only in `views` that include it |
| **Ref** | user | never touched | only in `views` that include it |

- Control holds the *inputs* the user shapes by hand: profile and path curves, empties, GP sketches, dimension anchors.
- Model objects are procedural: a GN modifier reads Control objects and exposes params as modifier inputs.
- Reshape a Control curve or change a modifier input, and everything stays live. Applying a modifier is an explicit **detach**: say so and log it.

## Geometry Nodes conventions

- One node group per pattern or part, named `GN_<Pattern>` (library) or `GN_<Model>_<Part>` (model-specific).
- Expose every tunable as a group input with a human name ("Depth", "Rabbet Width"), a default, and min/max. Never leave magic numbers inside the tree.
- Object inputs (e.g. "Profile", "Path") point at Control objects, read in ORIGINAL space: the curve's points drive the shape, and the host object's transform places the result.
- Set and read inputs **by socket name** through `kit.gn.set_input` / `get_input`. Never hardcode `Socket_N` identifiers.
- Input names double as `params.toml` keys. Keep them unique across patterns (prefix like `Pocket Width`), or scope a key: `"Frame/Height"`.
- Look nodes up by `bl_idname`/type, never by display name.
- Group nodes into numbered, labelled stages (`gn.stage`) so the tree reads in the editor. The user reviews the model there.
- Reusable groups live in `lib/patterns/` (see `workflows/gn-patterns.md`).
- Encode constraints as checks: a builder or `validate(p)` asserts min wall, envelope and clearances before showing a result.

## Params and variants

- `params.toml [base]` holds the canonical params; `[variants.<v>]` holds overrides only.
- `kit.params.apply(variant_or_dict, objects=None)` pushes params into the modifier inputs of Model (or given) objects; `build_all.py` applies `[base]` last. Params are the source of truth; a hand-tuned input that should stick goes back into `params.toml`.
- Compare variants live with `kit.params.grid()` or rendered with `blend variants <m>` (`workflows/variant-grid-exploration.md`), then let the user pick.

## Builders

- `builders/NN_<part>.py`, run in order by `build_all.py`. They create node groups, Control defaults (if missing) and Model objects with modifiers.
- Non-NN scripts (`explore.py`, `*_geo.py`) are helpers that `build_all` skips.
- When a helper proves reusable across models, move it to `lib/kit/` or `lib/patterns/`.

## Naming

- Meaningful names (`Frame`, `Clip_01`, `Profile_Outer`), never `Cube.003`.
- Control objects: `CTL_<Name>`. Notes: `DIM_<Name>`, `GP_<Name>`.
