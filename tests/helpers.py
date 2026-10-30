import os
import pty
import select
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAKE = os.path.join(ROOT, "tests", "fake_agy.py")


def make_env():
    home = tempfile.mkdtemp(prefix="agyauto-test-")
    env = dict(os.environ, HOME=home, AGYAUTO_STATE=os.path.join(home, "state"),
               AGYAUTO_CONFIG=os.path.join(home, "config.json"), TERM="xterm-256color", PYTHONDONTWRITEBYTECODE="1")
    env.pop("AGYAUTO_DUMP", None)
    return env


def spawn(args, env):
    """Start `python -m agyauto <args>` on a pty; returns (Popen, master_fd)."""
    m, s = pty.openpty()
    p = subprocess.Popen([sys.executable, "-m", "agyauto"] + args, cwd=ROOT, env=env,
                         stdin=s, stdout=s, stderr=s, close_fds=True, start_new_session=True)
    os.close(s)
    return p, m


def drain(m, p, timeout=15, until=None):
    out = b""
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([m], [], [], 0.2)
        if r:
            try:
                d = os.read(m, 65536)
            except OSError:
                break
            if not d:
                break
            out += d
            if until and until in out:
                break
        elif p.poll() is not None:
            break
    return out
