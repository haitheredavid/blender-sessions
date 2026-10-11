"""GN_FrameLoft: a picture frame lofted from a freeform outline into a rectangular opening.

The outer edge follows a Control curve (reshape it by hand) plus a parametric inward bow
per side (Sag, Tip Shape) and an optional hand-drawn wobble (Wobble, Seed); the face slopes from a thin outer edge (Edge Height) up to the
sight opening (Depth), shaped by Face Power (1 linear, >1 cove, <1 convex); behind the
opening a rabbet (Rabbet Width/Height/Depth) seats glazing, art and backboard.

Every ring has 4 x Samples points starting at the top-right corner and running CCW, so
sample i of the outline corresponds to sample i of each rectangle: the corner tips run
straight to the opening corners as hip lines. The outline ring is a rectangle (the
Control curve's bounding box) projected onto the curve (nearest point), then bowed.
Rings are bridged in a loop (outer wall, face, sightwell, ledge, rabbet wall, back) and
merged into one watertight mesh.

Control curve: closed, roughly rectangular, in XY, centred near the origin.
"""

from kit import gn

NAME = "GN_FrameLoft"
BAND = "GN_LoftBand"


def _math(t, op, a=None, b=None, a_out=0, b_out=0, value=None):
    n = gn.node(t, "ShaderNodeMath", props={"operation": op})
    if a is not None:
        gn.link(t, a, a_out, n, 0)
    if b is not None:
        gn.link(t, b, b_out, n, 1)
    if value is not None:
        n.inputs[1].default_value = value
    return n


def _vmath(t, op, a, b=None, a_out=0, b_out=0, scale=None):
    n = gn.node(t, "ShaderNodeVectorMath", props={"operation": op})
    gn.link(t, a, a_out, n, 0)
    if b is not None:
        gn.link(t, b, b_out, n, 1)
    if scale is not None:
        gn.link(t, scale[0], scale[1], n, "Scale")
    return n


def _sample(t, ring, ring_out, index, index_out=0):
    """Position of point `index` of a ring (wrapping)."""
    pos = gn.node(t, "GeometryNodeInputPosition")
    s = gn.node(
        t,
        "GeometryNodeSampleIndex",
        props={"data_type": "FLOAT_VECTOR", "domain": "POINT", "clamp": False},
    )
    gn.link(t, ring, ring_out, s, "Geometry")
    gn.link(t, pos, "Position", s, "Value")
    gn.link(t, index, index_out, s, "Index")
    return s


def build_band(reset: bool = False):
    """GN_LoftBand: Rows x (count+1) grid between two equal-count rings, Z shaped by
    Power; the extra column closes the loop and is merged by the caller."""
    t = gn.tree(BAND)
    if gn.current(t, __file__) and not reset:
        return t
    t = gn.tree(BAND, reset=True)
    t.is_modifier = False
    gn.input(t, "Ring A", "GEOMETRY")
    gn.input(t, "Ring B", "GEOMETRY")
    gn.input(t, "Z A", "FLOAT", 0.0)
    gn.input(t, "Z B", "FLOAT", 1.0)
    gn.input(t, "Rows", "INT", 2, min=2)
    gn.input(t, "Power", "FLOAT", 1.0, min=0.01)
    gn.output(t, "Mesh")
    gin, gout = gn.io(t)

    with gn.stage(t, "1 · Grid (count+1 × rows)"):
        size = gn.node(
            t, "GeometryNodeAttributeDomainSize", props={"component": "POINTCLOUD"}
        )
        gn.link(t, gin, "Ring A", size, "Geometry")
        cols = _math(t, "ADD", size, a_out="Point Count", value=1.0)
        grid = gn.node(t, "GeometryNodeMeshGrid", Size_X=1.0, Size_Y=1.0)
        gn.link(t, cols, "Value", grid, "Vertices X")
        gn.link(t, gin, "Rows", grid, "Vertices Y")

    with gn.stage(t, "2 · Column / row from index"):
        idx = gn.node(t, "GeometryNodeInputIndex")
        col = _math(
            t, "FLOORED_MODULO",
            _math(t, "FLOOR", _math(t, "DIVIDE", idx, gin, b_out="Rows")),
            size, b_out="Point Count",
        )  # fmt: skip
        row = _math(t, "FLOORED_MODULO", idx, gin, b_out="Rows")
        f = _math(t, "DIVIDE", row, _math(t, "SUBTRACT", gin, a_out="Rows", value=1.0))
    with gn.stage(t, "3 · Sample rings + lerp"):
        a = _sample(t, gin, "Ring A", col)
        b = _sample(t, gin, "Ring B", col)
        ab = _vmath(t, "SUBTRACT", b, a)
        xy = _vmath(t, "ADD", a, _vmath(t, "SCALE", ab, scale=(f, "Value")))
        sep = gn.node(t, "ShaderNodeSeparateXYZ")
        gn.link(t, xy, 0, sep, "Vector")
    with gn.stage(t, "4 · Z profile (Power)"):
        shaped = _math(t, "POWER", f, gin, b_out="Power")
        dz = _math(t, "SUBTRACT", gin, gin, a_out="Z B", b_out="Z A")
        z = _math(t, "ADD", gin, _math(t, "MULTIPLY", dz, shaped), a_out="Z A")
    with gn.stage(t, "5 · Position"):
        pos = gn.node(t, "ShaderNodeCombineXYZ")
        gn.link(t, sep, "X", pos, "X")
        gn.link(t, sep, "Y", pos, "Y")
        gn.link(t, z, "Value", pos, "Z")
        setp = gn.node(t, "GeometryNodeSetPosition")
        gn.link(t, grid, "Mesh", setp, "Geometry")
        gn.link(t, pos, "Vector", setp, "Position")
    gn.link(t, setp, "Geometry", gout, "Mesh")
    gn.arrange(t)
    gn.stamp(t, __file__)
    return t


def _rect_ring(t, gin, width, height, w_out, h_out):
    """4 x Samples points on a W x H rectangle, top-right corner first, CCW."""
    quad = gn.node(t, "GeometryNodeCurvePrimitiveQuadrilateral")
    gn.link(t, width, w_out, quad, "Width")
    gn.link(t, height, h_out, quad, "Height")
    cuts = _math(t, "SUBTRACT", gin, a_out="Samples", value=1.0)
    sub = gn.node(t, "GeometryNodeSubdivideCurve")
    gn.link(t, quad, "Curve", sub, "Curve")
    gn.link(t, cuts, "Value", sub, "Cuts")
    pts = gn.node(t, "GeometryNodeCurveToPoints", props={"mode": "EVALUATED"})
    gn.link(t, sub, "Curve", pts, "Curve")
    return pts


