"""kit: bpy helpers shared by session builders (runs inside Blender; bpy/bmesh only).

Builders reach it through sessions/<s>/builders/build_all.py, which puts lib/ on sys.path
and reloads these modules so edits take effect without restarting Blender:

    from kit import scene, mesh, materials

Grow it from sessions: when /done finds a helper worth reusing, move it here.
"""
