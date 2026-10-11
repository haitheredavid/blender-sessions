"""kit: bpy helpers shared by session builders (runs inside Blender; bpy/bmesh only).

Builders reach it through models/<m>/builders/build_all.py, which puts lib/ on sys.path
and reloads these modules so edits take effect without restarting Blender:

    from kit import scene, mesh, materials

Modules: scene (collections), mesh (bmesh/modifiers), materials, gn (Geometry Nodes
groups and modifier inputs), params (params.toml, units, variant grid), control (Control
curves/empties), annotate (dimensions), gp (grease pencil), anim (keyframes), speckle
(checkpoints through the Speckle connector). GN patterns live in lib/patterns.

Grow it from models: when /wrap finds a helper worth reusing, move it here.
"""
