"""Dimensions: live GN dimension lines between two Control anchors, in the Notes collection.

    from kit import annotate
    annotate.dim("Width", (-140, -190, 0), (140, -190, 0), offset=-15, suffix=" mm")

The anchors are Control empties (CTL_DIM_<name>_A/_B), or any objects you pass. Move them
(or parent/snap them to model features) and the line and its measured label update live.
Dimension objects (DIM_<name>) are meshes in Notes: hidden from check/export/render, and
shown by `blend views` shots that include = ["Notes"].
"""

import bpy
from mathutils import Vector

from kit import control, gn, materials, scene

NAME = "GN_Dimension"


def build(reset: bool = False):
    t = gn.tree(NAME)
    if t.nodes and not reset:
        return t
    t = gn.tree(NAME, reset=True)
    gn.input(t, "Geometry", "GEOMETRY")
    gn.input(t, "Start", "OBJECT")
    gn.input(t, "End", "OBJECT")
    gn.input(t, "Offset", "FLOAT", 10.0, subtype="DISTANCE")
    gn.input(
        t, "Normal", "VECTOR", (0.0, 0.0, 1.0), description="Plane the line sits in"
    )
    gn.input(t, "Text Size", "FLOAT", 5.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Thickness", "FLOAT", 0.4, min=0.0, subtype="DISTANCE")
    gn.input(t, "Decimals", "INT", 1, min=0, max=6)
    gn.input(t, "Suffix", "STRING", "")
    gn.input(t, "Material", "MATERIAL")
    gn.output(t, "Geometry")
    gin, gout = gn.io(t)

    def vmath(op, a, a_out, b=None, b_out=None, scale=None):
        n = gn.node(t, "ShaderNodeVectorMath", props={"operation": op})
        gn.link(t, a, a_out, n, 0)
        if b is not None:
            gn.link(t, b, b_out, n, 1)
        if scale is not None:
            gn.link(t, scale[0], scale[1], n, "Scale")
        return n

    sa = gn.node(t, "GeometryNodeObjectInfo", "Start")
    sb = gn.node(t, "GeometryNodeObjectInfo", "End")
    gn.link(t, gin, "Start", sa, "Object")
    gn.link(t, gin, "End", sb, "Object")
    along = vmath("SUBTRACT", sb, "Location", sa, "Location")
    side = vmath("NORMALIZE", vmath("CROSS_PRODUCT", along, 0, gin, "Normal"), 0)
    off = vmath("SCALE", side, 0, scale=(gin, "Offset"))
    a = vmath("ADD", sa, "Location", off, 0)
    b = vmath("ADD", sb, "Location", off, 0)

    lines = gn.node(t, "GeometryNodeJoinGeometry")
    for p, q in ((a, b), (sa, a), (sb, b)):  # dimension line + two extension lines
        ln = gn.node(t, "GeometryNodeCurvePrimitiveLine")
        gn.link(t, p, 0 if p in (a, b) else "Location", ln, "Start")
        gn.link(t, q, 0 if q in (a, b) else "Location", ln, "End")
        gn.link(t, ln, "Curve", lines, "Geometry")
    radius = gn.node(t, "ShaderNodeMath", props={"operation": "MULTIPLY"})
    gn.link(t, gin, "Thickness", radius, 0)
    radius.inputs[1].default_value = 0.5
    circle = gn.node(t, "GeometryNodeCurvePrimitiveCircle", Resolution=6)
    gn.link(t, radius, "Value", circle, "Radius")
    tube = gn.node(t, "GeometryNodeCurveToMesh", Fill_Caps=True)
    gn.link(t, lines, "Geometry", tube, "Curve")
    gn.link(t, circle, "Curve", tube, "Profile Curve")

    # label: measured distance + suffix, centred above the line, aligned with it
    dist = vmath("DISTANCE", sa, "Location", sb, "Location")
    num = gn.node(t, "FunctionNodeValueToString")
    gn.link(t, dist, "Value", num, "Value")
    gn.link(t, gin, "Decimals", num, "Decimals")
    text = gn.node(t, "GeometryNodeStringJoin")
    gn.link(t, gin, "Suffix", text, "Strings")  # multi-input: last linked comes first
    gn.link(t, num, "String", text, "Strings")
    curves = gn.node(
        t, "GeometryNodeStringToCurves", Align_X="Center", Align_Y="Bottom"
    )
    gn.link(t, text, "String", curves, "String")
    gn.link(t, gin, "Text Size", curves, "Size")
    real = gn.node(t, "GeometryNodeRealizeInstances")
    gn.link(t, curves, "Curve Instances", real, "Geometry")
    fill = gn.node(t, "GeometryNodeFillCurve")
    gn.link(t, real, "Geometry", fill, "Curve")
    align = gn.node(t, "FunctionNodeAlignRotationToVector", props={"axis": "X"})
    gn.link(t, along, 0, align, "Vector")
    mid = vmath("SCALE", vmath("ADD", a, 0, b, 0), 0)
    mid.inputs["Scale"].default_value = 0.5
    lift = gn.node(t, "ShaderNodeMath", props={"operation": "MULTIPLY"})
    gn.link(t, gin, "Text Size", lift, 0)
    lift.inputs[1].default_value = 0.3
    above = vmath("ADD", mid, 0, vmath("SCALE", side, 0, scale=(lift, "Value")), 0)
    place = gn.node(t, "GeometryNodeTransform")
    gn.link(t, fill, "Mesh", place, "Geometry")
    gn.link(t, align, "Rotation", place, "Rotation")
    gn.link(t, above, 0, place, "Translation")

    join = gn.node(t, "GeometryNodeJoinGeometry")
    gn.link(t, tube, "Mesh", join, "Geometry")
    gn.link(t, place, "Geometry", join, "Geometry")
    mat = gn.node(t, "GeometryNodeSetMaterial")
    gn.link(t, join, "Geometry", mat, "Geometry")
    gn.link(t, gin, "Material", mat, "Material")
    gn.link(t, mat, "Geometry", gout, "Geometry")
    gn.arrange(t)
    return t


def _anchor(name: str, where) -> bpy.types.Object:
    if isinstance(where, bpy.types.Object):
        return where
    return control.ensure(name, lambda n: control.empty(n, where, size=2.0))


def dim(
    name: str,
    a,
    b,
    offset: float | None = None,
    normal=(0.0, 0.0, 1.0),
    size: float | None = None,
    suffix: str = "",
    decimals: int = 1,
    color: str = "#1C1C1E",
) -> bpy.types.Object:
    """A live dimension DIM_<name> between a and b (objects, or points for new Control
    empties). offset/size default to a fraction of the measured length."""
    sa = _anchor(f"CTL_DIM_{name}_A", a)
    sb = _anchor(f"CTL_DIM_{name}_B", b)
    length = (
        sb.location - sa.location
    ).length or 1.0  # matrix_world is stale until eval
    size = size or length * 0.04
    host = gn.host(f"DIM_{name}", scene.notes())
    gn.modifier(
        host,
        build(),
        Start=sa,
        End=sb,
        Offset=offset if offset is not None else size * 2.5,
        Normal=Vector(normal),
        Text_Size=size,
        Thickness=size * 0.08,
        Decimals=decimals,
        Suffix=suffix,
        Material=materials.principled("dim_ink", color, roughness=0.8),
    )
    return host
