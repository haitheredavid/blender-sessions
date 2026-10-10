# Restructure: long-lived models, light sessions, editable parametric forms, Speckle history

## Progress
- [x] Phase 0: context (AGENTS.md, CLAUDE.md shim, `.context/` guides)
- [x] Phase 1: structure + witch frame migrated to `models/wispy-witch-frame`, refs → `refs/`
- [ ] Phase 2: parametric
- [ ] Phase 3: Speckle (connector spike first)
- [ ] Phase 4: expansions
- [ ] Phase 5: witch frame review; delete this doc

## Notes since planning
- `workflows/variant-grid-exploration.md` already covers the explore-grid technique (witch frame). Phase 2 variants build on it and don't replace it.
- The witch frame lives at `sessions/2026-10-10-wispy-witch-frame/` with a session-level `status = "done"`. Phase 1 migrates it to `models/wispy-witch-frame/` (git mv). Its builders are bmesh-based; Phase 5 reworks them onto GN.
- Guides in `.context/` describe the target conventions. Code catches up phase by phase.

## Context
The first blender-mcp work went well for setup, sketching, print-aware detailing and export. Iteration is where it fell down:
- **History was lost.** Builders capture only the final "one go" procedure, not the prompt-by-prompt layers.
- **The output couldn't be taken over.** A hand edit in Blender broke the computed procedures, so the user couldn't work alongside the agent.
- **Sessions were heavy.** "One session = one model" forces a big context. The user wants short sessions that iterate on one model across many sittings.
- **No external version history.** The user wants Speckle (free server, personal account) as the versioned record.
- **Narrow feature range.** The user wants to add parametric modeling, grease pencil, animation and dimension annotations.

Decisions made: **Geometry Nodes core**, **explicit Speckle checkpoints** (plus one on session close), and **`models/<name>/` with sessions inside**. This repo stays a general modeling and render environment; print pipelines such as bambi build on top of it. Witch frame gets reviewed after the restructure.

## Target layout
```
models/<name>/
  model.toml        # intent, status, units, tags, workflows, [speckle] ids, export/render/views/turntable
  params.toml       # [base] params + [variants.<v>] overrides → GN modifier inputs
  model.blend       # live source (LFS)
  builders/         # NN_<part>.py: build node groups + modifier stacks, never bake
  log/              # steps.jsonl + NNN-<slug>.py: every iteration step's code, verbatim
  sessions/         # YYYY-MM-DD-<slug>.md: short per-sitting notes (goal, steps, outcome, next)
  exports/  render.png  out/ (gitignored)
models/_template/
lib/kit/            # + gn.py, params.py, control.py, annotate.py, gp.py, anim.py
lib/patterns/       # reusable GN pattern builders (one module each)
assets/patterns.blend  # pattern node groups marked as assets (Asset Browser)
workflows/          # docs; one per pattern / feature
```

