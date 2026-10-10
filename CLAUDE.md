# blender-sessions

A sandbox for modeling in Blender through blender-mcp. Each session builds one model; the techniques that work get distilled into a growing `workflows/` library.

## Layout
- `src/blend/` is the `blend` CLI (typer), host-side Python 3.13.
- `blender_scripts/` runs **inside** Blender (`blender -b file.blend -P script.py -- --result out.json ...`). Use bpy/bmesh only and never import `blend` here. Each script takes `--result` and writes JSON there; `_common.py` holds the shared arg/Model-collection helpers.
- `lib/kit/` holds bpy helpers shared by session builders (`scene`, `mesh`, `materials`). Grow it when a helper proves reusable.
- `workflows/` holds reusable technique docs (`README.md` index, `_template.md`). Read the relevant ones before modeling, and update them at `/done`.
- `assets/studio.blend` is the neutral render studio (cyclorama, three-point light, camera at `blend_azimuth`/`blend_elevation`). `blend render` appends it, scales it to the model and fits the camera. `blend render-scene --overwrite` rebuilds it from `blender_scripts/build_studio.py`.
- `sessions/YYYY-MM-DD-<name>/` is one per model and contains:
  - `model.blend`: the source.
  - `session.toml`: intent, status, workflows, tags, units, export/render/turntable settings.
  - `notes.md`: Intent / Plan / Iterations / Workflow notes / Lessons.
  - `builders/`: code that rebuilds the model.
  - `exports/`: glb/fbx/obj.
  - `render.png`: committed.
  - `out/`: turntables and scratch, gitignored.
- `sessions/refs/` holds third-party reference images (gitignored).
- `docs/gallery/<session>.png` holds the README gallery tiles, rewritten between `<!-- gallery:start/end -->` on every render.

## Conventions
- **Units.** 1 Blender unit = 1 m by default. Use `blend new <name> --unit mm|cm` for small or precise work; `[units]` in `session.toml` records it. Model at real-world size.
- Z is up. The model rests on z=0 (the render centres it there anyway).
- **Collections.**
  - **Model** is the deliverable: it's what check, export and render read.
  - **Work** holds cutters, helpers and blockouts, and is never rendered.
  - **Ref** holds reference images and imported refs.
- Give objects meaningful names (`Body`, `Lid`, `Handle_L`), not `Cube.003`.
- **Builders.** Any model you'd want to rebuild lives in `builders/NN_<part>.py`, run in order by `builders/build_all.py`. That script clears Model and Work, puts `lib/` on sys.path, reloads `kit`, and saves at the end.

## Session lifecycle
- `/make <idea>` (`.claude/skills/make/`) plans in plan mode, then on approval runs `just new`, models via MCP, checks and renders.
- `/done [session]` (`.claude/skills/done/`) checks, exports and renders; writes Iterations and Lessons; distills `workflows/`; runs `just done`; and offers a commit.

## Working live through blender-mcp
The `blender` server is in `.mcp.json` (`uvx blender-mcp`). The add-on must be installed in Blender (`just addon` = `uvx mcp-for-blender install-addon`, then restart Blender). If `get_addon_status` reports `up_to_date: false`, tell the user to run it.
1. `just open <session>` opens `model.blend`, and the add-on's bridge auto-starts on port 9876. Only one Blender can own the port, so close other instances.
2. Call `get_addon_status` and `get_scene_info` first, and confirm `bpy.data.filepath`.
3. Build in small `execute_blender_code` steps and `look` often (small `max_size` keeps context cheap).
4. Find shader nodes **by type**, not name. Read enum identifiers instead of hardcoding them. Material colour goes on shader inputs; `diffuse_color` is viewport-only. Assign `render.engine` in `try/except TypeError`.
5. Imported or generated assets (`search_assets` → `import_asset`, `generate_3d`) come in at arbitrary scale. Size them from `world_bounding_box`. `generate_3d` may cost the user a credit, so ask first.
6. Save with `bpy.ops.wm.save_mainfile()` before any `just` command, since the headless scripts read the file from disk.

## CLI
`just` wraps the common commands; run `just` to list them. The full CLI:
```
blend new <name> [--unit m|cm|mm]    blend ls    blend open <s>    blend latest
blend check <s> [--strict]           blend export <s> [--formats glb,fbx,obj] [--split]
blend render <s> [--framing fit|wide] [--scene]   blend render-scene [--overwrite]
blend turntable <s> [--frames --fps --size]       blend gallery
blend views <s> [--only NAME]       # [[views]] in session.toml -> out/views/
blend done <s>                       blend workflows
```
`just wrap <s>` runs check, export and render in sequence.

## Dev
Run `just ci` (ruff + pytest) and `just fmt`.

Binaries (`*.blend`, `*.png`, `*.glb`, `*.fbx`, `*.obj`, `*.mp4`, `*.gif`, ...) live in Git LFS (`.gitattributes`). Fresh clones need `git lfs install`.
