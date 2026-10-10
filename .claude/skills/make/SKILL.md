---
name: make
description: Start a new Blender modeling session. Plans the model first (intent, references, scale, technique per part, which workflows apply), then on approval creates the session, builds it live in Blender via blender-mcp, and checks and renders it. Use when the user says "make a <thing>", "model a <thing>", "new session", or invokes /make <idea>.
argument-hint: <what to model>
---

# Make: new modeling session

The user wants to model something: $ARGUMENTS

Work in two stages: **plan** (no files touched), then **build** once the plan is approved. One session = one model.

## Stage 1: Plan

1. Call `EnterPlanMode` straight away.
2. Look for prior art:
   - Run `just ls` and `just workflows`.
   - Read `notes.md` (especially **Lessons**) for any sessions with a similar name or tags.
   - Read every `workflows/*.md` that might apply. Reuse techniques, dimensions and fixes rather than rediscovering them.
3. Fill in what's missing with **one** `AskUserQuestion` round. Only ask what the request leaves open and what changes the build:
   - **Purpose / target.** Still render, game asset (poly budget, engine), animation, 3D print, or kit-bash part?
   - **Style and detail.** Realistic or stylized, hard-surface or organic, low or high poly, level of bevels and greebles.
   - **Scale and units.** The real-world size. The default unit is metres; use `--unit mm` for small precise parts.
   - **References.** Images in `sessions/refs/<slug>/`, a description, or an asset to start from (`search_assets` / `generate_3d`).
   - **Export.** Formats needed (glb, fbx, obj) and whether one file or one per object.
4. Write the plan with these sections:
   - **Session name.** A short kebab-case slug; the folder becomes `sessions/YYYY-MM-DD-<slug>/`.
   - **Intent.** One or two sentences for `session.toml` `intent`.
   - **References.** What drives proportions and look.
   - **Parts.** Each named object with its key dimensions, the technique for it (primitives + modifiers, bmesh loft, booleans, curves, sculpt-free subdivision, etc.) and the `workflows/*.md` it follows. Name the builder files (`builders/10_<part>.py`, ...).
   - **Materials.** Simple Principled setups per part, if any.
   - **Workflows.** Which existing docs apply, and which new technique this session is likely to produce (a candidate for `/done`).
   - **Verification.** Expected result of `just check`, plus render framing.
5. Call `ExitPlanMode`.

## Stage 2: Build (after approval)

1. Run `just new <slug>` (add `--unit mm` or `--unit cm` if planned). This creates the session and opens `model.blend` with Model / Work / Ref collections. The MCP bridge starts on its own; wait a few seconds for port 9876.
2. Fill in `session.toml` (`intent`, `tags`, `workflows`, `[export]`). Copy the plan into `notes.md` under **Intent** and **Plan**.
3. Model through the `mcp__blender__*` tools, following `workflows/mcp-modeling-loop.md`:
   - Call `get_addon_status`, then `get_scene_info`. Confirm `bpy.data.filepath` is this session's `model.blend`.
   - Build in small `execute_blender_code` steps:
     - Deliverables go in **Model**; cutters and helpers in **Work**; refs in **Ref**.
     - Use `lib/kit` helpers (`from kit import scene, mesh, materials` once `build_all.py` has put lib/ on sys.path).
     - Find shader nodes by type, never by name. Never hardcode enum identifiers.
   - `look` after each meaningful step (small `max_size` for routine checks).
   - Persist working code in `builders/NN_<part>.py`, and confirm a clean rebuild with `build_all.py` before finishing.
   - Save with `bpy.ops.wm.save_mainfile()` before any `just` command, which reads the file from disk.
4. Run `just check <slug>`. Fix flagged loose geometry, degenerate faces or flipped normals in Blender (and in the builder), then run it again.
5. Run `just render <slug>`. Read `render.png` to judge it, and adjust framing in `[render]` if needed.
6. Add a dated line under **Iterations** in `notes.md`, covering what was built and any compromises. Jot technique notes under **Workflow notes** as you go; `/done` distills them.
7. Report back with the render, dimensions, check results, and what's left. Suggest `/done` when the model is finished.
