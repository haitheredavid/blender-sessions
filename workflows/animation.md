# Animation: parameter sweeps and exploded views

Keyframe GN inputs or object positions with `kit.anim`, then render the scene's own animation in the studio with `blend animate`.

## When to use
- Show how a param changes the form (depth sweep, taper sweep).
- Exploded assembly views: printed sections, clips, layers.

## Steps
1. **Sweep a param:** `anim.sweep(obj.modifiers["GN_OutlineExtrude"], "Height", [20, 60, 20], step=48)`. It sets the scene range.
2. **Explode:** `anim.explode(parts, distance=40, start=1, end=48, axis=(0, 0, 1))`. Each part moves in proportion to its offset from the group centre, so the middle part stays put.
3. Save, then run `uv run blend animate <m> [--fps 24] [--view NAME]`. This writes `out/animation.mp4` and `.gif`.
4. Animation lives in the `.blend`, not in the builders. Builders that key animation must be idempotent: they re-key on rebuild.

## Assembly animations (how parts go together)
1. Write a builder (e.g. `builders/70_assembly.py`) that makes its own **scene** (`Assembly`) and collection. Fill it with `obj.copy()` of the print parts and proxies: copies share mesh data, and GN pieces stay live. That keeps the working scene untouched.
2. Pose the assembly the way it's really built (the witch frame goes face-down: `FLIP @ src.matrix_world`, with no parenting).
3. Beats: each part holds at home + offset, then eases home. Give drop-ins **keyed `hide_render`/`hide_viewport`** so they appear just before their beat and don't hide earlier steps.
4. Parts that swing (turn clips) need their origin on the pivot. Store `pivot` and `swing` as custom props in the part's builder, then re-origin a data copy in the assembly scene.
5. Render: `uv run blend animate <m> --scene Assembly --collection Assembly --isometric` gives an orthographic camera at az 45 / el 35.264, framed over every pose.

## Gotchas
- **GN input keyframes** live at `modifiers["X"].properties.inputs.Socket_N.value` in Blender 5. `anim.key_input` resolves the path by socket name.
- **Framing:** with `--animate`, the studio frames the union of 9 sampled poses (exploded starts are the widest) and places the floor at the END state. It collects objects on the END frame, so parts keyed hidden early still render.
- **Studio placement uses an offset empty above the roots**, so keyed object locations keep the centring.

## Models
- witch-frame (2026-10-10): assembly animation. Pieces slide together, then the keys, glazing/art/backboard and turn clips drop in (isometric, 228 frames).
