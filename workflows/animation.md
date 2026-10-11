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

## Gotchas
- **GN input keyframes** live at `modifiers["X"].properties.inputs.Socket_N.value` in Blender 5. `anim.key_input` resolves the path by socket name.
- **The studio frames the END state** (fully exploded). The assembled start may float above the floor; flip start and end if the assembled state should sit on it.
- **Studio placement uses an offset empty above the roots**, so keyed object locations keep the centring.

## Models