## Agent context (`.context/`, following the ctx guides-vs-active model from ~/suffolk/ctx)
- **`AGENTS.md`** becomes the canonical, compact operational guide: what the repo is, repo shape, commands, standards, safety and where to edit. **`CLAUDE.md`** shrinks to a shim (`@AGENTS.md` plus Claude-specific skill pointers). Today's CLAUDE.md content gets split between AGENTS.md and the guides below.
- **`.context/README.md`**: the guides-vs-active conventions, copied from ctx and adapted. Guides never carry progress. Model progress lives in `models/<m>/sessions/` + `log/`, and repo-level in-flight design lives in `active/`.
- **Guides** (durable, the "how to operate" layer):
  - `project-context.md`: purpose (general modeling/render env that print pipelines like bambi build on), architecture (host CLI ↔ headless scripts ↔ live Blender via MCP ↔ Speckle), ownership table, durable decisions (GN core, Control ownership, explicit checkpoints, models/ + sessions).
  - `blender-mcp-guide.md`: **how a session works with the live Blender instance**. It covers:
    - **Connect**: `just open`, the port 9876 single-owner rule, `get_addon_status`/`get_scene_info`, and asserting `bpy.data.filepath` before any write.
    - **Step size**: one part or one modifier change per `execute_blender_code`, idempotent code (look up by name, then create if missing), never `bpy.ops` that depend on UI context without an override, and wrapping in try/except that returns a summary dict.
    - **Look budget**: `max_size` ~512 routine, larger only for review, and one look per step, not per line.
    - **Co-editing protocol**: the user may be editing the same file. Re-read the state (`get_scene_info`) at the start of each prompt, never touch Control without saying so, and treat modifier inputs as shared knobs.
    - **State hygiene**: Python globals persist, so reload kit; undo is unreliable over MCP, so checkpoint instead; save before any `just`/headless command.
    - **Logging**: when to call `blend step`, and what counts as a step.
    - **Failure recovery**: bridge dropped, wrong file open, crash → reopen and replay the log.
    - **Safety**: never quit Blender, never save-as over another model, ask before `generate_3d` (credits).
  - `modeling-guide.md`: units/Z-up/z=0, the collections ownership contract, GN conventions (socket naming, exposing inputs, node-by-type), params/variants, and naming.
  - `engineering-guide.md`: `just`/`blend` commands, the `blender_scripts` rules (bpy-only, `--result` JSON), `lib/kit` growth rules, Python style, tests, LFS, search scope (exclude `.venv`, `out/`, `*.blend`).
  - `speckle-guide.md`: installing the Speckle Blender connector and logging in (credentials stay in the connector, never read or echo them), project/model mapping per variant, what a checkpoint publishes (Apply Modifiers on), the MCP call path chosen in the Phase 3 spike, and loading old versions into Ref.
  - `writing-workflows.md`: how to distill a technique into `workflows/` (the analogue of writing-tdds). `workflows/` stays the technique library; `.context/` is about operating.
- **`active/`**: dated in-flight repo design docs (`YYYYMMDD-<title>.md`), deleted by the PR that lands them. This restructure plan lands there first as `active/20261010-restructure.md`, and the last phase deletes it.
- Skills (`/model`, `/session`, `/checkpoint`, `/wrap`) point at the guides instead of restating them, so each stays short and the session context stays light. `/session` loads `blender-mcp-guide.md` + `modeling-guide.md` only.

## Collections: ownership contract (fixes "my edits break it")
- **Control** is user-owned: curves, profiles, empties, GP sketches, dimension anchors. `build_all` **never clears it**. Builders create a control object only when it's missing (`kit.control.ensure(name, factory)`).
- **Model** holds procedural results. Each object has a GN modifier that reads Control objects and exposes params as modifier inputs. It's rebuilt freely.
- **Work / Ref** stay as they are now. A new **Notes** collection holds dimension annotations and GP callouts, and is rendered only in `views`.
- Rule (CLAUDE.md + workflow doc): tweak a modifier input or reshape a Control curve, and everything stays live. Applying a modifier is the explicit "detach" and gets logged as a step.

## Iteration capture (step log)
- Each meaningful MCP change is one **step**. The host-side command `blend step <model> <slug> --intent "..." --code-file <tmp>` writes `log/NNN-<slug>.py` and appends to `log/steps.jsonl`: `{n, ts, session, intent, params_diff, objects, look?, speckle_version?}`. It runs host-side so it's testable and needs no Blender state.
- `/session` tells the agent to log a step after each `execute_blender_code` that changes the model. Exploratory reads aren't logged.
- Builders = distilled rebuild; log = raw layered history. `/wrap` promotes stable steps into builders.
- `blend history <model> [--last N]` prints the step timeline across sessions. `/session` reads it to stay light.

## Skills (light sessions)
- **`/model <idea>`** (replaces `/make`): plan in plan mode, then `blend model new <name>`, then hand off to `/session`.
- **`/session <model> [goal]`** (new): reads only `model.toml`, `params.toml`, the last session note and `history --last 10`. Opens Blender, creates `sessions/<date>-<slug>.md`, and runs the modeling loop with step logging.
- **`/checkpoint [msg]`** (new): save, `blend check`, publish via the Speckle Blender connector over MCP (`kit.speckle`), and record the version id on the latest step.
- **`/wrap`** (replaces `/done`): session note (outcome + next), promote steps → builders, distill workflows, checkpoint, offer a commit. `blend model done` sets model `status`.

