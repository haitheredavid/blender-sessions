"""Sessions: dated folders under sessions/, one model each, holding its .blend and outputs."""

import re
import shutil
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from blend.config import get_settings

TEMPLATE = "_template"
FRAMINGS = (
    "fit",
    "wide",
)  # `blend render`: zoom to the model, or pull back for context
EXPORT_FORMATS = ("glb", "fbx", "obj")
EXPORT_SUFFIXES = {f".{f}" for f in EXPORT_FORMATS}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"invalid session name: {name!r}")
    return slug


@dataclass
class Session:
    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def toml(self) -> Path:
        return self.path / "session.toml"

    @property
    def blend(self) -> Path:
        return self.path / "model.blend"

    @property
    def exports(self) -> Path:
        return self.path / "exports"

    @property
    def out(self) -> Path:
        return self.path / "out"

    @property
    def render(self) -> Path:
        return self.path / "render.png"

    @property
    def config(self) -> dict:
        return tomllib.loads(self.toml.read_text())

    @property
    def workflows(self) -> list[str]:
        return list(self.config.get("workflows", []))

    def render_options(self) -> dict:
        """[render] framing (fit|wide) and scene for `blend render`, with defaults."""
        cfg = self.config.get("render", {})
        framing = cfg.get("framing", "fit")
        if framing not in FRAMINGS:
            raise ValueError(
                f"[render] framing must be one of {', '.join(FRAMINGS)}, not {framing!r}"
            )
        return {"framing": framing, "scene": cfg.get("scene")}

    def views(self) -> list[dict]:
        """[[views]] for `blend views`: named studio shots, validated, with defaults."""
        out, seen = [], set()
        for i, cfg in enumerate(self.config.get("views", [])):
            name = cfg.get("name")
            if not name or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
                raise ValueError(f"[[views]] #{i + 1}: name must be a lowercase slug")
            if name in seen:
                raise ValueError(f"[[views]] {name!r} is defined twice")
            seen.add(name)
            framing = cfg.get("framing", "fit")
            if framing not in FRAMINGS:
                raise ValueError(
                    f"[[views]] {name!r}: framing must be one of {', '.join(FRAMINGS)}"
                )
            target = cfg.get("target")
            if target is not None and len(target) != 3:
                raise ValueError(f"[[views]] {name!r}: target must be [x, y, z]")
            out.append(
                {
                    "name": name,
                    "azimuth": float(cfg.get("azimuth", -60.0)),
                    "elevation": float(cfg.get("elevation", 22.0)),
                    "framing": framing,
                    "upright": bool(cfg.get("upright", False)),
                    "include": list(cfg.get("include", [])),
                    "zoom": float(cfg.get("zoom", 1.0)),
                    "target": [float(v) for v in target] if target else None,
                    "size": int(cfg.get("size", 1200)),
                }
            )
        return out

    def export_formats(self) -> list[str]:
        """[export] formats, validated against EXPORT_FORMATS."""
        formats = self.config.get("export", {}).get("formats", ["glb"])
        if bad := [f for f in formats if f not in EXPORT_FORMATS]:
            raise ValueError(
                f"[export] formats must be from {', '.join(EXPORT_FORMATS)}, not {bad}"
            )
        return list(formats)

    def turntable_options(self) -> dict:
        cfg = self.config.get("turntable", {})
        return {"frames": int(cfg.get("frames", 120)), "fps": int(cfg.get("fps", 30))}

    def export_files(self) -> list[Path]:
        return sorted(
            p for p in self.exports.glob("*") if p.suffix.lower() in EXPORT_SUFFIXES
        )

    def status(self) -> str:
        if self.config.get("status") == "done":
            return "done"
        if self.render.exists():
            return "rendered"
        if self.export_files():
            return "exported"
        if self.blend.exists():
            return "modeling"
        return "new"

    def set_field(self, key: str, value: str | list[str]) -> None:
        """Set a top-level key in session.toml in place, keeping comments and layout."""
        if isinstance(value, list):
            rendered = "[" + ", ".join(f'"{v}"' for v in value) + "]"
        else:
            rendered = f'"{value}"'
        lines = self.toml.read_text().splitlines()
        pattern = re.compile(rf"^{re.escape(key)}\s*=")
        new = f"{key} = {rendered}"
        # top-level keys end at the first table header
        end = next(
            (i for i, ln in enumerate(lines) if ln.lstrip().startswith("[")), len(lines)
        )
        hit = next((i for i in range(end) if pattern.match(lines[i])), None)
        if hit is None:
            while end > 0 and not lines[end - 1].strip():
                end -= 1
            lines.insert(end, new)
        else:
            _, _, comment = lines[hit].partition("#")
            lines[hit] = f"{new:<29} #{comment}" if comment else new
        text = "\n".join(lines) + "\n"
        tomllib.loads(text)  # never leave a broken session.toml behind
        self.toml.write_text(text)


def sessions_dir(base: Path | None = None) -> Path:
    return base or get_settings().sessions_dir


def create(name: str, base: Path | None = None, today: date | None = None) -> Session:
    base = sessions_dir(base)
    slug = slugify(name)
    dest = base / f"{(today or datetime.now().astimezone().date()).isoformat()}-{slug}"
    if dest.exists():
        raise FileExistsError(dest)
    shutil.copytree(base / TEMPLATE, dest, ignore=shutil.ignore_patterns(".DS_Store"))
    s = Session(dest)
    s.toml.write_text(
        s.toml.read_text().replace("{{name}}", slug).replace("{{date}}", dest.name[:10])
    )
    return s


def list_all(base: Path | None = None) -> list[Session]:
    base = sessions_dir(base)
    return [
        Session(p)
        for p in sorted(base.iterdir())
        if p.is_dir() and p.name != TEMPLATE and (p / "session.toml").exists()
    ]


def resolve(ref: str, base: Path | None = None) -> Session:
    """Find a session by exact folder name, or by unique substring (e.g. 'teapot')."""
    all_sessions = list_all(base)
    exact = [s for s in all_sessions if s.name == ref]
    if exact:
        return exact[0]
    matches = [s for s in all_sessions if ref in s.name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise LookupError(f"no session matches {ref!r}")
    raise LookupError(f"{ref!r} is ambiguous: {', '.join(s.name for s in matches)}")


def latest(base: Path | None = None) -> Session:
    """Newest session that isn't done (for `/done` with no argument)."""
    active = [s for s in list_all(base) if s.status() != "done"]
    if not active:
        raise LookupError("no active sessions")
    return active[-1]
