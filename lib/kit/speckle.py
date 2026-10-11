"""Speckle checkpoints through the Speckle Blender connector (v3, installed as an extension).

Wraps the connector's own operations (publish_operation / load_operation) and its
specklepy client cache, so publishing uses exactly what the Speckle panel uses. The
account is always chosen by email from model.toml [speckle] account, never the
connector's default (which may be a different, e.g. work, account). Credentials stay in
the connector; nothing here reads or prints tokens.

    from kit import speckle
    cfg = speckle.config()                       # model.toml [speckle]
    model_id = speckle.ensure_model(cfg, "witch-frame")
    vid = speckle.publish(cfg, model_id, props={"variant": "base", "step": 12})
    speckle.load(cfg, model_id)                  # latest version into Ref, for comparison
"""

import importlib
import json
import sys
import tomllib

import bpy

from kit import scene


def _addon(sub: str):
    """A connector submodule, e.g. _addon("connector.operations.publish_operation")."""
    base = next((m for m in sys.modules if m.endswith("speckle_blender_addon")), None)
    if base is None:
        raise RuntimeError(
            "Speckle connector not loaded: install/enable it (see .context/speckle-guide.md)"
        )
    return importlib.import_module(f"{base}.{sub}")


def config() -> dict:
    """model.toml [speckle] next to the open .blend: account, project_id, models."""
    with open(bpy.path.abspath("//model.toml"), "rb") as f:
        cfg = dict(tomllib.load(f).get("speckle", {}))
    if not cfg.get("account"):
        raise ValueError("model.toml [speckle] account (email) is not set")
    return cfg


def account_id(email: str) -> str:
    """The connector's local account id for email. Raises instead of using the default."""
    from specklepy.api.credentials import get_local_accounts

    for acc in get_local_accounts():
        if acc.userInfo.email == email:
            return acc.id
    raise LookupError(f"no Speckle account for {email}; sign in from the Speckle panel")


def client(cfg: dict):
    api = _addon("connector.speckle_api")
    c = api.client_cache.get_client(account_id(cfg["account"]))
    if c is None:
        raise RuntimeError(f"could not create a Speckle client for {cfg['account']}")
    return c


def models(cfg: dict) -> dict[str, str]:
    """{model name: id} in the project."""
    c = client(cfg)
    project = c.project.get_with_models(cfg["project_id"], models_limit=100)
    return {m.name: m.id for m in project.models.items}


def ensure_model(cfg: dict, name: str) -> str:
    """Id of model `name` in the project, created if missing ("a/b" nests in the web UI)."""
    existing = models(cfg)
    if name in existing:
        return existing[name]
    from specklepy.core.api.inputs.model_inputs import CreateModelInput

    m = client(cfg).model.create(
        CreateModelInput(name=name, description="", project_id=cfg["project_id"])
    )
    return m.id


def _stamp(objects, props: dict) -> list[tuple]:
    """Put props on each object as blend_* custom properties (the connector publishes
    custom props; versions have no message field). Returns what to restore."""
    saved = []
    for o in objects:
        for k, v in props.items():
            key = f"blend_{k}"
            saved.append((o, key, o.get(key)))
            o[key] = v if isinstance(v, (str, int, float, bool)) else json.dumps(v)
    return saved


def publish(cfg: dict, model_id: str, objects=None, props: dict | None = None) -> str:
    """Publish objects (default: Model) with modifiers applied. Returns the version id."""
    objects = list(objects if objects is not None else scene.model().all_objects)
    if not objects:
        raise ValueError("nothing to publish: Model is empty")
    op = _addon("connector.operations.publish_operation")
    saved = _stamp(objects, props or {})
    try:
        ok, message, version_id = op.publish_operation(
            bpy.context,
            account_id(cfg["account"]),
            cfg["project_id"],
            model_id,
            objects,
            apply_modifiers=True,
        )
    finally:
        for o, key, old in saved:
            if old is None:
                del o[key]
            else:
                o[key] = old
    if not ok:
        raise RuntimeError(message)
    return version_id


def versions(cfg: dict, model_id: str, limit: int = 10) -> list[dict]:
    c = client(cfg)
    res = c.version.get_versions(model_id, cfg["project_id"], limit=limit)
    return [
        {"id": v.id, "created": str(v.created_at), "message": v.message}
        for v in res.items
    ]


def load(cfg: dict, model_id: str, version_id: str | None = None, name: str = ""):
    """Load a version (default: latest) into Ref for side-by-side comparison."""
    if version_id is None:
        latest = versions(cfg, model_id, limit=1)
        if not latest:
            raise LookupError("model has no versions")
        version_id = latest[0]["id"]
    op = _addon("connector.operations.load_operation")
    res = op.load_operation(
        bpy.context,
        account_id(cfg["account"]),
        cfg["project_id"],
        model_id,
        version_id,
        name or f"speckle_{version_id}",
    )
    ref = scene.collection(scene.REF)
    for item in res.values():
        if not isinstance(item, bpy.types.Collection) or item.name in ref.children:
            continue
        for parent in [bpy.context.scene.collection, *bpy.data.collections]:
            if item.name in parent.children:
                parent.children.unlink(item)
        ref.children.link(item)
    return version_id
