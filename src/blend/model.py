"""Models: long-lived folders under models/, each iterated across many short sessions.

models/<slug>/ holds model.blend, model.toml (config), params.toml (GN params + variants),
builders/, log/ (every iteration step, see blend.steplog), sessions/ (one note per sitting),
exports/, render.png and out/ (gitignored scratch).
"""

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
EXPORT_FORMATS = ("glb", "fbx", "obj", "stl", "3mf")
EXPORT_SUFFIXES = {f".{f}" for f in EXPORT_FORMATS}
# [print] keys a [print.<collection>] pack does not inherit from the main pack
PER_PACK_KEYS = (
    "orientation",
    "flat",
    "hardware",
    "assembly",
    "intent",
    "feedback_applied",
    "feedback_declined",
)
SESSION_NOTE = """\
# {date} {slug}

## Goal
{goal}

## Steps
<!-- `blend history {model}` has the full step log; summarise the arc here. -->

## Outcome

## Next
"""


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"invalid name: {name!r}")
    return slug


def today() -> date:
    return datetime.now().astimezone().date()


@dataclass
class Model:
    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def toml(self) -> Path:
        return self.path / "model.toml"

    @property
    def params_toml(self) -> Path:
        return self.path / "params.toml"

    @property
    def brief(self) -> Path:
        return self.path / "brief.md"

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
    def log_dir(self) -> Path:
        return self.path / "log"

    @property
    def sessions_dir(self) -> Path:
        return self.path / "sessions"

    @property
    def render(self) -> Path:
        return self.path / "render.png"

    @property
    def config(self) -> dict:
        return tomllib.loads(self.toml.read_text())

    @property
    def workflows(self) -> list[str]:
        return list(self.config.get("workflows", []))

    @property
    def speckle(self) -> dict:
        """[speckle] account (email) and project_id; Speckle models are named
        <model> / <model>/<variant> and resolved by name."""
        return dict(self.config.get("speckle", {}))

    # --- params ---------------------------------------------------------------

    def params(self) -> dict:
        """params.toml [base]: the canonical GN inputs."""
        if not self.params_toml.exists():
            return {}
        return dict(tomllib.loads(self.params_toml.read_text()).get("base", {}))

    def variants(self) -> dict[str, dict]:
        """[variants.<v>] merged over [base], keyed by variant name (base first)."""
        base = self.params()
        raw = (
            tomllib.loads(self.params_toml.read_text()).get("variants", {})
            if self.params_toml.exists()
            else {}
        )
        out = {"base": base}
        for name, overrides in raw.items():
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
                raise ValueError(f"[variants.{name}]: name must be a lowercase slug")
            if name == "base":
                raise ValueError("[variants.base] is reserved; use [base]")
            if unknown := set(overrides) - set(base):
                raise ValueError(
                    f"[variants.{name}] overrides unknown params: {sorted(unknown)}"
                )
            out[name] = {**base, **overrides}
        return out

    # --- sessions -------------------------------------------------------------

    def session_notes(self) -> list[Path]:
        if not self.sessions_dir.is_dir():
            return []

        def created(p: Path) -> tuple:  # date prefix, then creation order within a day
            st = p.stat()
            return p.name[:10], getattr(st, "st_birthtime", st.st_mtime), p.name

        return sorted(self.sessions_dir.glob("[0-9][0-9][0-9][0-9]-*.md"), key=created)

    def latest_session(self) -> Path | None:
        notes = self.session_notes()
        return notes[-1] if notes else None

    def new_session(self, name: str, goal: str = "", on: date | None = None) -> Path:
        """sessions/YYYY-MM-DD-<slug>.md; a second one the same day gets a -2 suffix."""
        slug = slugify(name)
        day = (on or today()).isoformat()
        self.sessions_dir.mkdir(exist_ok=True)
        path, n = self.sessions_dir / f"{day}-{slug}.md", 2
        while path.exists():
            path, n = self.sessions_dir / f"{day}-{slug}-{n}.md", n + 1
        path.write_text(
            SESSION_NOTE.format(date=day, slug=slug, goal=goal, model=self.name)
        )
        return path

    # --- outputs --------------------------------------------------------------

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

    def export_collection(self) -> str:
        """[export] collection: what `blend export` writes (Model, or e.g. Print)."""
        return str(self.config.get("export", {}).get("collection", "Model"))

    def print_options(self, collection: str = "") -> dict:
        """[print]: handoff settings for `blend print-pack` (collection, bed, material,
        printer, orientation, flat part globs, hardware, assembly notes). For another
        collection, its [print.<collection>] table replaces the notes (orientation,
        flat, hardware, assembly, intent, feedback_*) and keeps the printer settings.

        Arrays of tables ([[print.part]], [[print.filament]], [[print.coupon]]) are
        lists, so they stay in the base; a collection inherits them unless its own
        table defines them ([[print.<collection>.part]] etc.), which replaces them.
        feedback_applied/declined never inherit: recommendation ids are per pack
        (each pack has its own results.json)."""
        base = self.config.get("print", {})
        cfg = {k: v for k, v in base.items() if not isinstance(v, dict)}
        if collection:
            for key in PER_PACK_KEYS:
                cfg.pop(key, None)
            cfg.update(base.get(collection, {}), collection=collection)
        cfg.setdefault("collection", "Print")
        cfg.setdefault("bed", 256)
        return cfg

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
        """Set a top-level key in model.toml in place, keeping comments and layout."""
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
        tomllib.loads(text)  # never leave a broken model.toml behind
        self.toml.write_text(text)


def models_dir(base: Path | None = None) -> Path:
    return base or get_settings().models_dir


def create(name: str, base: Path | None = None, on: date | None = None) -> Model:
    base = models_dir(base)
    slug = slugify(name)
    dest = base / slug
    if dest.exists():
        raise FileExistsError(dest)
    shutil.copytree(base / TEMPLATE, dest, ignore=shutil.ignore_patterns(".DS_Store"))
    m = Model(dest)
    created = (on or today()).isoformat()
    for f in (m.toml, m.brief):
        f.write_text(
            f.read_text().replace("{{name}}", slug).replace("{{date}}", created)
        )
    return m


def list_all(base: Path | None = None) -> list[Model]:
    base = models_dir(base)
    if not base.is_dir():
        return []
    return [
        Model(p)
        for p in sorted(base.iterdir())
        if p.is_dir() and p.name != TEMPLATE and (p / "model.toml").exists()
    ]


def resolve(ref: str, base: Path | None = None) -> Model:
    """Find a model by exact folder name, or by unique substring (e.g. 'witch')."""
    all_models = list_all(base)
    exact = [m for m in all_models if m.name == ref]
    if exact:
        return exact[0]
    matches = [m for m in all_models if ref in m.name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise LookupError(f"no model matches {ref!r}")
    raise LookupError(f"{ref!r} is ambiguous: {', '.join(m.name for m in matches)}")


def latest(base: Path | None = None) -> Model:
    """The active model with the most recent session note (or newest folder)."""
    active = [m for m in list_all(base) if m.status() != "done"]
    if not active:
        raise LookupError("no active models")
    return max(
        active,
        key=lambda m: (
            m.latest_session().name[:10] if m.latest_session() else "",
            m.path.stat().st_mtime,
        ),
    )
