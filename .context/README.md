# .context Conventions

This folder holds agent-facing context. It contains two kinds of files with different lifecycles. Do not mix them.

## Guides (this folder's root)

Durable reference for operating in the repo: tooling, the live-Blender protocol, modeling conventions, and repo workflows.

- Guides never describe progress. No roadmaps, feature status, "current state" snapshots, or deferred-work lists.
- Durable decisions (the "why" behind a choice) live in `project-context.md`.
- Modeling *techniques* live in `workflows/`, not here. Guides say how to operate; workflows say how to build a kind of form.

Current guides:

- `project-context.md` - purpose, architecture, ownership, durable decisions.
- `blender-mcp-guide.md` - how a session works with the live Blender instance over MCP.
- `modeling-guide.md` - units, collections ownership contract, Geometry Nodes and params conventions, naming.
- `engineering-guide.md` - commands, `blender_scripts`/`lib` rules, Python style, tests, LFS, search scope.
- `speckle-guide.md` - Speckle Blender connector setup, checkpoints, version mapping.
- `writing-workflows.md` - how to distill a technique into `workflows/`.

## Progress lives elsewhere

- **Per model:** `models/<m>/sessions/*.md` (per-sitting notes) and `models/<m>/log/` (every iteration step). Speckle versions are the geometry history.
- **Repo-level design:** `active/`.

## Active docs (`active/`)

Ephemeral design docs: plans, migration notes, findings.

- File name format: `YYYYMMDD-<doc-title>.md`, dated the day it was created.
- An active doc lives only as long as its implementation. The commit or PR that completes the work deletes it.
- An old date is a signal to delete or re-validate the doc, never to trust it.
