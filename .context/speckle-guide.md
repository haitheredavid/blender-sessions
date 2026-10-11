# Speckle Guide

Speckle (app.speckle.systems) is the versioned record of each model. The **Speckle Blender connector**, installed in Blender as an extension, owns the login and the conversion. `lib/kit/speckle.py` drives the connector's own operations over MCP.

## Account

- Always publish as **haitheredavid@gmail.com** (`model.toml [speckle] account`).
- The connector's *default* local account may be a different (work) account. Never use or change the default.
- `kit.speckle.account_id(email)` raises if the account is missing; it never falls back.
- Credentials live in the connector (`~/.config/Speckle`). `.env` may hold a `SPECKLE_TOKEN` for headless fallbacks. Never read, print or copy either.

## Connector install (built from source)

The released zips lag new Blender versions, so the connector is built from GitHub `main`:

```sh
cd ~/projects/speckle-blender && git pull
uv sync --all-extras --dev && ./export_dependencies.sh
python3 patch_version.py 2026.10.0      # numeric only; "+dev" breaks bl_info
zip -r dist/speckle-blender.zip bpy_speckle -x '*/AGENTS.md'
```

Install it into the running Blender over MCP:
```python
bpy.ops.extensions.package_install_files(
    filepath=".../dist/speckle-blender.zip", repo="user_default", enable_on_install=True
)
```
First enable installs specklepy into `~/.config/Speckle/connector_installations/Blender <ver>/`.

## Mapping

| Repo | Speckle |
|---|---|
| this repo | project `blender-sessions` (`model.toml [speckle] project_id`) |
| model `<m>`, variant `base` | model `<m>` |
| variant `<v>` | model `<m>/<v>` (nested in the web UI) |
| `/checkpoint` | a version |

Models are resolved by name (`kit.speckle.ensure_model`), so no ids need storing.

## What a checkpoint publishes

- The Model collection, with modifiers applied, so the published geometry is the evaluated GN result.
- Versions have no message field (a server API gap), so context rides on each object as custom properties: `blend_model`, `blend_variant`, `blend_step`, `blend_session`, `blend_git`. They're stamped only for the publish and removed afterwards.
- The returned version id goes on the latest step: `blend step <m> --speckle-version <id>`.
- Checkpoints are explicit (the user asks, or `/wrap`). Never publish after every step.

## Driving the connector over MCP

- Connector modules live under `bl_ext.user_default.speckle_blender_addon`. `kit.speckle._addon()` finds them.
- **Publish:** `connector.operations.publish_operation.publish_operation(context, account_id, project_id, model_id, objects, apply_modifiers)` returns `(ok, message, version_id)`. It never reads UI state.
- **Load:** `connector.operations.load_operation.load_operation(context, account_id, project_id, model_id, version_id, name)`.
- **Client:** `connector.speckle_api.client_cache.get_client(account_id)` returns a specklepy client, used for models, versions and creating.
- The connector's `create_project` makes **public** workspace projects. Create projects through the client (`client.project.create(ProjectCreateInput(..., visibility=PRIVATE))`) if a new one is ever needed.
- The connector repo's `tools/headless_export.py` shows publish conversion without the UI. It's the starting point if a headless `blend push` is ever needed.

## Comparing versions

- `kit.speckle.load(cfg, model_id[, version_id])` loads a version into **Ref**. The connector panel can also browse and load versions.
- Loaded geometry is reference only. Never move it into Model.
