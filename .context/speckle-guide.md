# Speckle Guide

Speckle (app.speckle.systems, the user's personal account) is the versioned record of each model. The **Speckle Blender connector** (v3) installed in Blender owns the login, publishing and loading.

## Setup (user, once)

1. Install the Speckle Blender connector (docs.speckle.systems/connectors/blender) and enable it in Blender.
2. Sign in from the connector panel. The connector stores the account locally.
3. Never read, print or copy the stored credentials into the repo or `.env`.

## Mapping

| Repo | Speckle |
|---|---|
| model `models/<m>/` | project (ids in `model.toml [speckle]`) |
| base / variant `<v>` | model `<m>` / `<m>/<v>` |
| `/checkpoint` | version, message = checkpoint message |

## What a checkpoint publishes

- The Model collection of the active variant with **Apply Modifiers** on, so the published geometry is the evaluated GN result.
- Properties: `params` (merged for the variant), `variant`, `step` (latest log step), `session`, git sha.
- The returned version id is recorded on the latest step: `blend step <m> --speckle-version <id>`.
- Checkpoints are explicit (user asks, or `/wrap`). Never publish after every step.

## Driving the connector over MCP

TODO: filled in by the Phase 3 spike (see `active/20261010-restructure.md`). Record the add-on module name, the publish/load operators or functions, their parameters, and whether they work headless. `lib/kit/speckle.py` wraps the chosen path.

## Comparing versions

- Load an older version through the connector panel, or with `kit.speckle.load(...)` into **Ref** for a side-by-side.
- Loaded geometry is reference only. Never move it into Model.
