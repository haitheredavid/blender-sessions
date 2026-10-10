---
name: done
description: Close out a Blender modeling session. Saves, checks, exports and renders the model, records iterations and lessons in notes.md, distills reusable techniques into workflows/, marks the session done, and offers a commit. Use when the user says "done", "wrap it up", "finish the session", or invokes /done [session].
argument-hint: "[session] [--turntable]"
---

# Done: close a modeling session

Session: $ARGUMENTS. If empty, use the session being worked on in this conversation; otherwise run `uv run blend latest`.

## 1. Lock in the model
1. Via MCP, confirm `bpy.data.filepath` is the session's `model.blend`. If `builders/` exists, run `build_all.py` once to confirm the model rebuilds cleanly from code, then `look`.
2. Save with `bpy.ops.wm.save_mainfile()`.

## 2. Outputs
1. Run `just check <s>`. If it fails, fix the issues (or record why they're acceptable, e.g. an intentionally open surface) before continuing.
2. Run `just export <s>`, which uses the formats in `[export]`.
3. Run `just render <s>`, then read `render.png` to confirm it reads well.
4. If `--turntable` was passed or the user asks, run `just turntable <s>`.

## 3. Record
In `notes.md`:
- **Iterations.** Add a dated line: final state, face counts from check, exports written, compromises.
- **Lessons.** List what worked, what wasted time, and what to do differently. Be concrete (e.g. "bevel before boolean → artifacts; apply booleans first"), not "went well".

## 4. Distill workflows
This step is the point of the repo, so don't skip it.
1. Re-read **Workflow notes** and **Lessons**. For each technique that would help a future session:
   - If a `workflows/*.md` covers it, update that doc. Add steps, gotchas, a bpy snippet, and a line under **Sessions**.
   - If it's new and reusable, create `workflows/<kebab-name>.md` from `workflows/_template.md` and add it to the table in `workflows/README.md`.
   - If a builder helper proved generic, move it into `lib/kit/` and point the builder at it.
2. Set `workflows = [...]` in `session.toml` to every doc used or written.
3. Run `just workflows` to confirm none are flagged "no doc".

## 5. Close
1. Run `just done <s>`. This sets `status = "done"` and refreshes the README gallery.
2. Show a summary: the render, exports, check numbers, and the workflows created or updated.
3. Offer a commit along the lines of `feat(sessions): <slug>`, plus `docs(workflows): ...` if workflows changed. Do **not** commit or push without the user's go-ahead.
