"""Geometry Nodes: build node groups in code, attach them as modifiers, read/write inputs.

Everything addresses sockets by their *name* ("Depth"), never by identifier ("Socket_2"):
identifiers depend on creation order and break as soon as a group is edited by hand.
Blender 5 moved modifier inputs from ID properties (mod["Socket_2"]) to
mod.properties.inputs.Socket_2.value; set_input/get_input handle both.

    t = gn.tree("GN_Thing")                       # get or create (is_modifier)
    gn.input(t, "Depth", "FLOAT", 40.0, min=0)    # idempotent by name
    gin, gout = gn.io(t)
    ext = gn.node(t, "GeometryNodeExtrudeMesh", Offset_Scale=...)
    gn.link(t, gin, "Geometry", ext, "Mesh")
    gn.arrange(t)
    mod = gn.modifier(obj, t, Depth=60.0)
    gn.set_input(mod, "Depth", 55.0)
"""

import bpy

SOCKET_TYPES = {
    "GEOMETRY": "NodeSocketGeometry",
    "FLOAT": "NodeSocketFloat",
    "INT": "NodeSocketInt",
    "BOOL": "NodeSocketBool",
    "VECTOR": "NodeSocketVector",
    "OBJECT": "NodeSocketObject",
    "COLLECTION": "NodeSocketCollection",
    "MATERIAL": "NodeSocketMaterial",
    "STRING": "NodeSocketString",
    "COLOR": "NodeSocketColor",
}


def tree(name: str, reset: bool = False) -> bpy.types.GeometryNodeTree:
    """Get or create a modifier node group. reset=True empties it for a clean rebuild."""
    t = bpy.data.node_groups.get(name)
    if t is None:
        t = bpy.data.node_groups.new(name, "GeometryNodeTree")
    elif reset:
        t.nodes.clear()
        t.interface.clear()
    t.is_modifier = True
    return t


def _items(t, in_out: str) -> dict:
    return {
        i.name: i
        for i in t.interface.items_tree
        if i.item_type == "SOCKET" and i.in_out == in_out
    }


def input(
    t,
    name: str,
    kind: str = "FLOAT",
    default=None,
    min=None,
    max=None,
    subtype: str | None = None,
    description: str = "",
):
    """Get or create a group input socket by name; set default/min/max when given."""
    sock = _items(t, "INPUT").get(name)
    if sock is None:
        sock = t.interface.new_socket(
            name, in_out="INPUT", socket_type=SOCKET_TYPES[kind]
        )
    if description:
        sock.description = description
    if subtype and hasattr(sock, "subtype"):
        sock.subtype = subtype
    if min is not None and hasattr(sock, "min_value"):
        sock.min_value = min
    if max is not None and hasattr(sock, "max_value"):
        sock.max_value = max
    if default is not None and hasattr(sock, "default_value"):
        sock.default_value = default
    return sock


def output(t, name: str = "Geometry", kind: str = "GEOMETRY"):
    sock = _items(t, "OUTPUT").get(name)
    if sock is None:
        sock = t.interface.new_socket(
            name, in_out="OUTPUT", socket_type=SOCKET_TYPES[kind]
        )
    return sock


def io(t) -> tuple[bpy.types.Node, bpy.types.Node]:
    """The group input and output nodes (created if missing)."""
    gin = next((n for n in t.nodes if n.bl_idname == "NodeGroupInput"), None)
    gout = next((n for n in t.nodes if n.bl_idname == "NodeGroupOutput"), None)
    gin = gin or t.nodes.new("NodeGroupInput")
    gout = gout or t.nodes.new("NodeGroupOutput")
    return gin, gout


def _socket(sockets, key):
    """A node socket by index or by name (first enabled match; Math has three 'Value's)."""
    if isinstance(key, int):
        return sockets[key]
    for s in sockets:
        if s.name == key and s.enabled:
            return s
    for s in sockets:
        if s.identifier == key:
            return s
    raise KeyError(f"no socket {key!r} in {[s.name for s in sockets]}")


def node(t, idname: str, label: str = "", props: dict | None = None, **inputs):
    """Add a node. props sets node properties (e.g. operation, transform_space); kwargs
    set input defaults by socket name, with spaces written as underscores."""
    n = t.nodes.new(idname)
    if label:
        n.label = label
    for k, v in (props or {}).items():
        setattr(n, k, v)
    for k, v in inputs.items():
        _socket(n.inputs, k.replace("_", " ")).default_value = v
    return n


