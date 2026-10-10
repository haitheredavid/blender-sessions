from datetime import date

import pytest

from blend import session


def test_create_fills_template(sessions_dir):
    s = session.create("Tea Pot!", base=sessions_dir, today=date(2026, 10, 10))
    assert s.name == "2026-10-10-tea-pot"
    assert s.config["name"] == "tea-pot"
    assert s.config["created"] == "2026-10-10"
    assert s.config["status"] == "active"
    assert s.config["units"]["scale_length"] == 1.0
    assert (s.path / "builders" / "build_all.py").exists()
    assert s.exports.is_dir() and s.out.is_dir()
    assert s.status() == "new"


def test_create_refuses_duplicates(sessions_dir):
    session.create("cube", base=sessions_dir, today=date(2026, 10, 10))
    with pytest.raises(FileExistsError):
        session.create("cube", base=sessions_dir, today=date(2026, 10, 10))


def test_resolve_by_substring(sessions_dir):
    session.create("cube", base=sessions_dir, today=date(2026, 10, 10))
    session.create("cube-v2", base=sessions_dir, today=date(2026, 10, 10))
    assert (
        session.resolve("2026-10-10-cube", base=sessions_dir).name == "2026-10-10-cube"
    )
    assert session.resolve("v2", base=sessions_dir).name == "2026-10-10-cube-v2"
    with pytest.raises(LookupError, match="ambiguous"):
        session.resolve("cube", base=sessions_dir)
    with pytest.raises(LookupError, match="no session"):
        session.resolve("nope", base=sessions_dir)


def test_list_skips_template(sessions_dir):
    session.create("a", base=sessions_dir)
    assert [s.name.split("-", 3)[-1] for s in session.list_all(base=sessions_dir)] == [
        "a"
    ]


def test_status_progression(sessions_dir):
    s = session.create("lamp", base=sessions_dir)
    assert s.status() == "new"
    s.blend.write_bytes(b"BLENDER")
    assert s.status() == "modeling"
    (s.exports / "lamp.glb").write_bytes(b"glTF")
    assert s.status() == "exported"
    s.render.write_bytes(b"png")
    assert s.status() == "rendered"
    s.set_field("status", "done")
    assert s.status() == "done"


def test_set_field_keeps_comments_and_tables(sessions_dir):
    s = session.create("lamp", base=sessions_dir)
    s.set_field("workflows", ["mcp-modeling-loop", "hard-surface"])
    text = s.toml.read_text()
    assert "# workflows/<name>.md" in text
    assert s.workflows == ["mcp-modeling-loop", "hard-surface"]
    assert s.config["export"]["formats"] == ["glb"]
    s.set_field("owner", "me")  # new key lands above the first table
    assert s.config["owner"] == "me"
    assert "owner" not in s.config["units"]


def test_latest_skips_done(sessions_dir):
    a = session.create("a", base=sessions_dir, today=date(2026, 10, 9))
    b = session.create("b", base=sessions_dir, today=date(2026, 10, 10))
    assert session.latest(base=sessions_dir).name == b.name
    b.set_field("status", "done")
    assert session.latest(base=sessions_dir).name == a.name
    a.set_field("status", "done")
    with pytest.raises(LookupError):
        session.latest(base=sessions_dir)


def test_render_and_export_options(sessions_dir):
    s = session.create("cube", base=sessions_dir)
    assert s.render_options() == {"framing": "fit", "scene": None}
    assert s.export_formats() == ["glb"]
    assert s.turntable_options() == {"frames": 120, "fps": 30}
    s.toml.write_text(
        s.toml.read_text()
        .replace('# framing = "fit"', 'framing = "close"')
        .replace('formats = ["glb"]', 'formats = ["glb", "usd"]')
    )
    with pytest.raises(ValueError, match="framing"):
        s.render_options()
    with pytest.raises(ValueError, match="formats"):
        s.export_formats()
