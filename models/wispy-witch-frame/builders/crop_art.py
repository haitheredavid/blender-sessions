# One-off (no NN_ prefix, so build_all skips it): perspective-crop the illustration photo to
# the paper's edge, keeping the white border, and save a flat 9x12 texture for Art_Proxy.
#   exec(open(bpy.path.abspath("//builders/crop_art.py")).read(), {"__file__": ...})
# Paper = bright, low-saturation pixels; each edge is a line fitted to the first long white
# run scanning in from the photo edge, and corners are line intersections. CORNERS
# can be set by hand (top-down pixel coords: TL, TR, BR, BL) if detection is off.
from pathlib import Path

import bpy
import numpy as np

REFS = Path(__file__).parents[3] / "refs/wispy-witch-frame"
SRC, DST = REFS / "illustration.jpg", REFS / "illustration_crop.png"
PPI = 200  # output resolution: 9x12" -> 1800 x 2400
CORNERS = None


def load_rgb(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3]  # top-down rows


def _edge_hits(white, lines, from_end, run=24):
    """Per scanline, walking in from the photo's edge (the far end if from_end): the first
    pixel of a white run at least `run` long, i.e. the paper's outer edge. Couch and hand
    pixels aren't white; short bright specks are skipped."""
    hits = []
    for i, line in lines:
        seq = line[::-1] if from_end else line
        c = np.convolve(seq.astype(np.int32), np.ones(run, np.int32), "valid")
        idx = np.flatnonzero(c == run)
        if len(idx):
            j = idx[0]
            hits.append((i, len(line) - 1 - j if from_end else j))
    return np.array(hits, float)


def _fit(hits):
    """Robust line pos = a*i + b (refit after dropping outliers: hand, couch, glare)."""
    i, p = hits[:, 0], hits[:, 1]
    keep = np.ones(len(i), bool)
    for _ in range(3):
        a, b = np.polyfit(i[keep], p[keep], 1)
        r = np.abs(p - (a * i + b))
        keep = r <= max(3 * np.median(r[keep]), 2.0)
    return a, b


def paper_corners(rgb):
    lo, hi = rgb.min(2), rgb.max(2)
    white = (lo > 0.62) & (hi - lo < 0.2)  # warm paper; couch lo~0.35, hand spread~0.3
    h, w = white.shape
    rows = range(int(h * 0.1), int(h * 0.9), 8)
    cols = range(int(w * 0.15), int(w * 0.85), 8)
    left = _fit(_edge_hits(white, [(y, white[y]) for y in rows], False))
    right = _fit(_edge_hits(white, [(y, white[y]) for y in rows], True))
    top = _fit(_edge_hits(white, [(x, white[:, x]) for x in cols], False))
    bottom = _fit(_edge_hits(white, [(x, white[:, x]) for x in cols], True))

    def meet(vert, horiz):  # x = a*y + b  and  y = c*x + d
        (a, b), (c, d) = vert, horiz
        y = (c * b + d) / (1 - a * c)
        return a * y + b, y

    return np.array(
        [meet(left, top), meet(right, top), meet(right, bottom), meet(left, bottom)]
    )


def homography(dst, src):
    """3x3 H with H @ (u, v, 1) ~ (x, y, 1), from 4 point pairs."""
    a = []
    for (u, v), (x, y) in zip(dst, src):
        a.append([u, v, 1, 0, 0, 0, -u * x, -v * x, -x])
        a.append([0, 0, 0, u, v, 1, -u * y, -v * y, -y])
    _, _, vt = np.linalg.svd(np.array(a))
    return vt[-1].reshape(3, 3)


rgb = load_rgb(SRC)
corners = np.array(CORNERS, float) if CORNERS else paper_corners(rgb)
ow, oh = 9 * PPI, 12 * PPI
H = homography([(0, 0), (ow - 1, 0), (ow - 1, oh - 1), (0, oh - 1)], corners)
u, v = np.meshgrid(np.arange(ow), np.arange(oh))
p = H @ np.stack([u.ravel(), v.ravel(), np.ones(u.size)])
x = np.clip(p[0] / p[2], 0, rgb.shape[1] - 1.001)
y = np.clip(p[1] / p[2], 0, rgb.shape[0] - 1.001)
x0, y0 = x.astype(int), y.astype(int)
fx, fy = (x - x0)[:, None], (y - y0)[:, None]
out = (
    rgb[y0, x0] * (1 - fx) * (1 - fy)
    + rgb[y0, x0 + 1] * fx * (1 - fy)
    + rgb[y0 + 1, x0] * (1 - fx) * fy
    + rgb[y0 + 1, x0 + 1] * fx * fy
).reshape(oh, ow, 3)

# The holder's thumb overlaps the left border: within the outer 0.35" (inside the ~0.5"
# white border, clear of the painting), repaint saturated pixels with the median paper.
strip = int(0.35 * PPI)
border = np.zeros((oh, ow), bool)
border[:strip], border[-strip:], border[:, :strip], border[:, -strip:] = (True,) * 4
spread = out.max(2) - out.min(2)
paper = np.median(out[border & (spread < 0.2)], axis=0)
out[border & ((spread > 0.2) | (out.min(2) < 0.55))] = paper

rgba = np.concatenate([out, np.ones((oh, ow, 1), np.float32)], 2)[::-1]
img = bpy.data.images.new("illustration_crop", ow, oh)
img.pixels.foreach_set(rgba.astype(np.float32).ravel())
formats = [
    i.identifier for i in bpy.types.Image.bl_rna.properties["file_format"].enum_items
]
img.file_format = "PNG" if "PNG" in formats else formats[0]
img.filepath_raw = str(DST)
img.save()
bpy.data.images.remove(img)
print("crop corners (TL, TR, BR, BL):", corners.round().tolist(), "->", DST.name)
