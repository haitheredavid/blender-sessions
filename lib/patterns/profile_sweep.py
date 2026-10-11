"""GN_ProfileSweep: sweep a profile curve along a path curve (frames, mouldings, rims).

Inputs: Path (Control curve), Profile (Control curve: X across the path, Y up), Scale,
Fill Caps (open paths), Smooth. Curves are read in ORIGINAL space: their point shapes
drive the result, and the host object's transform places it (so variant copies can move).
"""

from kit import gn

NAME = "GN_ProfileSweep"


def build(reset: bool = False):
    t = gn.tree(NAME)
    if gn.current(t, __file__) and not reset:
        return t
    t = gn.tree(NAME, reset=True)
    gn.input(t, "Geometry", "GEOMETRY")
    gn.input(t, "Path", "OBJECT", description="Curve the profile follows")
    gn.input(t, "Profile", "OBJECT", description="Cross-section curve (X out, Y up)")
    gn.input(t, "Scale", "FLOAT", 1.0, min=0.0)
    gn.input(t, "Fill Caps", "BOOL", False)
    gn.input(t, "Smooth", "BOOL", False)
    gn.output(t, "Geometry")
    gin, gout = gn.io(t)
    path = gn.node(t, "GeometryNodeObjectInfo", "Path")
    prof = gn.node(t, "GeometryNodeObjectInfo", "Profile")
    sweep = gn.node(t, "GeometryNodeCurveToMesh")
    smooth = gn.node(t, "GeometryNodeSetShadeSmooth")
    gn.link(t, gin, "Path", path, "Object")
    gn.link(t, gin, "Profile", prof, "Object")
    gn.link(t, path, "Geometry", sweep, "Curve")
    gn.link(t, prof, "Geometry", sweep, "Profile Curve")
    gn.link(t, gin, "Scale", sweep, "Scale")
    gn.link(t, gin, "Fill Caps", sweep, "Fill Caps")
    gn.link(t, sweep, "Mesh", smooth, "Mesh")
    gn.link(t, gin, "Smooth", smooth, "Shade Smooth")
    gn.link(t, smooth, "Mesh", gout, "Geometry")
    gn.arrange(t)
    gn.stamp(t, __file__)
    return t


def apply(obj, **inputs):
    return gn.modifier(obj, build(), **inputs)
