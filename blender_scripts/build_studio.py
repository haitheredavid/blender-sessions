"""Build the render studio: a neutral cyclorama sweep, three-point lighting and a camera.

Usage: blender -b --factory-startup -P build_studio.py -- --save assets/studio.blend --result r.json

Everything lives in scene `blend_studio` (collection `studio`), sized for a model about
1 unit across, resting on the floor at z=0 and centred on the origin. render_studio.py
appends the scene, scales the collection to the model and fits the camera. The default
angle lives in the scene's custom props blend_azimuth / blend_elevation; tweak the look by
opening the saved .blend by hand.
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bpy
from _common import parse, write_result
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument("--save", required=True)
opts = parse(parser)

AZIMUTH, ELEVATION = -60.0, 22.0
RADIUS = (
    0.5  # reference model half-size; render_studio scales the studio by model/RADIUS
)

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

sc = bpy.context.scene
sc.name = "blend_studio"
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
sc["blend_azimuth"] = AZIMUTH
sc["blend_elevation"] = ELEVATION
sc["blend_radius"] = RADIUS

coll = bpy.data.collections.new("studio")
sc.collection.children.link(coll)


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(hex_color: str) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (*(srgb_to_linear(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4)), 1.0)


def link(name: str, data) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    return obj


# --- cyclorama: floor curving up into a wall behind (+Y) ---------------------
WIDTH, FRONT, CURVE_Y, R, HEIGHT = 12.0, -7.0, 1.5, 1.5, 7.0
profile = [(FRONT, 0.0), (CURVE_Y, 0.0)]
for i in range(1, 24):
    a = math.radians(90 * i / 24)
    profile.append((CURVE_Y + R * math.sin(a), R * (1 - math.cos(a))))
profile += [(CURVE_Y + R, R), (CURVE_Y + R, HEIGHT)]
verts = [(x, y, z) for y, z in profile for x in (-WIDTH / 2, WIDTH / 2)]
faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(profile) - 1)]
cyc_me = bpy.data.meshes.new("studio_cyclorama")
cyc_me.from_pydata(verts, [], faces)
cyc_me.shade_smooth()
cyc_mat = bpy.data.materials.new("studio_backdrop")
cyc_mat.use_nodes = True
bsdf = next(n for n in cyc_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = rgb("#9EA0A4")
bsdf.inputs["Roughness"].default_value = 0.9
cyc_mat.diffuse_color = rgb("#9EA0A4")
cyc_me.materials.append(cyc_mat)
link("studio_cyclorama", cyc_me)


# --- lights + camera ---------------------------------------------------------
def orbit(az: float, el: float, dist: float, center: Vector) -> Vector:
    a, e = math.radians(az), math.radians(el)
    return center + dist * Vector(
        (math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))
    )


def aim(obj, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


target = Vector((0, 0, RADIUS))
for name, az, el, power, color, size in (
    ("studio_key", AZIMUTH + 40, 45, 1.0, (1, 0.93, 0.85), 1.2),
    ("studio_rim", AZIMUTH + 180, 35, 1.2, (0.7, 0.8, 1), 0.8),
    ("studio_fill", AZIMUTH - 70, 15, 0.35, (1, 1, 1), 2.0),
):
    light = bpy.data.lights.new(name, "AREA")
    dist = RADIUS * 8
    light.energy = power * 11 * dist**2  # inverse-square: render_studio rescales by k^2
    light.color = color
    light.size = RADIUS * 2 * size
    obj = link(name, light)
    obj.location = orbit(az, el, dist, target)
    aim(obj, target)

cam_data = bpy.data.cameras.new("studio_cam")
cam_data.lens = 50
cam = link("studio_cam", cam_data)
cam.location = orbit(AZIMUTH, ELEVATION, RADIUS * 7, target)
aim(cam, target)
sc.camera = cam

world = bpy.data.worlds.new("studio_world")
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = rgb("#B4B6BA")
bg.inputs["Strength"].default_value = 0.25
sc.world = world

# --- render settings (render_studio.py renders with these) --------------------
engines = [i.identifier for i in sc.render.bl_rna.properties["engine"].enum_items]
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", *engines):
    try:
        sc.render.engine = engine
        break
    except TypeError:
        continue
sc.render.resolution_x = sc.render.resolution_y = 1000
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
try:
    sc.view_settings.view_transform = "AgX"
except TypeError:
    pass

Path(opts.save).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(opts.save).resolve()))
write_result(opts.result, {"saved": opts.save, "engine": sc.render.engine})