## Parametric core (Geometry Nodes)
- `lib/kit/gn.py`:
  - `group(name)` and `socket(group, name, type, default, min, max)` to define inputs.
  - `link` and a by-type node lookup.
  - `modifier(obj, group, **inputs)` attaches a group with its inputs.
  - `get_input`/`set_input` by socket **name**, resolving the identifier and never hardcoding `Socket_2`.
- `lib/kit/params.py`: loads `params.toml`, merges variant overrides, and `apply(obj, variant)` sets the inputs. It includes a unit helper (in → model units) for inch specs like the frame.
- `lib/patterns/`: each pattern is a GN group builder plus a `workflows/<pattern>.md`. First set:
  - `profile_sweep`: a profile curve swept along a path curve. Covers frames, mouldings, rims.
  - `outline_extrude`: closed curve → filled, extruded solid with bevel and taper.
  - `shell_offset`: wall thickness plus a stepped inner rabbet/groove.
  - Later: `revolve` and `section_split` (planes → printable pieces with joint stubs, refined in the frame review).
- `blender_scripts/build_patterns.py` + `blend patterns-lib` write `assets/patterns.blend` with the groups marked as assets, so the user can drag them in by hand.

## Variants
- `[variants.<v>]` in params.toml. Each variant gets its own scene, a linked copy of the base scene that shares Control, with per-variant modifier input overrides applied by `kit.params`.
- `blend variants <model>` renders every variant with the same view and composites a labelled grid into `out/variants.png` (Pillow, already a dependency).

## Speckle (explicit checkpoints, through the Speckle Blender connector)
- **The primary path is the Speckle Blender connector (v3, next-gen) installed in the user's Blender.** It owns the account login (stored locally by the connector, so no token in the repo or `.env`), publish, load and the version browser. The user can publish or load by hand from the Speckle panel at any time.
- **Checkpoints are driven through MCP against the connector.** Phase 3 starts with a spike:
  1. Over MCP, introspect the installed add-on: `addon_utils` module name, `dir(bpy.ops.speckle)` or equivalent, operator RNA props, and the connector's Python modules (account/client and publish functions).
  2. Choose a call path, in order of preference:
     - **(a) Operator.** Use the connector's publish operator with an override and params (project, model, selection, Apply Modifiers on so the GN results bake into the published geometry).
     - **(b) Connector internals.** If the operator is modal or UI-bound, call the connector's own Python publish functions and its stored account (`get_default_account`, its converter, `operations.send` + `version.create`), all inside Blender.
     - Record the outcome in `.context/speckle-guide.md`.
- `lib/kit/speckle.py` (Blender-side, used over MCP) wraps whichever path wins:
  - `publish(objects, project_id, model_id, message, props)`. It attaches `params`, `variant`, `step`, `session` and the git sha as custom props or version message, and returns the version id.
  - `load(project_id, model_id, version=None)` to pull an older version into Ref for side-by-side comparison.
- `/checkpoint` = save → `blend check` → `kit.speckle.publish(...)` via MCP → `blend step --speckle-version <id>` records it in the log. It applies to the active variant, with one Speckle model per variant (`<name>`, `<name>/<variant>`).
- Project and model ids live in `model.toml [speckle]`. `/model` sets them up by creating the project and model through the connector (or asks the user to pick in the Speckle panel and pastes the ids back).
- **Headless fallback (optional, only if needed):** `blend push` runs `blender -b` with the connector add-on enabled to publish without the UI open. No separate host-side specklepy unless the spike shows the connector can't run headless.