def link(t, a, a_out, b, b_in):
    """Link a.outputs[a_out] -> b.inputs[b_in] (names or indices)."""
    return t.links.new(_socket(a.outputs, a_out), _socket(b.inputs, b_in))


def arrange(t, dx: float = 220.0, dy: float = 180.0) -> None:
    """Lay nodes out left-to-right by link depth so the tree reads in the node editor."""
    depth = {n: 0 for n in t.nodes}
    for _ in range(len(t.nodes)):
        changed = False
        for lk in t.links:
            d = depth[lk.from_node] + 1
            if d > depth[lk.to_node]:
                depth[lk.to_node], changed = d, True
        if not changed:
            break
    columns: dict[int, list] = {}
    for n, d in depth.items():
        columns.setdefault(d, []).append(n)
    for d, nodes in columns.items():
        for i, n in enumerate(nodes):
            n.location = (d * dx, -i * dy)


# --- modifiers -----------------------------------------------------------------


def host(name: str, coll=None) -> bpy.types.Object:
    """Get or create an empty-mesh object (in Model by default) to carry GN modifiers."""
    from kit import scene

    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        (coll or scene.model()).objects.link(obj)
    return obj


def modifier(obj, t, name: str | None = None, **inputs) -> bpy.types.Modifier:
    """Get or add a NODES modifier running group t; kwargs set inputs by socket name
    (underscores stand for spaces)."""
    name = name or t.name
    mod = obj.modifiers.get(name)
    if mod is None:
        mod = obj.modifiers.new(name, "NODES")
    mod.node_group = t
    for k, v in inputs.items():
        set_input(mod, k.replace("_", " "), v)
    return mod


def socket_id(t, name: str) -> str:
    sock = _items(t, "INPUT").get(name)
    if sock is None:
        raise KeyError(
            f"{t.name} has no input {name!r}; has {list(_items(t, 'INPUT'))}"
        )
    return sock.identifier


def has_input(mod, name: str) -> bool:
    return mod.node_group is not None and name in _items(mod.node_group, "INPUT")


def _read(mod, ident: str):
    """Current value of input `ident`. Blender 5 keeps modifier inputs in
    mod.properties.inputs.<id>.value; older versions used ID properties (mod[id])."""
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props, "inputs"):
        return getattr(props.inputs, ident).value
    return mod.get(ident)


def _write(mod, ident: str, value) -> None:
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props, "inputs"):
        getattr(props.inputs, ident).value = value
    else:
        mod[ident] = value


def set_input(mod, name: str, value) -> None:
    """Set a modifier input by socket name and re-evaluate. Coerces to the socket's type
    (60 -> 60.0 for a float, "CTL_Path" -> the object) so the input never turns red."""
    sock = _items(mod.node_group, "INPUT").get(name)
    if sock is None:
        raise KeyError(f"{mod.node_group.name} has no input {name!r}")
    kind = sock.socket_type
    if kind == "NodeSocketFloat":
        value = float(value)
    elif kind == "NodeSocketInt":
        value = int(value)
    elif kind == "NodeSocketBool":
        value = bool(value)
    elif kind == "NodeSocketObject" and isinstance(value, str):
        value = bpy.data.objects[value]
    elif kind == "NodeSocketMaterial" and isinstance(value, str):
        value = bpy.data.materials[value]
    _write(mod, sock.identifier, value)
    mod.id_data.update_tag()


def _plain(v):
    if hasattr(v, "name") and hasattr(v, "users"):  # ID (object, material, ...)
        return v.name
    if hasattr(v, "__len__") and not isinstance(v, str):
        return list(v)
    return v


def get_input(mod, name: str):
    """A modifier input by socket name (IDs as their name, vectors as lists)."""
    return _plain(_read(mod, socket_id(mod.node_group, name)))


def inputs(mod) -> dict:
    """All non-geometry inputs of a GN modifier as {name: value}."""
    return {
        name: _plain(_read(mod, sock.identifier))
        for name, sock in _items(mod.node_group, "INPUT").items()
        if sock.socket_type != "NodeSocketGeometry"
    }


def gn_modifiers(obj) -> list[bpy.types.Modifier]:
    return [m for m in obj.modifiers if m.type == "NODES" and m.node_group]
