import os
from io import BytesIO

import pytest
from PIL import Image

from blend import gallery
from blend import model as models


def png(color: tuple, alpha: int = 255) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", (64, 32), (*color, alpha)).save(buf, "PNG")
    return buf.getvalue()


def test_gallery_links_tiles_newest_first(models_dir):
    root = models_dir.parent
    a = models.create("cube", base=models_dir)
    b = models.create("lamp", base=models_dir)
    c = models.create("nothing", base=models_dir)
    a.render.write_bytes(png((0, 200, 0)))
    b.render.write_bytes(png((200, 0, 0)))
    os.utime(a.render, (1, 1))  # b rendered most recently

    tiles = root / "docs" / "gallery"
    md = gallery.gallery_markdown(models.list_all(models_dir), root, tiles)
    assert c.name not in md
    assert f'<a href="models/{b.name}/brief.md">' in md
    assert f'src="docs/gallery/{b.name}.png"' in md
    assert md.index(b.name) < md.index(a.name)


def test_write_tiles_skips_unchanged(models_dir, tmp_path):
    s = models.create("lamp", base=models_dir)
    s.render.write_bytes(png((0, 200, 0), alpha=0))
    tiles = tmp_path / "tiles"
    [tile] = gallery.write_tiles([s], tiles)
    first = tile.read_bytes()
    assert Image.open(tile).size == (gallery.TILE, gallery.TILE)
    assert gallery.write_tiles([s], tiles) == []  # same input, no rewrite
    s.render.write_bytes(png((200, 0, 0)))
    assert gallery.write_tiles([s], tiles) == [tile]
    assert tile.read_bytes() != first


def test_gallery_empty(models_dir):
    root = models_dir.parent
    assert "nothing" in gallery.gallery_markdown([], root, root / "tiles")


def test_update_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"# x\n\n{gallery.START}\nold\n{gallery.END}\n\nafter\n")
    assert gallery.update_readme(readme, "new")
    assert (
        readme.read_text() == f"# x\n\n{gallery.START}\nnew\n{gallery.END}\n\nafter\n"
    )
    assert not gallery.update_readme(readme, "new")


def test_update_readme_needs_markers(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# x\n")
    with pytest.raises(LookupError):
        gallery.update_readme(readme, "new")
