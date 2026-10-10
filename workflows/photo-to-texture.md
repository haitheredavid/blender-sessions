# Photo to texture

Turn a handheld photo of a flat artwork or document into a flat, perspective-corrected texture at real size, and show it on a proxy in Blender. Use it to preview real art in a frame, a label on a product, or a decal from a photo.

## When to use
- You have a phone photo of a sheet on a cluttered background (couch, hand) and need it flat, cropped to the sheet edge, at known dimensions.

## Steps
1. **Copy the photo** to `refs/<slug>/` (gitignored).
2. **Load it into numpy inside Blender:** `img.pixels.foreach_get` gives a float array, bottom-up. Flip it to top-down rows.
3. **Build the sheet mask:**
   - Bright and low-saturation: `min > 0.62 and (max − min) < 0.2`.
   - Before picking thresholds, print a few pixel values from the background, skin and paper. Warm paper fails tight thresholds.
4. **Find the edges:**
   - For each scanline, walk in from the photo edge to the first white run ≥ 24 px. That is the sheet edge.
   - Never scan outward from the art: the artwork contains white too.
   - Fit a line per edge with iterative outlier rejection (fingers, glare), then intersect the lines for the corners.
5. **Warp:** build a homography from the output rectangle (real size × PPI, e.g. 9×12" at 200 ppi) to the corners, and sample bilinearly.
6. **Clean the border:** repaint saturated or dark pixels in the outer border strip (inside the sheet's white margin) with the median paper colour. This removes the holding thumb.
7. **Save and preview:**
   - Save the PNG with `file_format` read from the enum.
   - Look at a downscaled preview (`sips -Z 700`) and a crop of the border.
   - If detection fails, hand-set `CORNERS = [TL, TR, BR, BL]` in top-down pixel coords.
8. **Map it onto the proxy:**
   - Image Texture node with Generated coords, for Material Preview and renders.
   - **Plus planar UVs**, for the Solid viewport's Texture colour mode.

## bpy
```python
uv = obj.data.uv_layers.new(name="UVMap")
for loop in obj.data.loops:
    co = obj.data.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (co.x / w + 0.5, co.y / h + 0.5)
for a in bpy.context.screen.areas:
    if a.type == "VIEW_3D":
        a.spaces.active.shading.color_type = "TEXTURE"  # check the enum first
```
Reference: `models/wispy-witch-frame/builders/crop_art.py` (detection, homography, border cleanup) and `30_proxies.py` (material and UVs).

## Gotchas
- **Solid mode ignores Generated coords and shows the material's viewport colour.** It needs UVs plus `color_type = "TEXTURE"`.
- **A glass or glazing proxy over the art draws opaque in Solid mode.** Set its `display_type = "WIRE"` (viewport only; renders still use the material). Keep its alpha low, about 0.05, or the art reads milky.
- **`bpy.data.images.load` + `foreach_get` on a 12 MP photo is about 31M floats.** That's fine, but remove the datablock afterwards.

## Models
- wispy-witch-frame (2026-10-10): cropped the witch illustration photo to the 9×12" paper with its white border and showed it inside the frame.
