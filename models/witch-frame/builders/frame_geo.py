"""Parametric wispy-witch frame: one watertight ring sweep (units: mm, 1 BU = 1 mm).

Every ring has the same vertex count (4 sides x N samples, corners shared), and sample i on
the outer outline corresponds to sample i on each inner rectangle, so the corner tips run
straight to the opening corners as hip lines. Rings, bridged cyclically:

    outline z=0 -> outline z=h_outer -> face rings (slope) -> sight rect z=H
    -> sight rect z=rabbet -> rabbet rect z=rabbet -> rabbet rect z=0 -> (outline z=0)
"""

import math
import random

import bmesh
from mathutils import Vector

IN = 25.4
ART = (9 * IN, 12 * IN)  # the paper, white border included
BACKBOARD = (9 * IN, 12 * IN, 3.0)  # cut to the art's size so it never shows
GLAZING = (9 * IN, 12 * IN, 2.0)  # acrylic in front of the art, same size
CLIP_ZONE = 4.0  # behind the stack: turn clips live here (z 0..4)
OVERLAP = IN / 8  # sight opening overlaps the art per side
CLEAR = 0.5  # rabbet clearance per side around the stack

DEFAULTS = {
    "width": 11 * IN,  # tip-to-tip
    "height": 14 * IN,  # tip-to-tip
    "sag": 12.0,  # inward bow of each side at mid-span
    "k": 0.7,  # bow shape: <1 sharp horn tips, flat middle; >1 soft tips
    "wobble": 0.0,  # hand-drawn noise amplitude (mm)
    "seed": 3,
    "depth": 40.0,  # total depth H at the sight opening
    "h_outer": 12.0,  # thin outer edge height (must clear the rabbet)
    "profile": "linear",  # linear | cove | convex
    "profile_pow": 1.8,
    "rabbet": CLIP_ZONE + BACKBOARD[2] + GLAZING[2],  # 9: glazing + art/board + clips
    "min_wall": 6.0,
    "n": 64,  # samples per side
    "m": 14,  # face rings
}


def sight_size():
    return ART[0] - 2 * OVERLAP, ART[1] - 2 * OVERLAP


def rabbet_size():
    w = max(BACKBOARD[0], GLAZING[0], ART[0])
    h = max(BACKBOARD[1], GLAZING[1], ART[1])
    return w + 2 * CLEAR, h + 2 * CLEAR


def _rect_ring(w, h, n):
    """Corners CCW from (-w/2,-h/2); n samples per side, corners shared."""
    c = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = []
    for s in range(4):
        a, b = Vector(c[s]), Vector(c[(s + 1) % 4])
        pts += [a.lerp(b, j / n) for j in range(n)]
    return pts


def outline(p):
    """Outer outline: tip-to-tip sides bowed inward by sag*sin(pi t)^k (+ optional wobble)."""
    w, h, n = p["width"], p["height"], p["n"]
    base = _rect_ring(w, h, n)
    rng = random.Random(p["seed"])
    pts = []
    for s in range(4):
        a, b = base[s * n], base[((s + 1) % 4) * n]
        d = (b - a).normalized()
        inward = Vector((-d.y, d.x))  # CCW ring: left of travel is inside
        span = (b - a).length
        ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]
        amp = [rng.uniform(0.5, 1.0) for _ in range(3)]
        for j in range(n):
            t = j / n
            bow = math.sin(math.pi * t) ** p["k"]
            off = p["sag"] * bow
            if p["wobble"]:
                env = math.sin(math.pi * t)
                noise = sum(
                    am * math.sin(f * math.pi * t + phi)
                    for f, am, phi in zip((2, 3, 5), amp, ph)
                )
                off += p["wobble"] * env * noise / 2.0
            pts.append(a + d * (span * t) + inward * off)
    return pts


def _rect_clearance(pt, w, h):
    """Signed distance from pt to the outside of an axis rect (negative = inside)."""
    dx, dy = abs(pt.x) - w / 2, abs(pt.y) - h / 2
    if dx > 0 and dy > 0:
        return math.hypot(dx, dy)
    return max(dx, dy)


def validate(p):
    out = outline(p)
    rw, rh = rabbet_size()
    wall = min(_rect_clearance(v, rw, rh) for v in out)
    assert wall >= p["min_wall"], f"wall {wall:.2f} < {p['min_wall']} (reduce sag)"
    assert p["width"] <= 12 * IN + 1e-6 and p["height"] <= 15 * IN + 1e-6, "too big"
    assert p["h_outer"] > p["rabbet"] + 2, "outer edge too thin over clip pockets"
    return wall


def _face_height(p, s):
    q = p["profile_pow"]
    g = {"linear": s, "cove": s**q, "convex": 1 - (1 - s) ** q}[p["profile"]]
    return p["h_outer"] + (p["depth"] - p["h_outer"]) * g


def build_bmesh(p):
    n, m = p["n"], p["m"]
    out = outline(p)
    sw, sh = sight_size()
    rw, rh = rabbet_size()
    sight = _rect_ring(sw, sh, n)
    rab = _rect_ring(rw, rh, n)
    R = p["rabbet"]

    rings = [[(v.x, v.y, 0.0) for v in out]]
    for i in range(m + 1):
        s = i / m
        z = _face_height(p, s)
        rings.append([(*a.lerp(b, s), z) for a, b in zip(out, sight)])
    rings.append([(v.x, v.y, R) for v in sight])
    rings.append([(v.x, v.y, R) for v in rab])
    rings.append([(v.x, v.y, 0.0) for v in rab])

    bm = bmesh.new()
    vr = [[bm.verts.new(c) for c in ring] for ring in rings]
    k = len(rings[0])
    for r in range(len(vr)):
        A, B = vr[r], vr[(r + 1) % len(vr)]
        for j in range(k):
            j2 = (j + 1) % k
            bm.faces.new((A[j], A[j2], B[j2], B[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # smooth the face slope and the bowed outer wall; keep crisp creases
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            e.smooth = a.normal.angle(b.normal) < math.radians(35)
    return bm


def params(**over):
    p = dict(DEFAULTS)
    p.update(over)
    return p
