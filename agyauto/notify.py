import shutil
import subprocess
import sys
import time

_last = 0.0


def send(title, body):
    """Best-effort desktop notification, rate limited to one per 20 s. Never raises."""
    global _last
    if time.time() - _last < 20:
        return
    _last = time.time()
    try:
        if sys.platform == "darwin" and shutil.which("osascript"):
            body = body.replace("\\", "\\\\").replace('"', '\\"')
            title = title.replace("\\", "\\\\").replace('"', '\\"')
            cmd = ["osascript", "-e", 'display notification "%s" with title "%s"' % (body, title)]
        elif shutil.which("notify-send"):
            cmd = ["notify-send", "-u", "critical", title, body]
        else:
            return
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    except Exception:
        pass
