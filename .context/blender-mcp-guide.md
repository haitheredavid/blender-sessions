# Blender MCP Guide

How a session works with the live Blender instance through blender-mcp. Read this before any `mcp__blender__*` call. The user may be working in the same Blender at the same time; treat it as a shared workspace, not a sandbox.

## Setup (once)

- `.mcp.json` runs `uvx blender-mcp`. The add-on must be installed in Blender: `just addon`, then restart Blender.
- If `get_addon_status` reports `up_to_date: false`, tell the user to run `just addon`. Do not install it yourself mid-session.

## Connect

1. `just open <model>` opens `models/<m>/model.blend`. The add-on bridge auto-starts on port **9876**.
2. Only one Blender can own the port. If another instance is open, the agent models into the wrong file. Ask the user to close it.
3. Call `get_addon_status`, then `get_scene_info`.
4. Assert the file before any write. Every write step begins with:
   ```python
   assert bpy.data.filepath.endswith("models/<m>/model.blend"), bpy.data.filepath
   ```
5. Note the Blender version from `get_addon_status`. APIs differ (GPv3 from 4.3, GN socket API from 4.0).

## Step size

- One step = one part, one node group change, or one modifier-input change. Never a whole model in one call.
- Write idempotent code: look objects and node groups up by name and create them only if missing. A re-run must not duplicate.
- End each step with a small summary dict (names, counts, key dims) as the last expression or a `print`. Do not dump whole meshes or node trees.
- Avoid `bpy.ops` that need a UI context. Prefer data API calls. When an operator is unavoidable, use `bpy.context.temp_override(...)`.
- Find shader and GN nodes **by type**, never by name; names are localized. Read enum identifiers from `bl_rna` instead of hardcoding them. Set `render.engine` inside `try/except TypeError`.
- Material colour goes on shader node inputs. `diffuse_color` is viewport-only.
- GN modifier inputs: use `kit.gn.set_input`/`get_input` by socket name. Blender 5 stores them in `mod.properties.inputs.<id>.value`, so `mod["Socket_N"]` raises.

## Look budget

- One `look` per meaningful step, not per line of code.
- `max_size` ~512 for routine checks; go larger only for a detail review the user asked for.
- Prefer `look(mode="angles", views=[...])` with 1-2 views. For comparisons, build a variant grid and look once.
- For thin or flat models (frames, panels) use a low 3/4 view to read depth; top views only show outline.

## Co-editing protocol

- At the start of every user prompt, re-read the state (`get_scene_info`, or a targeted query). The user may have moved, edited or deleted things since the last step.
- **Control** objects belong to the user. Read them freely; change them only when the prompt asks, and say what changed.
- Modifier inputs are shared knobs. If an input differs from `params.toml`, ask whether the hand value should become the new param before overwriting it.
- Never apply modifiers, join objects or convert to mesh without saying so. That breaks the live parametric chain (see `modeling-guide.md`). If it is needed, log it as a step named `detach-<obj>`.
- Never delete objects you did not create in this session without asking.

## State hygiene

- Python globals persist between `execute_blender_code` calls. `build_all.py` reloads `kit`; reload any other ad-hoc import yourself (`importlib.reload`).
- Undo over MCP is unreliable. Make changes reversible with params, or `/checkpoint` before a risky step.
- Save (`bpy.ops.wm.save_mainfile()`) before any `just` / `blend` command. Headless scripts read the file from disk.
- Units: in an mm model 1 BU = 1 mm. Check `scene.unit_settings` before writing literal sizes.

## Logging steps

- After each `execute_blender_code` that **changes the model**, write the code to a scratch file and run:
  `uv run blend step <m> <slug> --intent "<why, one line>" --code-file <file>`.
- Do not log read-only queries, looks, or failed attempts that were fully reverted.
- `/checkpoint` adds a Speckle version id to the latest step (`speckle-guide.md`).

## Failure recovery

- **Bridge not responding:** ask the user whether Blender is open and responsive. Do not relaunch Blender while the user may have unsaved work.
- **Wrong file open:** stop writing. Ask the user to save it and run `just open <m>`.
- **Crash or lost work:** reopen, rebuild with `build_all.py`, then replay `log/` steps after the last promoted one.
- **Step raised mid-way:** re-query the state before retrying. A partial step may have created objects.

## Safety

- Never quit Blender, never `save_as` over another model's file, never `read_factory_settings`.
- `generate_3d` may cost the user a credit. Ask first.
- Imported or generated assets arrive at arbitrary scale. Size them from `world_bounding_box` and place them on z=0.
- Speckle credentials stay inside the connector. Never read or print them.
