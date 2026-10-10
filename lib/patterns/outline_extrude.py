"""GN_OutlineExtrude: a closed Control curve filled and extruded into a solid.

Inputs: Outline (closed curve, read in ORIGINAL space: its shape, not its placement), Height, Taper (scale of
the top face; 1 = straight walls), Fillet (corner radius applied to the outline).
The base face is kept (flipped) so the result is closed and manifold.
"""

from kit import gn

NAME = "GN_OutlineExtrude"


def build(reset: bool = False):
    t = gn.tree(NAME)
    if t.nodes and not reset:
        return t
    t = gn.tree(NAME, reset=True)
    gn.input(t, "Geometry", "GEOMETRY")
    gn.input(t, "Outline", "OBJECT", description="Closed curve to fill")
    gn.input(t, "Height", "FLOAT", 1.0, subtype="DISTANCE")
    gn.input(t, "Taper", "FLOAT", 1.0, min=0.0, description="Top scale (1 = straight)")
    gn.input(t, "Fillet", "FLOAT", 0.0, min=0.0, subtype="DISTANCE")
    gn.output(t, "Geometry")
    gin, gout = gn.io(t)
    info = gn.node(t, "GeometryNodeObjectInfo", "Outline")
    fillet = gn.node(t, "GeometryNodeFilletCurve", Count=4)
    fill = gn.node(
        t, "GeometryNodeFillCurve", Mode="N-gons"
    )  # tris extrude inner walls
    ext = gn.node(t, "GeometryNodeExtrudeMesh")
    scale = gn.node(t, "GeometryNodeScaleElements")
    base = gn.node(t, "GeometryNodeFlipFaces")
    join = gn.node(t, "GeometryNodeJoinGeometry")
    merge = gn.node(
        t, "GeometryNodeMergeByDistance", Distance=1e-4
    )  # float noise at ~100s of units
    gn.link(t, gin, "Outline", info, "Object")
    gn.link(t, info, "Geometry", fillet, "Curve")
    gn.link(t, gin, "Fillet", fillet, "Radius")
    gn.link(t, fillet, "Curve", fill, "Curve")
    gn.link(t, fill, "Mesh", ext, "Mesh")
    gn.link(t, gin, "Height", ext, "Offset Scale")
    gn.link(t, ext, "Mesh", scale, "Geometry")
    gn.link(t, ext, "Top", scale, "Selection")
    gn.link(t, gin, "Taper", scale, "Scale")
    gn.link(t, fill, "Mesh", base, "Mesh")
    gn.link(t, scale, "Geometry", join, "Geometry")
    gn.link(t, base, "Mesh", join, "Geometry")
    gn.link(t, join, "Geometry", merge, "Geometry")
    gn.link(t, merge, "Geometry", gout, "Geometry")
    gn.arrange(t)
    return t


def apply(obj, **inputs):
    return gn.modifier(obj, build(), **inputs)
