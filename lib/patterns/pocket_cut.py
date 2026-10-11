"""GN_PocketCut: cut a rounded-rectangle pocket into the incoming geometry.

Rabbets, recesses, backboard seats. The pocket is Pocket Width x Pocket Height, centred at
Pocket Center (XY), running from Pocket Bottom up Pocket Depth along Z. Chain it after a
shape modifier. Inputs are prefixed so params.toml keys don't collide with other patterns.
"""

from kit import gn

NAME = "GN_PocketCut"


def build(reset: bool = False):
    t = gn.tree(NAME)
    if gn.current(t, __file__) and not reset:
        return t
    t = gn.tree(NAME, reset=True)
    gn.input(t, "Geometry", "GEOMETRY")
    gn.input(t, "Pocket Width", "FLOAT", 0.1, min=0.0, subtype="DISTANCE")
    gn.input(t, "Pocket Height", "FLOAT", 0.1, min=0.0, subtype="DISTANCE")
    gn.input(t, "Pocket Depth", "FLOAT", 0.01, min=0.0, subtype="DISTANCE")
    gn.input(
        t,
        "Pocket Bottom",
        "FLOAT",
        0.0,
        subtype="DISTANCE",
        description="Z where it starts",
    )
    gn.input(t, "Pocket Corner Radius", "FLOAT", 0.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Pocket Center", "VECTOR", (0.0, 0.0, 0.0), subtype="TRANSLATION")
    gn.output(t, "Geometry")
    gin, gout = gn.io(t)
    quad = gn.node(t, "GeometryNodeCurvePrimitiveQuadrilateral")
    fillet = gn.node(t, "GeometryNodeFilletCurve", Count=6)
    fill = gn.node(
        t, "GeometryNodeFillCurve", Mode="N-gons"
    )  # tris extrude inner walls
    ext = gn.node(t, "GeometryNodeExtrudeMesh")
    cap = gn.node(t, "GeometryNodeFlipFaces")
    join = gn.node(t, "GeometryNodeJoinGeometry")
    merge = gn.node(
        t, "GeometryNodeMergeByDistance", Distance=1e-4
    )  # float noise at ~100s of units
    # cutter slightly taller at the start so an open pocket from the back face cuts clean
    eps = gn.node(t, "ShaderNodeMath", props={"operation": "SUBTRACT"})
    eps.inputs[1].default_value = 1e-4
    grow = gn.node(t, "ShaderNodeMath", props={"operation": "ADD"})
    grow.inputs[1].default_value = 1e-4
    xyz = gn.node(t, "ShaderNodeCombineXYZ")
    sep = gn.node(t, "ShaderNodeSeparateXYZ")
    move = gn.node(t, "GeometryNodeTransform")
    boolean = gn.node(
        t,
        "GeometryNodeMeshBoolean",
        props={"operation": "DIFFERENCE", "solver": "EXACT"},
    )  # the 5.x default solver mangles this cut
    gn.link(t, gin, "Pocket Width", quad, "Width")
    gn.link(t, gin, "Pocket Height", quad, "Height")
    gn.link(t, quad, "Curve", fillet, "Curve")
    gn.link(t, gin, "Pocket Corner Radius", fillet, "Radius")
    gn.link(t, fillet, "Curve", fill, "Curve")
    gn.link(t, fill, "Mesh", ext, "Mesh")
    gn.link(t, gin, "Pocket Depth", grow, 0)
    gn.link(t, grow, "Value", ext, "Offset Scale")
    gn.link(t, fill, "Mesh", cap, "Mesh")
    gn.link(t, ext, "Mesh", join, "Geometry")
    gn.link(t, cap, "Mesh", join, "Geometry")
    gn.link(t, join, "Geometry", merge, "Geometry")
    gn.link(t, gin, "Pocket Center", sep, "Vector")
    gn.link(t, gin, "Pocket Bottom", eps, 0)
    gn.link(t, sep, "X", xyz, "X")
    gn.link(t, sep, "Y", xyz, "Y")
    gn.link(t, eps, "Value", xyz, "Z")
    gn.link(t, merge, "Geometry", move, "Geometry")
    gn.link(t, xyz, "Vector", move, "Translation")
    gn.link(t, gin, "Geometry", boolean, "Mesh 1")
    gn.link(t, move, "Geometry", boolean, "Mesh 2")
    gn.link(t, boolean, "Mesh", gout, "Geometry")
    gn.arrange(t)
    gn.stamp(t, __file__)
    return t


def apply(obj, **inputs):
    return gn.modifier(obj, build(), **inputs)
