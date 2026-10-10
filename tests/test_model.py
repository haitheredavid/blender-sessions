from datetime import date

import pytest

from blend import model as models

D = date(2026, 10, 10)


def test_create_fills_template(models_dir):
    m = models.create("Tea Pot!", base=models_dir, on=D)
    assert m.name == "tea-pot"
    assert m.config["name"] == "tea-pot"
    assert m.config["created"] == "2026-10-10"
    assert m.config["status"] == "active"
    assert m.config["units"]["scale_length"] == 1.0
    assert "# tea-pot" in m.brief.read_text()
    assert (m.path / "builders" / "build_all.py").exists()
    assert m.exports.is_dir() and m.out.is_dir()
    assert m.log_dir.is_dir() and m.sessions_dir.is_dir()
    assert m.params() == {} and m.variants() == {"base": {}}
    assert m.status() == "new"


def test_create_refuses_duplicates(models_dir):
    models.create("cube", base=models_dir)
    with pytest.raises(FileExistsError):
        models.create("cube", base=models_dir)


def test_resolve_by_substring(models_dir):
    models.create("cube", base=models_dir)
    models.create("cube-v2", base=models_dir)
    assert models.resolve("cube", base=models_dir).name == "cube"  # exact wins
    assert models.resolve("v2", base=models_dir).name == "cube-v2"
    with pytest.raises(LookupError, match="ambiguous"):
        models.resolve("cub", base=models_dir)
    with pytest.raises(LookupError, match="no model"):
        models.resolve("nope", base=models_dir)


def test_list_skips_template(models_dir):
    models.create("a", base=models_dir)
    assert [m.name for m in models.list_all(base=models_dir)] == ["a"]


def test_status_progression(models_dir):
    m = models.create("lamp", base=models_dir)
    assert m.status() == "new"
    m.blend.write_bytes(b"BLENDER")
    assert m.status() == "modeling"
    (m.exports / "lamp.glb").write_bytes(b"glTF")
    assert m.status() == "exported"
    m.render.write_bytes(b"png")
    assert m.status() == "rendered"
    m.set_field("status", "done")
    assert m.status() == "done"


def test_set_field_keeps_comments_and_tables(models_dir):
    m = models.create("lamp", base=models_dir)
    m.set_field("workflows", ["mcp-modeling-loop", "hard-surface"])
    text = m.toml.read_text()
    assert "# workflows/<name>.md" in text
    assert m.workflows == ["mcp-modeling-loop", "hard-surface"]
    assert m.config["export"]["formats"] == ["glb"]
    m.set_field("owner", "me")  # new key lands above the first table
    assert m.config["owner"] == "me"
    assert "owner" not in m.config["units"]


def test_sessions(models_dir):
    m = models.create("lamp", base=models_dir)
    assert m.latest_session() is None
    a = m.new_session("Blockout", goal="rough shape", on=date(2026, 10, 9))
    b = m.new_session("blockout", on=D)
    c = m.new_session("blockout", on=D)
    assert a.name == "2026-10-09-blockout.md"
    assert "rough shape" in a.read_text()
    assert c.name == "2026-10-10-blockout-2.md"
    assert m.session_notes() == [a, b, c]
    assert m.latest_session() == c


def test_latest_prefers_recent_session(models_dir):
    a = models.create("a", base=models_dir)
    b = models.create("b", base=models_dir)
    a.new_session("x", on=D)
    b.new_session("x", on=date(2026, 10, 9))
    assert models.latest(base=models_dir).name == "a"
    a.set_field("status", "done")
    assert models.latest(base=models_dir).name == "b"
    b.set_field("status", "done")
    with pytest.raises(LookupError):
        models.latest(base=models_dir)


def test_params_and_variants(models_dir):
    m = models.create("frame", base=models_dir)
    m.params_toml.write_text(
        '[base]\nDepth = 40.0\n"Rabbet Width" = 6\n\n'
        "[variants.deep]\nDepth = 60.0\n\n[variants.flat]\n"
    )
    assert m.params() == {"Depth": 40.0, "Rabbet Width": 6}
    v = m.variants()
    assert list(v) == ["base", "deep", "flat"]
    assert v["deep"] == {"Depth": 60.0, "Rabbet Width": 6}
    assert v["flat"] == v["base"]
    m.params_toml.write_text("[base]\nDepth = 40.0\n\n[variants.x]\nDepht = 1\n")
    with pytest.raises(ValueError, match="unknown params"):
        m.variants()
    m.params_toml.write_text("[base]\n\n[variants.Big]\n")
    with pytest.raises(ValueError, match="slug"):
        m.variants()


def test_render_and_export_options(models_dir):
    m = models.create("cube", base=models_dir)
    assert m.render_options() == {"framing": "fit", "scene": None}
    assert m.export_formats() == ["glb"]
    assert m.turntable_options() == {"frames": 120, "fps": 30}
    m.toml.write_text(
        m.toml.read_text()
        .replace('# framing = "fit"', 'framing = "close"')
        .replace('formats = ["glb"]', 'formats = ["glb", "usd"]')
    )
    with pytest.raises(ValueError, match="framing"):
        m.render_options()
    with pytest.raises(ValueError, match="formats"):
        m.export_formats()


def test_views_defaults_and_validation(models_dir):
    m = models.create("frame", base=models_dir)
    m.toml.write_text(
        m.toml.read_text()
        + '\n[[views]]\nname = "front"\nupright = true\ninclude = ["Ref"]\n'
        + '\n[[views]]\nname = "tip"\nzoom = 3\ntarget = [1, 2, 3]\n'
    )
    front, tip = m.views()
    assert front["upright"] and front["include"] == ["Ref"]
    assert (
        front["framing"] == "fit" and front["zoom"] == 1.0 and front["target"] is None
    )
    assert tip["target"] == [1.0, 2.0, 3.0] and tip["zoom"] == 3.0
    m.toml.write_text(m.toml.read_text() + '\n[[views]]\nname = "tip"\n')
    with pytest.raises(ValueError, match="twice"):
        m.views()
