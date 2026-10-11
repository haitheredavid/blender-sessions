# blender-sessions

Modeling in Blender through [blender-mcp](https://github.com/ahujasid/blender-mcp), alongside an agent. Each model lives in `models/<name>/` and is iterated over many short sessions. It stays parametric (Geometry Nodes driven by `Control` curves you can reshape by hand), every step is logged, and checkpoints are versioned to [Speckle](https://speckle.systems). The techniques that work get written up in [`workflows/`](workflows/). Agent context lives in [`AGENTS.md`](AGENTS.md) and [`.context/`](.context/).

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

## working

In Claude Code:

- `/model <idea>` plans a new model and creates `models/<slug>/`.
- `/session <model> [goal]` is one short sitting. It loads the brief, params and recent steps, models live in Blender, and logs each step.
- `/checkpoint [msg]` publishes a Speckle version of the current state.
- `/wrap` promotes steps into builders, then checks, exports and renders. It also distills `workflows/`, checkpoints, and offers a commit.

By hand:

```sh
just                       # list recipes
just new teapot            # new model + model.blend (metres; --unit mm for small parts), opened in Blender
just session teapot spout  # start a session note
just history teapot        # step timeline across sessions
just check teapot          # mesh health: loose geo, degenerate faces, flipped normals, transforms
just export teapot         # Model collection -> exports/*.glb (fbx/obj via [export] or --formats)
just render teapot         # studio render -> render.png + gallery below
just views teapot          # [[views]] shots -> out/views/
just turntable teapot      # 360° mp4 + gif in out/
just workflows             # workflow docs and the models that use them
```

## models

<!-- gallery:start -->
<p align="center">
<a href="models/witch-frame/brief.md"><img src="docs/gallery/witch-frame.png" width="24%" alt="witch-frame" title="3D-printable shadow-box frame for a 9x12in witch illustration: concave bat-wing sides with flared corner tips, a face sloping from a thin outer edge into a deep sightwell, and a rabbet with turn clips for a 10x13in backboard."></a>
</p>
<!-- gallery:end -->
