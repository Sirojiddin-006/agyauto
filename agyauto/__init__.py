"""agyauto - auto-approve agy (Antigravity CLI) permission prompts, with a dashboard."""
import os

try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")) as _f:
        __version__ = _f.read().strip()
except OSError:
    __version__ = "0.0.0"
