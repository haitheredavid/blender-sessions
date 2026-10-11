---
name: checkpoint
description: Publish the current state of a model to Speckle as a new version through the Speckle Blender connector, on the user's personal account, and record the version id in the model's step log. Use when the user says "checkpoint", "publish to speckle", "save a version", or invokes /checkpoint [model] [variant].
argument-hint: "[model] [variant]"
---

# Checkpoint: publish a Speckle version

Arguments: $ARGUMENTS. Model defaults to the one in this conversation, else `uv run blend model latest`. Variant defaults to `base`.

Read `.context/speckle-guide.md` first.

1. **Preflight** (over MCP):
   - assert `bpy.data.filepath` is `models/<m>/model.blend`;
   - confirm the connector is loaded;
   - `kit.speckle.config()` must name the account `haitheredavid@gmail.com`. Never publish with any other account.
2. **Variant:** if it isn't `base`, `kit.params.apply("<variant>")` first, then re-apply `base` afterwards.
3. Save, then run `just check <m>`. Stop on failures unless the user accepts them.
4. **Publish** (MCP):
   ```python
   from kit import speckle
   cfg = speckle.config()
   name = "<m>" if variant == "base" else "<m>/<variant>"
   mid = speckle.ensure_model(cfg, name)
   vid = speckle.publish(cfg, mid, props={"model": "<m>", "variant": variant,
         "step": <latest step n>, "session": "<latest session>", "git": "<short sha>"})
   ```
5. **Record:** `uv run blend step <m> --speckle-version <vid>`. This attaches it to the latest step; if there are no steps yet, log one first (`blend step <m> checkpoint --intent "..."`).
6. Report the version id and the link `https://app.speckle.systems/projects/<project_id>/models/<mid>`.
