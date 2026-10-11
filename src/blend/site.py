"""The Pages gallery (site/): a React-Three-Fiber viewer over each model's web GLBs.

`blend export <m> --web` writes models/<m>/web/model.glb (the Model collection, as
built) and web/parts.glb ([site] parts, e.g. Print). `blend site` gathers every model
with a web/model.glb into site/public/: models.json plus a copy of each model's GLBs
and render.png under models/<m>/. Those copies are gitignored; the committed GLBs stay
under models/ (LFS).
"""

import json
import shutil
from pathlib import Path

from blend.model import Model

REPO = "haitheredavid/bless"
SPECKLE = "https://app.speckle.systems/projects/{project}"


def published(models: list[Model]) -> list[Model]:
    """Models with a web export, most recently created first."""
    shown = [m for m in models if (m.web / "model.glb").exists()]
    return sorted(shown, key=lambda m: str(m.config.get("created", "")), reverse=True)


def entry(m: Model) -> dict:
    """models.json record for one model; paths are relative to the site root."""
    cfg = m.config
    opts = m.site_options()
    base = f"models/{m.name}"
    speckle = m.speckle.get("project_id") if opts["speckle"] else None
    return {
        "name": m.name,
        "title": m.name.replace("-", " "),
        "created": str(cfg.get("created", "")),
        "intent": str(cfg.get("intent", "")),
        "tags": list(cfg.get("tags", [])),
        "status": m.status(),
        "upright": opts["upright"],
        "model": f"{base}/model.glb",
        "parts": f"{base}/parts.glb" if (m.web / "parts.glb").exists() else None,
        "render": f"{base}/render.png" if m.render.exists() else None,
        "brief": f"https://github.com/{REPO}/blob/main/models/{m.name}/brief.md",
        "speckle": SPECKLE.format(project=speckle) if speckle else None,
    }


def build(models: list[Model], public: Path) -> list[Path]:
    """Write public/models.json and copy each published model's files under
    public/models/<m>/ (stale model folders are removed). Returns files written."""
    shown = published(models)
    dest_root = public / "models"
    if dest_root.exists():
        keep = {m.name for m in shown}
        for d in dest_root.iterdir():
            if d.is_dir() and d.name not in keep:
                shutil.rmtree(d)
    written = []
    for m in shown:
        dest = dest_root / m.name
        dest.mkdir(parents=True, exist_ok=True)
        for src in (m.web / "model.glb", m.web / "parts.glb", m.render):
            if src.exists():
                shutil.copy2(src, dest / src.name)
                written.append(dest / src.name)
    manifest = public / "models.json"
    manifest.write_text(json.dumps([entry(m) for m in shown], indent=2) + "\n")
    written.append(manifest)
    return written
