"""Studio render (still or turntable) of the Model collection, for the session gallery.

Usage: blender -b model.blend -P render_studio.py -- --studio assets/studio.blend --out render.png
       [--framing fit|wide] [--scene NAME] [--size 800] [--azimuth DEG --elevation DEG]
       [--frames N --fps 30] [--upright] [--include COLL ...] [--zoom 1.0]
       [--target X Y Z] [--params JSON] --result r.json

Appends the `blend_studio` scene from studio.blend (build_studio.py), centres the model on
the floor (XY centred, lowest point at z=0), scales the studio to the model and fits the
camera. `fit` fills the frame with the model; `wide` pulls back to show the floor around it.
--frames N > 0 renders a 360° turntable instead: PNG frames to --out (a directory).
--upright stands the model up (+Z face turned toward -Y), e.g. a frame as it hangs on a
wall. --include adds visible meshes from other collections (e.g. Ref proxies). --zoom > 1
crops in on --target (a point in the model's original coordinates; default its centre).
--params sets GN modifier inputs on the model first ({"Depth": 60}, as in params.toml;
`blend variants` uses it). Objects without materials render a neutral grey. Never saves
the .blend.
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bpy
import numpy as np
from _common import collection_objects, model_objects, parse, write_result
from mathutils import Matrix, Vector

parser = argparse.ArgumentParser()
parser.add_argument("--studio", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--framing", choices=("fit", "wide"), default="fit")
parser.add_argument("--scene", default="")
parser.add_argument("--size", type=int, default=800)
parser.add_argument("--azimuth", type=float)
parser.add_argument("--elevation", type=float)
parser.add_argument("--frames", type=int, default=0)
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--upright", action="store_true")
parser.add_argument("--include", action="append", default=[])
parser.add_argument("--zoom", type=float, default=1.0)
parser.add_argument("--target", type=float, nargs=3)
parser.add_argument("--params", default="")
opts = parse(parser)

STUDIO_SCENE = "blend_studio"

src = bpy.data.scenes[opts.scene] if opts.scene else bpy.context.scene
objects = model_objects(src)
if not objects:
    raise SystemExit("no visible mesh objects in the Model collection")
for name in opts.include:
    objects += [o for o in collection_objects(name, src) if o not in objects]

unused_params = []
if opts.params:  # kit is bpy-only, so headless scripts may share it
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from kit import params as kit_params

    unused_params = kit_params.apply(json.loads(opts.params), objects)["unused"]

grey = None
for o in objects:
    if not any(s.material for s in o.material_slots):
        if grey is None:
            grey = bpy.data.materials.new("studio_grey")
            grey.use_nodes = True
            bsdf = next(n for n in grey.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Base Color"].default_value = (0.45, 0.45, 0.45, 1)
            bsdf.inputs["Roughness"].default_value = 0.55
        o.data.materials.clear()
        o.data.materials.append(grey)

with bpy.data.libraries.load(opts.studio, link=False) as (lib, data):
    if STUDIO_SCENE not in lib.scenes:
        raise SystemExit(f"{opts.studio} has no scene {STUDIO_SCENE!r}")
    data.scenes = [STUDIO_SCENE]
sc = data.scenes[0]

# Parent every model root to a pivot so the turntable spins the whole model.
pivot = bpy.data.objects.new("studio_pivot", None)
sc.collection.objects.link(pivot)
for o in objects:
    sc.collection.objects.link(o)
roots = [o for o in objects if o.parent not in objects]
studio_layer = sc.view_layers[0]


def world_points(objs) -> np.ndarray:
    """Evaluated vertices in world space, (N, 3); framing on real geometry, not bboxes."""
    studio_layer.update()  # a non-active scene's transforms aren't evaluated on load
    dg = studio_layer.depsgraph
    chunks = [np.zeros((0, 3))]
    for o in objs:
        e = o.evaluated_get(dg)
        co = np.empty(len(e.data.vertices) * 3)
        e.data.vertices.foreach_get("co", co)
        m = np.array(e.matrix_world)
        chunks.append(co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3])
    return np.concatenate(chunks)


# Every placement below applies to the target too, so track it as a world-space point.
target = Vector(opts.target) if opts.target else None
if opts.upright:
    stand = Matrix.Rotation(
        math.radians(90), 4, "X"
    )  # +Z face -> -Y (toward the front)
    for o in roots:
        o.matrix_world = stand @ o.matrix_world
    target = stand @ target if target else None

# centre on the floor: XY centred, lowest point at z=0
pts = world_points(objects)
lo, hi = pts.min(0), pts.max(0)
shift = Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
for o in roots:
    o.matrix_world = shift @ o.matrix_world
target = shift @ target if target else None
for o in roots:
    mw = o.matrix_world.copy()
    o.parent = pivot
    o.matrix_world = mw
pts = world_points(objects)
size = pts.max(0) - pts.min(0)

# Scale the model (via the pivot) to the studio's reference size rather than scaling the
# studio up: EEVEE lighting breaks when lights are scaled by large factors (mm models).
radius = max(float(np.linalg.norm(size)) / 2, 1e-4)
model_size = size
k = radius / sc.get("blend_radius", 0.5)
pivot.scale = (1 / k,) * 3
target = target / k if target else None
pts = world_points(objects)
size = pts.max(0) - pts.min(0)
radius = max(float(np.linalg.norm(size)) / 2, 1e-4)

if opts.frames > 0:
    # sample the frame across the whole spin so nothing leaves it mid-turn
    r_xy = float(np.max(np.linalg.norm(pts[:, :2], axis=1)))
    ring = [
        (r_xy * math.cos(a), r_xy * math.sin(a), z)
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)
        for z in (pts[:, 2].min(), pts[:, 2].max())
    ]
    frame_pts = np.array(ring)
else:
    frame_pts = pts
if opts.framing == "wide":
    floor = np.array(
        [
            (x, y, 0)
            for x in (-2 * radius, 2 * radius)
            for y in (-2 * radius, 2 * radius)
        ]
    )
    frame, fill = np.concatenate([floor, frame_pts]), 0.92
else:
    frame, fill = frame_pts, 0.82
if opts.zoom > 1:
    # frame only the geometry within radius/zoom of the target (a cube, so thin axes
    # don't crop the subject)
    focus = np.array(target) if target else (pts.min(0) + pts.max(0)) / 2
    half = radius / opts.zoom
    near = pts[np.all(np.abs(pts - focus) <= half, axis=1)]
    frame, fill = (near if len(near) else focus[None, :]), 0.82
center = Vector((frame.min(0) + frame.max(0)) / 2)

azimuth = opts.azimuth if opts.azimuth is not None else sc.get("blend_azimuth", -60.0)
elevation = (
    opts.elevation if opts.elevation is not None else sc.get("blend_elevation", 22.0)
)


def orbit(az: float, el: float, dist: float) -> Vector:
    a, e = math.radians(az), math.radians(el)
    return center + dist * Vector(
        (math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))
    )


cam = sc.camera
cam_data = cam.data
cam_data.clip_start = radius * 0.01
cam_data.clip_end = radius * 1000
tan_half = cam_data.sensor_width / (2 * cam_data.lens)  # square frame: same both ways

# Project the frame points, centre with lens shift and scale the distance until they
# fill FILL of the frame. Perspective makes it nonlinear, so iterate.
dist = radius / tan_half
for _ in range(8):
    cam.location = orbit(azimuth, elevation, dist)
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    view = np.array(cam.matrix_basis.inverted())
    p = frame @ view[:3, :3].T + view[:3, 3]
    us, vs = p[:, 0] / -p[:, 2] / tan_half, p[:, 1] / -p[:, 2] / tan_half
    cam_data.shift_x = (
        us.min() + us.max()
    ) / 4  # shift is in frame widths; ndc spans 2
    cam_data.shift_y = (vs.min() + vs.max()) / 4
    extent = max(us.max() - us.min(), vs.max() - vs.min()) / 2
    dist *= float(extent) / fill

sc.render.resolution_x = sc.render.resolution_y = opts.size
out = Path(opts.out).resolve()
if opts.frames > 0:
    sc.frame_start, sc.frame_end = 1, opts.frames
    sc.render.fps = opts.fps
    # a simple-expression driver (no Python auto-exec needed); frame N sits one step
    # short of 360° so the loop doesn't repeat a frame
    drv = pivot.driver_add("rotation_euler", 2).driver
    drv.type = "SCRIPTED"
    drv.expression = f"2 * pi * (frame - 1) / {opts.frames}"
    out.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out / "f####")
    bpy.ops.render.render(animation=True, scene=sc.name)
else:
    out.parent.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out)
    bpy.ops.render.render(write_still=True, scene=sc.name)

write_result(
    opts.result,
    {
        "out": str(out),
        "objects": len(objects),
        "unused_params": unused_params,
        "engine": sc.render.engine,
        "framing": opts.framing,
        "frames": opts.frames,
        "fps": opts.fps,
        "size": [round(float(v), 4) for v in model_size],
    },
)
