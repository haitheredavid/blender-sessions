from PIL import Image

from blend import grid


def test_compose_lays_out_rows_with_captions(tmp_path):
    cells = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255), (9, 9, 9)]):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", (100, 60), color).save(p)
        cells.append((f"v{i}", p))
    out = grid.compose(cells, tmp_path / "out" / "grid.png", columns=3)
    img = Image.open(out)
    cap = 24  # max(24, 60 // 12)
    assert img.size == (300, 2 * (60 + cap))
    assert img.getpixel((50, cap + 30)) == (255, 0, 0)
    assert img.getpixel((250, cap + 30)) == (0, 0, 255)
    assert img.getpixel((50, 60 + 2 * cap + 30)) == (9, 9, 9)


def test_compose_needs_cells(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        grid.compose([], tmp_path / "x.png")
