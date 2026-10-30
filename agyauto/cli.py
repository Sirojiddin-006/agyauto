import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request

from . import __version__, config, history, paths, registry
from .i18n import set_lang, t

REPO = "Sirojiddin-006/agyauto"
SUBCOMMANDS = ("replay", "dashboard", "status", "history", "config", "lang", "doctor", "update", "uninstall", "version", "help", "run")

HELP = """agyauto %s - auto-approve agy permission prompts, with a dashboard

usage:
  agyauto                         open the dashboard
  agyauto agy [args]              run agy with auto-approval
  agyauto ssh user@host           run ssh; start agy inside it, prompts are approved
  agyauto [--danger] [--name N] [--key enter|1] [--record FILE] [--] <command...>

commands:
  status [--json]                 list running sessions
  history [-n N] [--kind K] [-s TEXT]   show recent approvals / blocks
  config [get|set KEY VALUE]      show or change settings (picked up live by running sessions)
  lang [en|uz]                    show or set the interface language
  replay FILE [--rows N --cols N]  render a --record file (debugging the live view)
  doctor                          check the installation
  update                          update to the latest version
  uninstall [--purge]             remove agyauto (--purge also deletes config and history)

Only the pty of the wrapped command is written to: no window focus, no effect on other workspaces.
Deleting / or ~ (rm -rf /) is never approved, even in dangermode.
"""


def _lang():
    cfg = config.load()
    set_lang(cfg["lang"])
    return cfg


def cmd_wrap(argv):
    from . import wrapper
    name = danger = key = None
    record = os.environ.get("AGYAUTO_RECORD")
    while argv and argv[0].startswith("-") and argv[0] != "--":
        a = argv.pop(0)
        if a == "--danger":
            danger = True
        elif a == "--record" and argv:
            record = argv.pop(0)
        elif a == "--name" and argv:
            name = argv.pop(0)
        elif a == "--key" and argv:
            key = argv.pop(0)
            if key not in ("enter", "1"):
                sys.exit("agyauto: --key must be enter or 1")
        elif a in ("-h", "--help"):
            print(HELP % __version__)
            return 0
        else:
            sys.exit("agyauto: unknown option %s" % a)
    if argv and argv[0] == "--":
        argv.pop(0)
    if not argv:
        sys.exit("agyauto: command required, e.g. agyauto agy")
    return wrapper.run(argv, name=name, danger=danger, key_override=key, record=record)


def cmd_replay(argv):
    """Render a --record file the way the live view would (debugging aid)."""
    from . import vt
    rows, cols, path = 40, 120, None
    while argv:
        a = argv.pop(0)
        if a == "--rows" and argv:
            rows = int(argv.pop(0))
        elif a == "--cols" and argv:
            cols = int(argv.pop(0))
        else:
            path = a
    if not path:
        sys.exit("usage: agyauto replay FILE [--rows N] [--cols N]")
    scr = vt.Screen(rows, cols)
    with open(path, "rb") as f:
        scr.feed(f.read().decode("utf8", "replace"))
    print("\n".join(scr.visible()))
    return 0


def cmd_status(argv):
    ss = registry.sessions()
    if "--json" in argv:
        print(json.dumps(ss, indent=2))
        return 0
    if not ss:
        print("no running sessions")
        return 0
    now = time.time()
    print("%-8s %-10s %-24s %8s %6s %6s %6s" % ("PID", "STATE", "NAME", "UPTIME", "OK", "BLOCK", "STALL"))
    for s in ss:
        st = "stale" if s.get("stale") else s.get("status", "")
        print("%-8d %-10s %-24s %7ds %6d %6d %6d" % (s["pid"], st, s.get("name", "")[:24], now - s.get("started", now),
                                                      s.get("approved", 0), s.get("blocked", 0), s.get("stalled", 0)))
    return 0


def cmd_history(argv):
    n, kind, text = 30, None, None
    while argv:
        a = argv.pop(0)
        if a == "-n" and argv:
            n = int(argv.pop(0))
        elif a == "--kind" and argv:
            kind = argv.pop(0).upper()
        elif a in ("-s", "--search") and argv:
            text = argv.pop(0)
    db = history.connect()
    for _id, ts, _sid, sess, k, ptype, cmd, _key, _scr in reversed(history.query(db, kind=kind, text=text, limit=n)):
        print("%s  %-8s %-18s %-8s %s" % (time.strftime("%F %T", time.localtime(ts)), k, sess[:18], ptype,
                                          (cmd or "").replace("\n", " ")[:100]))
    return 0


def cmd_config(argv):
    cfg = config.load()
    if not argv or argv[0] == "get":
        for k in config.DEFAULTS:
            if len(argv) < 2 or argv[1] == k:
                print("%s = %s" % (k, json.dumps(cfg[k], ensure_ascii=False)))
        return 0
    if argv[0] == "set" and len(argv) >= 3:
        try:
            cfg[argv[1]] = config.coerce(argv[1], argv[2] if argv[1] != "deny" else ",".join(argv[2:]))
        except (KeyError, ValueError) as e:
            sys.exit("agyauto: bad setting: %s" % e)
        config.save(cfg)
        print("%s = %s" % (argv[1], json.dumps(cfg[argv[1]], ensure_ascii=False)))
        return 0
    sys.exit("usage: agyauto config [get [KEY] | set KEY VALUE]")


