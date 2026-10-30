import json
import os
import tempfile

from . import paths

DEFAULTS = {
    "lang": "en",             # en | uz
    "key": "enter",           # enter | 1
    "delay": 0.4,             # seconds the screen must be quiet before answering
    "stall_after": 4.0,       # seconds before an unhandled key-hint screen is recorded as STALLED
    "notify": True,           # desktop notification on BLOCKED
    "retention_days": 90,
    "danger_default": False,
    "deny": [],               # extra regexes; a prompt matching one is never auto-approved
}


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(paths.config_file()) as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return cfg


def mtime():
    try:
        return os.stat(paths.config_file()).st_mtime
    except OSError:
        return 0.0


def save(cfg):
    path = paths.config_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        json.dump({k: cfg[k] for k in DEFAULTS if k in cfg}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def coerce(key, raw):
    """Parse a CLI string for config key `key` into the right type."""
    if key not in DEFAULTS:
        raise KeyError(key)
    d = DEFAULTS[key]
    if isinstance(d, bool):
        return raw.lower() in ("1", "true", "yes", "on")
    if isinstance(d, int):
        return int(raw)
    if isinstance(d, float):
        return float(raw)
    if isinstance(d, list):
        return [x for x in raw.split(",") if x]
    if key == "lang" and raw not in ("en", "uz"):
        raise ValueError("lang must be en or uz")
    if key == "key" and raw not in ("enter", "1"):
        raise ValueError("key must be enter or 1")
    return raw
