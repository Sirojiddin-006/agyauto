"""Filesystem locations. Everything honours env overrides so tests never touch the real home."""
import os


def _home():
    return os.environ.get("HOME") or os.path.expanduser("~")


def state_dir():
    d = os.environ.get("AGYAUTO_STATE") or os.path.join(
        os.environ.get("XDG_STATE_HOME") or os.path.join(_home(), ".local", "state"), "agyauto")
    return d


def sessions_dir():
    return os.path.join(state_dir(), "sessions")


def history_db():
    return os.path.join(state_dir(), "history.db")


def config_file():
    return os.environ.get("AGYAUTO_CONFIG") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.join(_home(), ".config"), "agyauto", "config.json")


def install_dir():
    return os.environ.get("AGYAUTO_INSTALL") or os.path.join(
        os.environ.get("XDG_DATA_HOME") or os.path.join(_home(), ".local", "share"), "agyauto")


def bin_link():
    return os.path.join(_home(), ".local", "bin", "agyauto")


def ensure_private(path):
    os.makedirs(path, mode=0o700, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path
