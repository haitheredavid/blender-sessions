import json

from blend import model as models
from blend import site


def publish(m: models.Model, parts: bool = False) -> None:
    m.web.mkdir()
    (m.web / "model.glb").write_bytes(b"glb")
    if parts:
        (m.web / "parts.glb").write_bytes(b"parts")


def test_site_options_default_from_print_and_hero(models_dir):
    m = models.create("frame", base=models_dir)
    m.toml.write_text(
        m.toml.read_text() + '\n[[views]]\nname = "hero"\nupright = true\n'
    )
    assert m.site_options() == {"parts": "Print", "upright": True, "speckle": False}
    m.toml.write_text(m.toml.read_text() + '\n[site]\nparts = ""\nupright = false\n')
    assert m.site_options()["parts"] == ""
    assert m.site_options()["upright"] is False


def test_build_lists_only_web_exports_newest_first(models_dir, tmp_path):
    old = models.create("old", base=models_dir, on=models.date(2026, 1, 1))
    new = models.create("new", base=models_dir, on=models.date(2026, 2, 1))
    models.create("unpublished", base=models_dir)
    publish(old, parts=True)
    publish(new)
    new.render.write_bytes(b"png")

    public = tmp_path / "public"
    written = site.build(models.list_all(models_dir), public)

    data = json.loads((public / "models.json").read_text())
    assert [e["name"] for e in data] == ["new", "old"]
    assert data[0]["render"] == "models/new/render.png"
    assert data[0]["parts"] is None
    assert data[1]["parts"] == "models/old/parts.glb"
    assert data[1]["speckle"] is None  # private unless [site] speckle = true
    assert (public / "models/old/parts.glb").read_bytes() == b"parts"
    assert public / "models.json" in written


def test_build_drops_stale_models_and_links_public_speckle(models_dir, tmp_path):
    public = tmp_path / "public"
    (public / "models" / "gone").mkdir(parents=True)
    m = models.create("lamp", base=models_dir)
    m.toml.write_text(m.toml.read_text() + "\n[site]\nspeckle = true\n")
    publish(m)

    site.build(models.list_all(models_dir), public)

    assert not (public / "models" / "gone").exists()
    [entry] = json.loads((public / "models.json").read_text())
    assert entry["speckle"] == "https://app.speckle.systems/projects/de2b7457ae"
