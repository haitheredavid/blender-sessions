# Bug: Speckle checkpoints publish without mesh geometry

## Symptom
`/checkpoint` (`kit.speckle.publish`) succeeds and returns a version id, and the version shows up on app.speckle.systems. In the viewer, though, no geometry appears: some data landed but not the mesh data.

- Project `blender-sessions` (`de2b7457ae`), model `witch-frame` (`c70f68dd96`).
- Versions `23b410c176` (baked bmesh Frame, 8 clip meshes) and `b8a0881e09` (GN `GN_FrameLoft` Frame with live boolean modifiers, 8 clips).
- `b8a0881e09` was published headless (`blender -b ... -P`); `23b410c176` from the live GUI over MCP.

## Setup
- Speckle Blender connector built from GitHub `main` at `cdc9648`, version-patched to `2026.10.0`. Blender 5.2.2; the docs list support only up to 5.1.
- `publish_operation(context, account_id, project_id, model_id, objects, apply_modifiers=True)` with the Model collection's objects. Publish uses parquet bundles (connector PR #321, "Migrate Blender publish and receive to parquet bundles").
- The model is in mm: `scale_length = 0.001`, 1 BU = 1 mm.
- Objects carry `blend_*` custom props during publish.

## Hypotheses (unverified)
1. **GN host objects:** the Frame's base mesh is empty and all geometry comes from the modifier. If the converter reads `obj.data` instead of the evaluated mesh, the frame publishes empty. This doesn't explain the baked `23b410c176`.
2. **Units/scale:** mm geometry with `scale_length = 0.001` might be converted with the wrong units, so it ends up microscopic or far off in the viewer.
3. **Blender 5.2 vs connector:** a mesh API change (attributes, loop triangles) in 5.2 that the converter doesn't handle. The bundle may then carry only the collection/properties rows.
4. **Bundle ingestion:** the server stores the version but the mesh parquet rows aren't ingested (a server or connector version mismatch).

## Next steps
1. Run the connector's harness on the model to see whether mesh rows exist in the bundle:
   `~/projects/speckle-blender/tools/run_fixture.sh --blend models/witch-frame/model.blend --objects Frame,Clip_01`
   Compare with and without `--no-modifiers`.
2. Publish a trivial metre-scale cube from a fresh file to separate units from GN from a general failure.
3. Load `b8a0881e09` back through the connector (`kit.speckle.load`) and inspect what arrives in Ref.
4. If it's a connector bug, report it upstream (specklesystems/speckle-blender) with the harness output.

Delete this doc once checkpoints show geometry, and fold the fix or caveat into `.context/speckle-guide.md`.
