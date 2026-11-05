import json
import os
from pathlib import Path

DEFAULTS = {"size": "normal", "moving": True, "topmost": True,
            "frequency": "normal", "hide_fullscreen": True, "autostart": False,
            "x": None, "y": None}


def config_path():
    root = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    return root / "GlassesMandu" / "settings.json"


def load(path=None):
    path = path or config_path()
    result = DEFAULTS.copy()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return result
        for key, values in (("size", ("small", "normal", "large")),
                            ("frequency", ("low", "normal", "high"))):
            if raw.get(key) in values:
                result[key] = raw[key]
        for key in ("moving", "topmost", "hide_fullscreen", "autostart"):
            if type(raw.get(key)) is bool:
                result[key] = raw[key]
        for key in ("x", "y"):
            if type(raw.get(key)) is int and abs(raw[key]) < 1000000:
                result[key] = raw[key]
    except (OSError, ValueError, TypeError):
        pass
    return result


def save(settings, path=None):
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
