"""Model renders and the README gallery.

render.png (`blend render`) is a studio shot at the model root, so it's committed
(out/ is gitignored). The README shows renders as uniform tiles (docs/gallery/<model>.png)
in a grid between the gallery markers, most recently rendered first; each tile links to
the model's brief.
"""

import re
from html import escape
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from blend.model import Model

START = "<!-- gallery:start -->"
END = "<!-- gallery:end -->"
COLUMNS = 4
TILE = 480
BG_TOP, BG_BOTTOM = (180, 185, 192), (160, 161, 164)  # the studio cyclorama


def model_image(m: Model) -> Path | None:
    return m.render if m.render.exists() else None


def _label(m: Model) -> tuple[str, str]:
    """('colossus tmg', '2026-09-26') from 'colossus-tmg' created 2026-09-26."""
    return m.name.replace("-", " "), str(m.config.get("created", ""))


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def make_tile(src: Path, title: str, subtitle: str, size: int = TILE) -> Image.Image:
    """Square card: dark backdrop, the image fitted in, caption bar, rounded corners."""
    img = Image.open(src).convert("RGBA")
    tile = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(tile)
    for y in range(size):  # vertical gradient matching the studio backdrop
        k = y / (size - 1)
        c = tuple(round(a + (b - a) * k) for a, b in zip(BG_TOP, BG_BOTTOM))
        draw.line([(0, y), (size, y)], fill=(*c, 255))

    caption_h = size // 6
    if img.getextrema()[3][0] == 255:  # opaque (a render): cover the whole card
        fitted = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
        tile.alpha_composite(fitted)
    else:  # transparent render: fit above the caption with some air
        box = size - caption_h - size // 10
        fitted = ImageOps.contain(img, (box, box), Image.Resampling.LANCZOS)
        x = (size - fitted.width) // 2
        y = (size - caption_h - fitted.height) // 2
        tile.alpha_composite(fitted, (x, y))

    shade = Image.new("RGBA", (size, caption_h), (12, 13, 16, 200))
    tile.alpha_composite(shade, (0, size - caption_h))
    pad = size // 22
    draw = ImageDraw.Draw(tile)
    draw.text(
        (pad, size - caption_h + pad * 0.7),
        title,
        font=_font(size // 17),
        fill=(240, 240, 242, 255),
    )
    draw.text(
        (pad, size - pad * 0.8),
        subtitle,
        font=_font(size // 26),
        fill=(150, 154, 162, 255),
        anchor="ls",
    )

    mask = Image.new("L", (size, size))
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=size // 18, fill=255
    )
    tile.putalpha(ImageChops.multiply(tile.getchannel("A"), mask))
    return tile


def _shown(models: list[Model]) -> list[Model]:
    return sorted(
        (m for m in models if model_image(m)),
        key=lambda m: (m.render.stat().st_mtime, m.name),
        reverse=True,
    )


def write_tiles(models: list[Model], tiles: Path) -> list[Path]:
    """Render tiles/<model>.png for every model with an image; returns the changed ones."""
    tiles.mkdir(parents=True, exist_ok=True)
    changed = []
    for m in _shown(models):
        buf = BytesIO()
        img = model_image(m)
        assert img is not None
        make_tile(img, *_label(m)).save(buf, "PNG", optimize=True)
        dest = tiles / f"{m.name}.png"
        if not dest.exists() or dest.read_bytes() != buf.getvalue():
            dest.write_bytes(buf.getvalue())
            changed.append(dest)
    return changed


def gallery_markdown(models: list[Model], root: Path, tiles: Path) -> str:
    """A borderless grid of tile links, newest first. Paths are relative to root."""
    shown = _shown(models)
    if not shown:
        return "_nothing rendered yet_"

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    links = []
    for m in shown:
        tip = escape(m.config.get("intent", "") or m.name, quote=True)
        img = (
            f'<img src="{rel(tiles / f"{m.name}.png")}" width="{100 // COLUMNS - 1}%" '
            f'alt="{escape(m.name, quote=True)}" title="{tip}">'
        )
        links.append(f'<a href="{rel(m.brief)}">{img}</a>')
    return '<p align="center">\n' + "\n".join(links) + "\n</p>"


def update_readme(readme: Path, md: str) -> bool:
    """Replace the text between the gallery markers. True if the file changed."""
    text = readme.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise LookupError(f"{readme.name} has no {START} ... {END} block")
    new = pattern.sub(lambda _: f"{START}\n{md}\n{END}", text, count=1)
    if new == text:
        return False
    readme.write_text(new)
    return True