def build(reset: bool = False):
    t = gn.tree(NAME)
    if gn.current(t, __file__) and not reset:
        return t
    band = build_band(reset)
    t = gn.tree(NAME, reset=True)
    gn.input(t, "Geometry", "GEOMETRY")
    gn.input(t, "Outline", "OBJECT", description="Closed Control curve: the outer edge")
    gn.input(
        t, "Sag", "FLOAT", 12.0, subtype="DISTANCE", description="Inward bow mid-side"
    )
    gn.input(
        t, "Tip Shape", "FLOAT", 0.7, min=0.05, description="<1 horn tips, >1 soft"
    )
    gn.input(
        t, "Wobble", "FLOAT", 0.0, min=0.0, subtype="DISTANCE",
        description="Hand-drawn wiggle along each side (0 at the tips)",
    )  # fmt: skip
    gn.input(t, "Seed", "INT", 3, description="Wobble pattern")
    gn.input(t, "Edge Height", "FLOAT", 12.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Depth", "FLOAT", 40.0, min=0.0, subtype="DISTANCE")
    gn.input(
        t,
        "Face Power",
        "FLOAT",
        1.0,
        min=0.05,
        description="1 linear, >1 cove, <1 convex",
    )
    gn.input(t, "Sight Width", "FLOAT", 200.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Sight Height", "FLOAT", 280.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Rabbet Width", "FLOAT", 210.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Rabbet Height", "FLOAT", 290.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Rabbet Depth", "FLOAT", 9.0, min=0.0, subtype="DISTANCE")
    gn.input(t, "Samples", "INT", 64, min=2, max=512, description="Points per side")
    gn.input(t, "Face Rings", "INT", 14, min=0, max=128)
    gn.input(t, "Material", "MATERIAL")
    gn.output(t, "Geometry")
    gin, gout = gn.io(t)

    with gn.stage(t, "1 · Outline ring (projected onto CTL curve)"):
        # outline ring: bounding-box rectangle of the Control curve, projected onto it
        info = gn.node(t, "GeometryNodeObjectInfo", "Outline")
        gn.link(t, gin, "Outline", info, "Object")
        bbox = gn.node(t, "GeometryNodeBoundBox")
        gn.link(t, info, "Geometry", bbox, "Geometry")
        span = _vmath(t, "SUBTRACT", bbox, bbox, a_out="Max", b_out="Min")
        centre = _vmath(
            t, "SCALE", _vmath(t, "ADD", bbox, bbox, a_out="Max", b_out="Min")
        )
        centre.inputs["Scale"].default_value = 0.5
        sep = gn.node(t, "ShaderNodeSeparateXYZ")
        gn.link(t, span, 0, sep, "Vector")
        base = _rect_ring(t, gin, sep, sep, "X", "Y")
        moved = gn.node(t, "GeometryNodeSetPosition")
        gn.link(t, base, "Points", moved, "Geometry")
        gn.link(t, centre, 0, moved, "Offset")
        edges = gn.node(t, "GeometryNodeCurveToMesh")
        gn.link(t, info, "Geometry", edges, "Curve")
        prox = gn.node(t, "GeometryNodeProximity", props={"target_element": "EDGES"})
        gn.link(t, edges, "Mesh", prox, "Geometry")
        onto = gn.node(t, "GeometryNodeSetPosition")
        gn.link(t, moved, "Geometry", onto, "Geometry")
        gn.link(t, prox, "Position", onto, "Position")

    with gn.stage(t, "2 · Bow: Sag × sin(πt)^Tip Shape"):
        # bow: inward (left of the CCW side direction) by Sag * sin(pi t)^Tip Shape
        idx = gn.node(t, "GeometryNodeInputIndex")
        within = _math(t, "FLOORED_MODULO", idx, gin, b_out="Samples")
        corner = _math(t, "SUBTRACT", idx, within)
        total = _math(t, "MULTIPLY", gin, a_out="Samples", value=4.0)
        nxt = _math(
            t, "FLOORED_MODULO", _math(t, "ADD", corner, gin, b_out="Samples"), total
        )
        c0 = _sample(t, moved, "Geometry", corner)
        c1 = _sample(t, moved, "Geometry", nxt)
        d = gn.node(t, "ShaderNodeSeparateXYZ")
        gn.link(t, _vmath(t, "SUBTRACT", c1, c0), 0, d, "Vector")
        inward = gn.node(t, "ShaderNodeCombineXYZ")
        gn.link(t, _math(t, "MULTIPLY", d, a_out="Y", value=-1.0), "Value", inward, "X")
        gn.link(t, d, "X", inward, "Y")
        frac = _math(t, "DIVIDE", within, gin, b_out="Samples")
        sine = _math(t, "SINE", _math(t, "MULTIPLY", frac, value=3.141592653589793))
        bow = _math(t, "MULTIPLY", gin, _math(t, "POWER", sine, gin, b_out="Tip Shape"),
                    a_out="Sag")  # fmt: skip
    with gn.stage(t, "3 · Wobble + offset outline"):
        # wobble: Wobble * sin(pi t) * sum(amp sin(f pi t + phase)) / 2, f = 2, 3, 5, with a
        # random amp/phase per side and harmonic (the bmesh frame_geo outline, ported)
        side = _math(t, "FLOOR", _math(t, "DIVIDE", idx, gin, b_out="Samples"))
        noise = None
        for k, freq in enumerate((2, 3, 5)):
            ident = _math(t, "MULTIPLY_ADD", side, value=3.0)
            ident.inputs[2].default_value = float(k)
            rnd = {}
            for key, lo, hi, salt in (
                ("phase", 0.0, 6.283185307179586, 0),
                ("amp", 0.5, 1.0, 97),
            ):
                r = gn.node(t, "FunctionNodeRandomValue", props={"data_type": "FLOAT"})
                r.inputs["Min"].default_value, r.inputs["Max"].default_value = lo, hi
                salted = _math(t, "ADD", ident, value=float(salt))
                gn.link(t, salted, "Value", r, "ID")
                gn.link(t, gin, "Seed", r, "Seed")
                rnd[key] = r
            arg = _math(t, "ADD", _math(t, "MULTIPLY", frac, value=freq * 3.141592653589793),
                        rnd["phase"], b_out="Value")  # fmt: skip
            term = _math(
                t, "MULTIPLY", _math(t, "SINE", arg), rnd["amp"], b_out="Value"
            )
            noise = term if noise is None else _math(t, "ADD", noise, term)
        wob = _math(
            t, "MULTIPLY", _math(t, "MULTIPLY", gin, sine, a_out="Wobble"), noise
        )
        half = _math(t, "MULTIPLY", wob, value=0.5)
        total = _math(t, "ADD", bow, half)
        offset = _vmath(
            t, "SCALE", _vmath(t, "NORMALIZE", inward), scale=(total, "Value")
        )
        outline = gn.node(t, "GeometryNodeSetPosition")
        gn.link(t, onto, "Geometry", outline, "Geometry")
        gn.link(t, offset, 0, outline, "Offset")

    with gn.stage(t, "4 · Sight + rabbet rings"):
        sight = _rect_ring(t, gin, gin, gin, "Sight Width", "Sight Height")
        rabbet = _rect_ring(t, gin, gin, gin, "Rabbet Width", "Rabbet Height")
        face_rows = _math(t, "ADD", gin, a_out="Face Rings", value=2.0)

    with gn.stage(t, "5 · Loft bands (wall, face, sightwell, ledge, rabbet, back)"):
        join = gn.node(t, "GeometryNodeJoinGeometry")
        # (ring A, z A, ring B, z B, rows, power): the cross-section loop, outside to back
        zero, edge, depth, rab = (
            (None, 0.0),
            (gin, "Edge Height"),
            (gin, "Depth"),
            (gin, "Rabbet Depth"),
        )
        bands = [
            (outline, zero, outline, edge, None, None),
            (outline, edge, sight, depth, face_rows, (gin, "Face Power")),
            (sight, depth, sight, rab, None, None),
            (sight, rab, rabbet, rab, None, None),
            (rabbet, rab, rabbet, zero, None, None),
            (rabbet, zero, outline, zero, None, None),
        ]
        for ra, za, rb, zb, rows, power in bands:
            g = gn.node(t, "GeometryNodeGroup")
            g.node_tree = band
            gn.link(t, ra, 0, g, "Ring A")
            gn.link(t, rb, 0, g, "Ring B")
            for sock, z in (("Z A", za), ("Z B", zb)):
                if z[0] is None:
                    g.inputs[sock].default_value = z[1]
                else:
                    gn.link(t, z[0], z[1], g, sock)
            if rows is not None:
                gn.link(t, rows, "Value", g, "Rows")
            if power is not None:
                gn.link(t, power[0], power[1], g, "Power")
            gn.link(t, g, "Mesh", join, "Geometry")
    with gn.stage(t, "6 · Merge + material"):
        merge = gn.node(t, "GeometryNodeMergeByDistance", Distance=1e-3)
        gn.link(t, join, "Geometry", merge, "Geometry")
        mat = gn.node(
            t, "GeometryNodeSetMaterial"
        )  # the band loop already winds outward
        gn.link(t, merge, "Geometry", mat, "Geometry")
        gn.link(t, gin, "Material", mat, "Material")
    gn.link(t, mat, "Geometry", gout, "Geometry")
    gn.arrange(t)
    gn.stamp(t, __file__)
    return t


def apply(obj, **inputs):
    return gn.modifier(obj, build(), **inputs)
