"""REPL commands, run inside Blender. Each is a plain function, so `gn Frame Depth 0.4` at
the `blend repl` prompt and `gn("Frame", "Depth", 0.4)` in Python (or a logged step) do
the same thing.
Commands print their result and return None, so the console shows no repr noise.

Add one with @command; its docstring's first line is its `help` entry.
"""

import fnmatch

import bpy
from kit import gn as _gn

COMMANDS: dict = {}


def command(fn):
    COMMANDS[fn.__name__] = fn
    return fn


def _match(name: str, pattern: str) -> bool:
    if not any(c in pattern for c in "*?["):
        pattern = f"*{pattern}*"
    return fnmatch.fnmatchcase(name.lower(), pattern.lower())


def _object(name: str):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise KeyError(f"no object {name!r}")
    return obj


def _gn_mods(obj) -> list:
    return [m for m in obj.modifiers if m.type == "NODES" and m.node_group]


@command
def help(cmd=None):
    """List commands, or show one command's help. help(obj) falls back to pydoc."""
    if cmd is None:
        width = max(len(n) for n in COMMANDS)
        for name, fn in sorted(COMMANDS.items()):
            print(f"{name:<{width}}  {(fn.__doc__ or '').strip().splitlines()[0]}")
        print("Anything else runs as Python (C, D, bpy, kit are there).")
    elif isinstance(cmd, str) and cmd in COMMANDS:
        print((COMMANDS[cmd].__doc__ or "").strip())
    else:
        import pydoc

        print(pydoc.render_doc(cmd, renderer=pydoc.plaintext))


@command
def ls(pattern="*"):
    """List objects: ls [pattern]. Name, type, collection, dimensions."""
    objs = [o for o in bpy.context.scene.objects if _match(o.name, pattern)]
    for o in sorted(objs, key=lambda o: o.name):
        coll = o.users_collection[0].name if o.users_collection else "-"
        d = o.dimensions
        print(f"{o.name:<24} {o.type:<8} {coll:<12} {d.x:.4g} x {d.y:.4g} x {d.z:.4g}")
    if not objs:
        print(f"no objects match {pattern!r}")


@command
def sel(*patterns):
    """Select objects by name or pattern; the first becomes active. sel alone clears."""
    layer = bpy.context.view_layer
    for o in layer.objects:
        o.select_set(False)
    picked = [
        o for p in patterns for o in layer.objects if o.name == p or _match(o.name, p)
    ]
    for o in picked:
        o.select_set(True)
    if picked:
        layer.objects.active = picked[0]
    print(", ".join(dict.fromkeys(o.name for o in picked)) or "nothing selected")


@command
def zoom():
    """Frame the selection in the 3D viewport (everything when nothing is selected)."""
    screen = bpy.context.screen
    area = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
    if area is None:
        print("no 3D viewport in this workspace")
        return
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(area=area, region=region):
        if bpy.context.selected_objects:
            bpy.ops.view3d.view_selected()
        else:
            bpy.ops.view3d.view_all()


@command
def gn(obj=None, name=None, value=None):
    """Geometry Nodes inputs: gn | gn <obj> | gn <obj> <input> | gn <obj> <input> <value>.
    Quote names with spaces ("Wall Height") or write them with underscores."""
    if obj is None:
        for o in sorted(bpy.data.objects, key=lambda o: o.name):
            mods = _gn_mods(o)
            if mods:
                print(f"{o.name:<24} {', '.join(m.name for m in mods)}")
        return
    mods = _gn_mods(_object(obj))
    if not mods:
        print(f"{obj} has no Geometry Nodes modifier")
        return
    if name is None:
        for m in mods:
            print(f"{m.name}:")
            for k, v in _gn.inputs(m).items():
                print(f"  {k} = {v}")
        return
    for key in (name, name.replace("_", " ")):
        mod = next((m for m in mods if _gn.has_input(m, key)), None)
        if mod is not None:
            break
    else:
        raise KeyError(f"{obj} has no GN input {name!r}")
    old = _gn.get_input(mod, key)
    if value is None:
        print(f"{key} = {old}")
        return
    _gn.set_input(mod, key, value)
    print(f"{key}: {old} -> {_gn.get_input(mod, key)}")


@command
def save():
    """Save the open .blend (do this before any `just` command)."""
    if not bpy.data.filepath:
        print("file has never been saved; use File > Save As")
        return
    bpy.ops.wm.save_mainfile()
    print(f"saved {bpy.data.filepath}")


__all__ = list(COMMANDS)
