"""Blender side of `blend repl`: run one input in a namespace that persists between inputs.

The host sends, through the blender-mcp add-on's execute_code (which starts every call
with a fresh namespace):

    from cmdline import remote; remote.run(SRC)

The REPL namespace lives in bpy.app.driver_namespace, so it survives across calls but is
never saved in the .blend. run() prints the input's output, then a trailer: MARK followed
by JSON {ok, error, file, commands, objects, gn} for the host's prompt, completion and logging.
"""

import ast
import builtins
import json
import sys
import traceback

import bpy
import mathutils

MARK = "\x00blend-repl\x00"
KEY = "blend_repl"


def namespace(reset: bool = False) -> dict:
    ns = bpy.app.driver_namespace.get(KEY)
    if ns is None or reset:
        import kit

        from cmdline import commands

        ns = {"__name__": "__repl__", "__builtins__": builtins}
        ns.update(bpy=bpy, C=bpy.context, D=bpy.data, kit=kit)
        ns.update(
            {
                k: getattr(mathutils, k)
                for k in ("Vector", "Matrix", "Euler", "Quaternion")
            }
        )
        ns.update(commands.COMMANDS)
        bpy.app.driver_namespace[KEY] = ns
    return ns


def _exec(src: str, ns: dict) -> None:
    """Exec src; when it ends in an expression, print its repr like the Python REPL."""
    tree = ast.parse(src, "<repl>", "exec")
    last = (
        tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    )
    exec(compile(tree, "<repl>", "exec"), ns)  # noqa: S102 - a REPL runs typed code
    if last is not None:
        value = eval(compile(ast.Expression(last.value), "<repl>", "eval"), ns)
        if value is not None:
            ns["_"] = value
            print(repr(value))


def _state() -> dict:
    gn = {}
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type == "NODES" and m.node_group:
                names = [
                    i.name
                    for i in m.node_group.interface.items_tree
                    if i.item_type == "SOCKET"
                    and i.in_out == "INPUT"
                    and i.socket_type != "NodeSocketGeometry"
                ]
                gn.setdefault(o.name, []).extend(names)
    from cmdline import commands

    return {
        "file": bpy.data.filepath,
        "commands": sorted(commands.COMMANDS),
        "objects": sorted(o.name for o in bpy.data.objects),
        "gn": gn,
    }


def run(src: str, reset: bool = False) -> None:
    ns = namespace(reset)
    error = None
    try:
        _exec(src, ns)
    except SyntaxError:
        error = "".join(traceback.format_exception_only(*sys.exc_info()[:2]))
    except Exception:  # noqa: BLE001 - the REPL reports any error from typed code
        etype, value, tb = sys.exc_info()
        user = tb  # start the traceback at the typed code, not at this module
        while user is not None and user.tb_frame.f_code.co_filename != "<repl>":
            user = user.tb_next
        error = "".join(traceback.format_exception(etype, value, user or tb))
    print(MARK + json.dumps({"ok": error is None, "error": error, **_state()}))