def cmd_lang(argv):
    cfg = config.load()
    if argv:
        if argv[0] not in ("en", "uz"):
            sys.exit("agyauto: language must be en or uz")
        cfg["lang"] = argv[0]
        config.save(cfg)
    print(cfg["lang"])
    return 0


def cmd_doctor(_argv):
    ok = True

    def line(good, text):
        nonlocal ok
        ok = ok and good
        print(("  ok   " if good else "  FAIL ") + text)

    line(sys.version_info >= (3, 8), "python %s (need >= 3.8)" % sys.version.split()[0])
    for mod in ("pty", "termios", "curses", "sqlite3"):
        try:
            __import__(mod)
            line(True, "module " + mod)
        except ImportError:
            line(False, "module %s missing" % mod)
    link = paths.bin_link()
    line(os.path.exists(link) or True, "launcher %s" % (link if os.path.exists(link) else "(running from source)"))
    on_path = shutil.which("agyauto")
    print("  %s agyauto on PATH: %s" % ("ok  " if on_path else "warn", on_path or "no - add ~/.local/bin to PATH"))
    print("  agy: %s" % (shutil.which("agy") or "not found (agyauto wraps any command, but you probably want agy)"))
    try:
        history.connect().close()
        line(True, "history db %s" % paths.history_db())
    except Exception as e:  # noqa: BLE001
        line(False, "history db: %s" % e)
    print("  notifications: %s" % (shutil.which("notify-send") or shutil.which("osascript") or "none available"))
    return 0 if ok else 1


def _fetch_latest():
    url = os.environ.get("AGYAUTO_TARBALL") or "https://github.com/%s/archive/refs/heads/main.tar.gz" % REPO
    tmp = tempfile.mkdtemp(prefix="agyauto-up-")
    try:
        with urllib.request.urlopen(url, timeout=30) as r, open(os.path.join(tmp, "src.tgz"), "wb") as f:
            shutil.copyfileobj(r, f)
        with tarfile.open(os.path.join(tmp, "src.tgz")) as tf:
            for m in tf.getmembers():
                if m.name.startswith("/") or ".." in m.name.split("/"):
                    raise RuntimeError("unsafe path in archive")
            tf.extractall(tmp)
        roots = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        if len(roots) != 1 or not os.path.exists(os.path.join(tmp, roots[0], "VERSION")):
            raise RuntimeError("unexpected archive layout")
        return tmp, os.path.join(tmp, roots[0])
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def install_tree(src, dest_dir):
    """Atomically replace <dest_dir>/app with `src` and point the launcher at it."""
    os.makedirs(dest_dir, exist_ok=True)
    app, new, old = (os.path.join(dest_dir, n) for n in ("app", "app.new", "app.old"))
    for d in (new, old):
        shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(src, new, ignore=shutil.ignore_patterns(".git", "tests", "__pycache__", ".github"))
    if os.path.exists(app):
        os.rename(app, old)
    os.rename(new, app)
    shutil.rmtree(old, ignore_errors=True)
    os.chmod(os.path.join(app, "bin", "agyauto"), 0o755)
    link = paths.bin_link()
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.path.islink(link) or os.path.exists(link):
        os.unlink(link)
    os.symlink(os.path.join(app, "bin", "agyauto"), link)


def cmd_update(_argv):
    print("agyauto %s - checking for updates..." % __version__)
    try:
        tmp, src = _fetch_latest()
    except Exception as e:  # noqa: BLE001
        sys.exit("agyauto: update failed: %s" % e)
    try:
        with open(os.path.join(src, "VERSION")) as f:
            new = f.read().strip()
        if new == __version__:
            print("already up to date (%s)" % new)
            return 0
        install_tree(src, paths.install_dir())
        print("updated %s -> %s (running sessions keep using the old code until restarted)" % (__version__, new))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


def cmd_uninstall(argv):
    live = registry.sessions(cleanup=False)
    if live:
        print("note: %d session(s) are running; they keep working until their terminal closes." % len(live))
    link = paths.bin_link()
    if os.path.islink(link) and "agyauto" in os.path.realpath(link):
        os.unlink(link)
    shutil.rmtree(paths.install_dir(), ignore_errors=True)
    if "--purge" in argv:
        shutil.rmtree(paths.state_dir(), ignore_errors=True)
        shutil.rmtree(os.path.dirname(paths.config_file()), ignore_errors=True)
        print("removed agyauto, config and history")
    else:
        print("removed agyauto (config and history kept; use --purge to delete them)")
    return 0


def cmd_dashboard(_argv):
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return cmd_status([])
    from . import tui
    _lang()
    tui.run()
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return cmd_dashboard([])
    head = argv[0]
    if head in ("-h", "--help", "help"):
        print(HELP % __version__)
        return 0
    if head in ("-V", "--version", "version"):
        print(__version__)
        return 0
    if head == "_install" and len(argv) == 2:  # used by install.sh
        install_tree(argv[1], paths.install_dir())
        return 0
    if head == "run":
        return cmd_wrap(argv[1:])
    handlers = {"replay": cmd_replay, "dashboard": cmd_dashboard, "status": cmd_status, "history": cmd_history, "config": cmd_config,
                "lang": cmd_lang, "doctor": cmd_doctor, "update": cmd_update, "uninstall": cmd_uninstall}
    if head in handlers:
        return handlers[head](argv[1:]) or 0
    return cmd_wrap(argv)
