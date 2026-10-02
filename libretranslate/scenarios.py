import os
import json
from string import Template

DATA_DIR = os.path.join(os.path.dirname(__file__), "scenarios_data")
_REGISTRY = None


def _load():
    """Load scenario templates from scenarios_data/*.json (cached)."""
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY
    _REGISTRY = {}
    if not os.path.isdir(DATA_DIR):
        return _REGISTRY
    for fn in sorted(os.listdir(DATA_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(DATA_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if "id" in obj and "template_zh" in obj and "template_ru" in obj:
                _REGISTRY[obj["id"]] = obj
        except Exception as e:
            print("scenario load error:", fn, str(e))
    return _REGISTRY


def list_scenarios():
    """Return scenario metadata for the frontend list view."""
    reg = _load()
    return [
        {
            "id": s["id"],
            "name_zh": s.get("name_zh", ""),
            "name_ru": s.get("name_ru", ""),
            "category": s.get("category", ""),
            "variables": s.get("variables", []),
        }
        for s in reg.values()
    ]


def get_scenario(sid):
    return _load().get(sid)


def render_scenario(sid, variables=None):
    """Render both zh and ru sides of a scenario with the given variables.

    Returns {"id", "zh", "ru", "variables"} or None when the scenario is
    unknown. Missing variables are left as the original $placeholder so the
    caller can spot unfilled slots.
    """
    s = get_scenario(sid)
    if s is None:
        return None
    safe_vars = {str(k): str(v) for k, v in (variables or {}).items()}
    zh = Template(s["template_zh"]).safe_substitute(safe_vars)
    ru = Template(s["template_ru"]).safe_substitute(safe_vars)
    return {"id": sid, "zh": zh, "ru": ru, "variables": safe_vars}
