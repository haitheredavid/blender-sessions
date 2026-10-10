"""Materials. Nodes are found by type, never by name (names are localized)."""

import bpy


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(hex_color: str) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (*(srgb_to_linear(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4)), 1.0)


def bsdf(mat: bpy.types.Material) -> bpy.types.ShaderNode:
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def principled(
    name: str,
    color: str = "#B8B8B8",
    roughness: float = 0.5,
    metallic: float = 0.0,
) -> bpy.types.Material:
    """Get or create a Principled material. Colour goes on the node, not diffuse_color."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    node = bsdf(mat)
    node.inputs["Base Color"].default_value = rgba(color)
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = rgba(color)  # viewport solid-mode only
    return mat


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj
