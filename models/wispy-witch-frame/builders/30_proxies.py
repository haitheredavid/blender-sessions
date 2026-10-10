# Ref-only proxies (never exported): the rabbet stack (backboard, art, glazing) to judge
# fit and the sightwell shadow, and the user's sketch as an image empty. build_all doesn't
# clear Ref, so this step clears its own. The art face shows the cropped illustration
# (refs/wispy-witch-frame/illustration_crop.png, made by crop_art.py).
import sys
from pathlib import Path

import bpy
from kit import materials, mesh, scene

sys.path.insert(0, str(Path(__file__).parent))
import frame_geo

REFS = Path(__file__).parents[3] / "refs/wispy-witch-frame"

ref = scene.collection(scene.REF)
for name in ("Backboard_Proxy", "Art_Proxy", "Glazing_Proxy", "Sketch_Ref"):
    if (old := bpy.data.objects.get(name)) is not None:
        bpy.data.objects.remove(old, do_unlink=True)

bw, bh, bt = frame_geo.BACKBOARD
aw, ah = frame_geo.ART
gw, gh, gt = frame_geo.GLAZING
art_t = 0.3  # the paper, on the board's front face
z0 = frame_geo.CLIP_ZONE  # back of the stack
board = mesh.box(
    "Backboard_Proxy", (bw, bh, bt - art_t), (0, 0, z0 + (bt - art_t) / 2), ref
)
art = mesh.box("Art_Proxy", (aw, ah, art_t), (0, 0, z0 + bt - art_t / 2), ref)
glaze = mesh.box("Glazing_Proxy", (gw, gh, gt), (0, 0, z0 + bt + gt / 2), ref)
materials.assign(board, materials.principled("Proxy_Board", "#D9D2C3", roughness=0.9))

# art: the cropped photo on Generated coords (box bounds -> 0..1, so the top face maps 1:1)
art_mat = materials.principled("Proxy_Art", "#1C2A4A", roughness=0.8)
crop = REFS / "illustration_crop.png"
if crop.exists():
    nodes, links = art_mat.node_tree.nodes, art_mat.node_tree.links
    for n in [n for n in nodes if n.type in ("TEX_IMAGE", "TEX_COORD")]:
        nodes.remove(n)
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(crop), check_existing=True)
    coord = nodes.new("ShaderNodeTexCoord")
    links.new(coord.outputs["Generated"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], materials.bsdf(art_mat).inputs["Base Color"])
materials.assign(art, art_mat)
# planar UVs from XY too: Solid view's Texture colour mode reads UVs, not Generated coords
uv = art.data.uv_layers.new(name="UVMap")
for loop in art.data.loops:
    co = art.data.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (co.x / aw + 0.5, co.y / ah + 0.5)

# glazing: nearly clear; blended so the art reads through it in EEVEE and the viewport
glass = materials.principled("Proxy_Glazing", "#E8F0F4", roughness=0.05)
materials.bsdf(glass).inputs["Alpha"].default_value = 0.05
methods = [
    i.identifier
    for i in bpy.types.Material.bl_rna.properties["surface_render_method"].enum_items
]
glass.surface_render_method = "BLENDED" if "BLENDED" in methods else methods[0]
materials.assign(glaze, glass)
glaze.display_type = (
    "WIRE"  # viewport only: solid mode would draw it opaque over the art
)

sketch = REFS / "sketch.jpeg"
if sketch.exists():
    img = bpy.data.images.load(str(sketch), check_existing=True)
    emp = bpy.data.objects.new("Sketch_Ref", None)
    emp.empty_display_type = "IMAGE"
    emp.data = img
    emp.empty_display_size = 600
    emp.location = (-700, 0, 0)
    ref.objects.link(emp)
