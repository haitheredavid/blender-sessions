# Web demo

Publish a model to the Pages gallery (site/, `haitheredavid.github.io/bless/`): an orbitable React-Three-Fiber viewer of the assembled model, plus an exploded view of its print parts.

## When to use
- A model is worth showing off (usually at `/wrap` or when it's marked done).
- After a geometry change to a model that's already published (it has `web/model.glb`).

## Steps
1. Save the live file, then `just site-export <m>`. It writes `models/<m>/web/model.glb` (the Model collection) and `web/parts.glb` (`[site] parts`, default the `[print]` collection; skipped if that collection doesn't exist).
2. `just site-dev` gathers every model with a `web/model.glb` into `site/public/` (`blend site`) and serves the site at `http://localhost:5173/bless/`. Check the model page: upright, framed, and the parts toggle explodes cleanly.
3. Commit `web/*.glb` (LFS). A push to `main` that touches `models/*/web/`, `render.png`, `model.toml` or `site/` redeploys through `.github/workflows/pages.yml`.

## Config
```toml
[site]                 # all optional
parts = "Print"        # "" for no parts view
upright = true         # default: [[views]] hero's upright
speckle = false        # link the Speckle project; only once it's public
```

## Gotchas
- The GLBs keep Blender's numbers (mm models are ~300 units across), so the viewer scales every model to ~1 unit. Don't rescale at export.
- `upright` rotates +90 deg about X in glTF space: Blender's +Z face turns toward the camera and +Y becomes up, matching `blend views` upright shots.
- `Ref` and `Control` aren't exported, so art proxies don't show. Never publish third-party reference images (`refs/`).
- The gallery tile is `render.png`, so re-render after a visible change.
- Pages builds only pull `web/*.glb` and `render.png` from LFS, so keep the site's data in those files.

## Models
- witch-frame (2026-10-11): first published model; the Frame and 8 clips assembled, plus the 16 print parts exploded.
