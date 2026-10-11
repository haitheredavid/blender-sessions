from pathlib import Path

from blend import printpack


def part(name, w, d, vol=1.0):
    return {"name": name, "size": [w, d, 5], "volume_cm3": vol, "manifold": True,
            "fits_bed": True}  # fmt: skip


def test_suggest_plates_shelf_packs_bounding_boxes():
    pieces = [part(f"P{i}", 139.7, 177.8) for i in range(4)]
    small = [part(f"K{i}", 32, 6) for i in range(4)] + [part("C", 16.5, 9)]
    plates = printpack.suggest_plates(pieces + small, 256)
    # two 139.7 x 177.8 boxes never share a 256 bed, rotated or not: 4 plates
    assert [p[0] for p in plates] == ["P0", "P1", "P2", "P3"]
    assert sum(len(p) for p in plates) == 9  # small parts fill in beside the pieces
    assert printpack.suggest_plates([part("Big", 300, 10)], 256) == [["Big"]]
    assert printpack.suggest_plates(
        [part("A", 120, 120), part("B", 120, 120)], 256
    ) == [["A", "B"]]


def test_manifest_and_readme(tmp_path):
    out = tmp_path / "models" / "m" / "print"
    res = {"blend": str(out / "parts.blend"), "stl_dir": str(out / "stl"),
           "parts": [part("Piece", 140, 178, 120.5), part("Key", 32, 6, 0.5)]}  # fmt: skip
    cfg = {"bed": 256, "material": "PLA", "hardware": ["8x M3x8"], "assembly": ["glue"]}
    m = printpack.manifest("m", res, cfg, tmp_path)
    assert m["units"] == "mm" and m["blend"] == "models/m/print/parts.blend"
    assert m["parts"][0]["stl"] == "stl/Piece.stl"
    assert m["total_volume_cm3"] == 121.0
    out.mkdir(parents=True)
    printpack.write(out, m)
    text = (out / "README.md").read_text()
    assert "| Piece | 140 x 178 x 5 | 120.5 | yes |" in text and "- 8x M3x8" in text
    assert Path(out / "manifest.json").exists()