## Feature expansions (kit module + workflow doc each)
- **Grease pencil** (`kit/gp.py`): a sketch layer in Control. `to_curve` turns a sketch into a profile or path that feeds the patterns; annotation strokes go in Notes. GPv3 API (Blender 4.3+); check the version from `get_addon_status`.
- **Dimensions** (`kit/annotate.py`): `dim(a, b, offset, label=None)` builds a GN dimension line (line, ticks and string-to-curves label) driven by Control empties, so it updates live. `[[views]] include = ["Notes"]` gives annotated orthographic shots.
- **Animation** (`kit/anim.py`): keyframe GN inputs (param sweeps), exploded section views and camera paths. `blend animate <model> --action <name>` renders an mp4/gif, reusing the turntable encoding path in `cli.py`.

## Code changes
- Rename `src/blend/session.py` → `src/blend/model.py`. The `Model` dataclass keeps `views()`, `export_formats()`, `set_field()`, `resolve()`, `latest()` and `slugify()`, and adds `params()`, `variants()`, `log_dir`, `sessions_dir` and `speckle` ids. In `config.py`, `sessions_dir` becomes `models_dir`.
- `src/blend/cli.py`:
  - Session args become model args.
  - Add `model new|ls|done`, `session new`, `step [--speckle-version]`, `history`, `variants`, `patterns-lib` and `animate` (plus `push` only if the headless fallback is needed).
  - check/export/render/views/turntable/gallery keep working against Model.
- `models/_template/builders/build_all.py`:
  - Clears Model + Work only and ensures Control/Notes exist.
  - Applies `params.toml [base]`.
  - `parents[2]/lib` still resolves.
- `lib/kit/scene.py` adds `control()` and `notes()`. `blender_scripts/setup_scene.py` creates them.
- `blender_scripts/export.py` adds `stl` (and `3mf` when the exporter exists) to `EXPORT_FORMATS`.
- Also update `justfile`, `CLAUDE.md`, `README.md`, `.gitignore` (`models/*/out/`) and `workflows/mcp-modeling-loop.md`. Rewrite the skills: `make`→`model` and `done`→`wrap`, and add `session` and `checkpoint`.
- Tests (pytest, existing `tests/`) cover:
  - Model params/variants parsing and `set_field`.
  - The step log writer and history.
  - Recording `--speckle-version` on a step.
  - The variant grid compositor.

## Phases (each one commit)
0. **Context**: AGENTS.md + CLAUDE.md shim, `.context/` README + guides (blender-mcp-guide first), and this plan as `active/20261010-restructure.md`. Docs only; it sets the rules the later phases follow.
1. **Structure**: models/ layout, Model class, CLI renames, Control/Notes, template, `/model` `/session` `/wrap`, step log + history, docs.
2. **Parametric**: gn/params/control kit, first 3 patterns, patterns asset lib, variants + grid, workflow docs.
3. **Speckle**: install connector + login (user), introspection spike, `kit/speckle.py` publish/load, `/checkpoint`, speckle-guide.
4. **Expansions**: GP, dimensions, animation, stl/3mf, workflow docs.
5. **Witch frame review**: bring the in-progress frame in as `models/witch-frame/`, built on profile_sweep + shell_offset (rabbet), with depth/taper/curve variants.

## Verification
- `just ci` green after each phase, including the new tests.
- Phase 1: run `blend model new demo` → `just open demo`; MCP `get_scene_info` should list Model/Work/Ref/Control/Notes. Two `blend step` calls appear in `blend history demo`. Hand-move a Control curve and re-run build_all: the edit survives.
- Phase 2: build a profile_sweep frame on a Control rectangle. Change a modifier input by hand and `look` to confirm the form updates live. `blend variants demo` writes the grid.
- Phase 3: `/checkpoint test` on demo → the version shows on app.speckle.systems with the GN result baked and params in its props. The version id lands in `steps.jsonl`. `kit.speckle.load` of the previous version appears in Ref, and the user can also see both versions in the connector panel.
- Phase 4: a GP sketch → curve drives a sweep. `dim()` follows a moved empty. `blend views` renders Notes. `blend animate` writes an mp4.
