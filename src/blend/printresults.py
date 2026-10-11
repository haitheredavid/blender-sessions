"""Print results: what bambi logged about a print pack, read back on the modelling side.

bambi appends checks, slices, prints and coupon fits to models/<m>/print[/<pack>]/results.json
(`print-results/1`, bambi: plugin/references/print-results.md) and proposes recommendations:
model.toml keys or builder parameters to change. A recommendation closes when its id is in
the pack manifest's feedback_applied / feedback_declined, which `blend print-pack` copies from
[print] (or [print.<Collection>]) in model.toml. `blend print-results` lists them.
"""

import json
import tomllib
from datetime import datetime
from pathlib import Path

RESULTS = "results.json"
MANIFEST = "manifest.json"
SESSION = "session.toml"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _when(text: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(text))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.astimezone()


def _duration(seconds) -> str:
    m = round(float(seconds) / 60)
    return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m}m"


def facts(run: dict) -> str:
    """One line of the facts that matter for a run, by kind."""
    kind = run.get("kind")
    bits: list[str] = []
    if kind == "check":
        summary = run.get("summary", {})
        bits.append(run.get("severity", ""))
        bits += [f"{k} {v}" for k, v in summary.items()]
    elif kind == "slice":
        if p := run.get("process"):
            bits.append(p)
        if (sec := run.get("seconds")) is not None:
            bits.append(_duration(sec))
        if (g := run.get("grams")) is not None:
            bits.append(f"{g:g} g")
        if fils := run.get("filaments"):
            bits.append("/".join(fils))
        if over := run.get("overrides"):
            bits.append(" ".join(f"{k}={v}" for k, v in over.items()))
        if run.get("filament_changes"):
            bits.append(f"{run['filament_changes']} swaps")
    elif kind == "print":
        bits.append(run.get("outcome") or run.get("state", ""))
        for f in run.get("failures", []):
            z = f" z{f['z_mm']:g}" if f.get("z_mm") is not None else ""
            bits.append(f"{f.get('part', '?')}: {f.get('kind', '?')}{z}")
    elif kind == "fit":
        bits.append(f"{run.get('coupon', '?')} = {run.get('value')}")
        if m := run.get("material"):
            bits.append(m)
    if note := run.get("note"):
        bits.append(note)
    return "; ".join(b for b in bits if b)


def status(rec_id: str, manifest: dict, model_cfg: dict) -> str:
    """applied / declined (in the pack's spec), applied-unpacked / declined-unpacked (in
    model.toml but not re-packed yet), or pending."""
    for key in ("applied", "declined"):
        if rec_id in manifest.get(f"feedback_{key}", []):
            return key
    for key in ("applied", "declined"):
        if rec_id in model_cfg.get(f"feedback_{key}", []):
            return f"{key}, not re-packed"
    return "pending"


def staleness(results: dict, manifest: dict, session: dict) -> list[str]:
    """Why the last slice may not match the pack any more."""
    slices = [r for r in results.get("runs", []) if r.get("kind") == "slice"]
    if not slices:
        return []
    last = slices[-1]
    notes = []
    recorded = session.get("source", {}).get("spec_hash")
    if recorded and last.get("spec_hash") and recorded != last["spec_hash"]:
        notes.append(
            f"last slice {last.get('id')} used spec {last['spec_hash']}, "
            f"session.toml records {recorded}: re-slice"
        )
    created, at = _when(manifest.get("created", "")), _when(last.get("at", ""))
    if created and at and created > at:
        notes.append(
            f"re-packed since slice? manifest created {manifest['created']} "
            f"after {last.get('id')} ({last['at']})"
        )
    return notes


def report(pack_dir: Path, model_cfg: dict) -> dict:
    """Everything `blend print-results` shows, as data. model_cfg is the pack's
    print_options() (for feedback ids recorded but not yet re-packed)."""
    results = _load_json(pack_dir / RESULTS)
    manifest = _load_json(pack_dir / MANIFEST)
    session_path = pack_dir / SESSION
    session = tomllib.loads(session_path.read_text()) if session_path.exists() else {}
    runs = [
        {
            "id": r.get("id"),
            "kind": r.get("kind"),
            "at": r.get("at"),
            "facts": facts(r),
        }
        for r in results.get("runs", [])
    ]
    recs = [
        {**r, "status": status(r.get("id", ""), manifest, model_cfg)}
        for r in results.get("recommendations", [])
    ]
    return {
        "pack": str(pack_dir),
        "schema": results.get("schema"),
        "spec": manifest.get("schema", "print-spec/0" if manifest else None),
        "runs": runs,
        "recommendations": recs,
        "pending": [r["id"] for r in recs if r["status"] == "pending"],
        "stale": staleness(results, manifest, session),
    }
