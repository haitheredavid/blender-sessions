"""Variant grids: renders of each params variant composited into one labelled image."""

from pathlib import Path

from PIL import Image, ImageDraw

from blend.gallery import _font

BG = (24, 25, 28)
FG = (232, 232, 235)


def compose(cells: list[tuple[str, Path]], out: Path, columns: int = 3) -> Path:
    """Lay cells out left-to-right, top-to-bottom, each captioned with its label.
    Cells are scaled to the first image's size."""
    if not cells:
        raise ValueError("no images to compose")
    images = [Image.open(p).convert("RGB") for _, p in cells]
    w, h = images[0].size
    cap = max(24, h // 12)
    cols = max(1, min(columns, len(cells)))
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + cap)), BG)
    draw = ImageDraw.Draw(sheet)
    font = _font(int(cap * 0.6))
    for i, ((label, _), img) in enumerate(zip(cells, images)):
        x, y = (i % cols) * w, (i // cols) * (h + cap)
        sheet.paste(img.resize((w, h)), (x, y + cap))
        draw.text((x + cap // 3, y + cap // 2), label, font=font, fill=FG, anchor="lm")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
