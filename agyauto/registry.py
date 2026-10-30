"""File-based session registry: no daemon, every wrapper publishes a heartbeat file."""
import json
import os
import time

from . import paths

STALE_AFTER = 6.0


def _atomic_write(path, text):
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def init():
    return paths.ensure_private(paths.sessions_dir())


def _p(pid, ext):
    return os.path.join(paths.sessions_dir(), "%d.%s" % (pid, ext))


def publish(pid, state):
    state = dict(state, pid=pid, beat=time.time())
    _atomic_write(_p(pid, "json"), json.dumps(state))


def publish_screen(pid, text):
    _atomic_write(_p(pid, "screen"), text)


def read_control(pid):
    try:
        with open(_p(pid, "ctl")) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_control(pid, **changes):
    cur = read_control(pid)
    cur.update(changes)
    _atomic_write(_p(pid, "ctl"), json.dumps(cur))


def read_screen(pid):
    try:
        with open(_p(pid, "screen")) as f:
            return f.read()
    except OSError:
        return ""


def remove(pid):
    for ext in ("json", "ctl", "screen"):
        try:
            os.unlink(_p(pid, ext))
        except OSError:
            pass


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def sessions(cleanup=True):
    """All live sessions, oldest first. Files of dead processes are removed."""
    out = []
    try:
        names = os.listdir(paths.sessions_dir())
    except OSError:
        return out
    for n in names:
        if not n.endswith(".json"):
            continue
        try:
            pid = int(n[:-5])
            with open(os.path.join(paths.sessions_dir(), n)) as f:
                s = json.load(f)
        except (ValueError, OSError):
            continue
        if not _alive(pid):
            if cleanup:
                remove(pid)
            continue
        s["stale"] = time.time() - s.get("beat", 0) > STALE_AFTER
        out.append(s)
    out.sort(key=lambda s: s.get("started", 0))
    return out
