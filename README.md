# blender-sessions

Modeling in Blender through [blender-mcp](https://github.com/ahujasid/blender-mcp), one model per session. Each session leaves behind its `.blend`, the code that builds it, exports and a render. More importantly, the techniques that worked get written up in [`workflows/`](workflows/) so the next session starts smarter.

This is a sibling of [bambi](https://github.com/haitheredavid/bambi), with the 3D-printing pipeline swapped for a modeling one.

## setup

macOS. You'll need Blender, [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just) and ffmpeg (for turntables):

```sh
brew install --cask blender
brew install uv just ffmpeg git-lfs
git lfs install
just setup
```

`just addon` installs or updates the MCP for Blender add-on (`uvx mcp-for-blender install-addon`); restart Blender after. The MCP server itself is wired up in `.mcp.json`.

## sessions

In Claude Code:

- `/make <idea>` plans the model, creates `sessions/YYYY-MM-DD-<slug>/`, opens it in Blender and builds it live.
- `/done` checks, exports and renders the model, writes up lessons, and updates `workflows/`.

By hand:

```sh
just                     # list recipes
just new teapot          # new session + model.blend (metres; --unit mm for small parts), opened in Blender
just check teapot        # mesh health: loose geo, degenerate faces, flipped normals, transforms
just export teapot       # Model collection -> exports/*.glb (fbx/obj via [export] or --formats)
just render teapot       # studio render -> render.png + gallery below
just turntable teapot    # 360° mp4 + gif in out/
just workflows           # workflow docs and the sessions that use them
```

## models

<!-- gallery:start -->
_nothing rendered yet_
<!-- gallery:end -->
