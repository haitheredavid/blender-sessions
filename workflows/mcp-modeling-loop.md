# MCP modeling loop

The base loop for building a model in a live Blender through blender-mcp: small code steps, look often, persist everything in builders/.

## When to use
- Every session. Other workflows plug into step 3.

## Steps
1. `just open <session>` (or `just new`): the add-on bridge starts on port 9876. Only one Blender may own the port; close others first or you'll model into the wrong file.
2. `get_addon_status`, then `get_scene_info`: confirm the right file is open (`bpy.data.filepath`) and the Model / Work / Ref collections exist.
3. Build in small `execute_blender_code` steps (one part or one modifier stack at a time). Put deliverable geometry in **Model**; cutters, helpers and blockouts in **Work**; references in **Ref**.
4. `look` after every meaningful step. Use a small `max_size` (~512) for routine checks and go bigger only for detail review.
5. Once a step works, copy its code into `builders/NN_<part>.py`, so `build_all.py` can rebuild the model from scratch. Experiments can stay ad hoc; the result can't.
6. `bpy.ops.wm.save_mainfile()` before any `just` command, since the headless scripts read the file from disk.
7. `just check <s>` → fix → `just render <s>`.

## bpy
```python
# rebuild everything from builders/ (model.blend open)
exec(
    open(bpy.path.abspath("//builders/build_all.py")).read(), {"__name__": "build_all"}
)

# shader nodes: find by type, never by name (names are localized)
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

# enums: read valid identifiers instead of hardcoding
[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
```

## Gotchas
- Material colours go on shader node inputs. `material.diffuse_color` only affects the solid viewport.
- `scene.render.engine` under-reports its options. Assign inside `try/except TypeError`; the error message lists the valid engines.
- Imported or generated assets (`import_asset`, `generate_3d`) arrive at arbitrary scale. Size them from the reported `world_bounding_box` and put them on the ground.
- Python state persists between `execute_blender_code` calls. `kit` modules are reloaded by `build_all.py`, but ad-hoc imports are not, so reload them yourself.

## Sessions
