"""Run a command in its own pty and answer agy permission prompts by writing straight to that pty.

Nothing here depends on window focus or workspace: the keystroke goes into this session's pty only.
"""
import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import time
import tty

from . import config, history, matcher, notify, registry
from .redact import redact

_FOCUS = re.compile(rb"^(\x1b\[[IO])+$")  # terminal focus in/out reports are not user typing


def _winsz(fd):
    return fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\0" * 8)


def _exit_code(status):
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return 1


def run(cmd, name=None, danger=None, key_override=None):
    cfg = config.load()
    if key_override:
        cfg["key"] = key_override
    cfg_mtime = config.mtime()
    key = {"enter": b"\r", "1": b"1"}.get(cfg["key"], b"\r")
    pid_self = os.getpid()
    registry.init()
    db = history.connect()
    history.prune(db, int(cfg["retention_days"]))

    state = {
        "name": name or " ".join(cmd)[:60], "cmd": cmd, "started": time.time(),
        "approved": 0, "blocked": 0, "stalled": 0, "paused": False,
        "danger": cfg["danger_default"] if danger is None else danger,
        "last_event": "", "last_at": 0.0, "status": "watching", "cwd": os.getcwd(),
    }
    deny = [re.compile(p, re.I) for p in cfg["deny"] if p]

    child, fd = pty.fork()
    if child == 0:
        try:
            os.execvp(cmd[0], cmd)
        except OSError as e:
            sys.stderr.write("agyauto: cannot run %s: %s\n" % (cmd[0], e))
            os._exit(127)

    interactive = sys.stdin.isatty()
    old = None
    if interactive:
        try:
            fcntl.ioctl(fd, termios.TIOCSWINSZ, _winsz(0))
        except OSError:
            pass
        old = termios.tcgetattr(0)
        tty.setraw(0)

        def on_winch(*_):
            try:
                fcntl.ioctl(fd, termios.TIOCSWINSZ, _winsz(0))
                os.kill(child, signal.SIGWINCH)
            except OSError:
                pass
        signal.signal(signal.SIGWINCH, on_winch)

    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda s, _f: os.kill(child, s))

    match, view = "", ""            # `match` is cleared after answering, `view` feeds the live screen
    last_out = last_in = last_beat = last_view = 0.0
    view_dirty = False
    blocked_sig = stalled_sig = ""
    code = 0
    status = None

    def beat(now):
        state["status"] = ("paused" if state["paused"] else "danger" if state["danger"] else "watching")
        registry.publish(pid_self, state)

    def event(kind, ptype, command, k, screen="", question=""):
        command = command or (question or "")
        history.add(db, pid_self, state["name"], kind, ptype, command, k, screen)
        state["last_event"] = "%s %s" % (kind, (command or ptype).replace("\n", " ")[:80])
        state["last_at"] = time.time()

    try:
        beat(time.time())
        while True:
            try:
                r, _, _ = select.select([fd] + ([0] if interactive else []), [], [], 0.1)
            except InterruptedError:
                continue
            now = time.time()
            if fd not in r and status is None:
                # macOS never reports EOF on the pty master once the child is gone, so poll for the exit
                try:
                    wpid, wst = os.waitpid(child, os.WNOHANG)
                except ChildProcessError:
                    wpid, wst = child, 0
                if wpid:
                    status = wst
            if fd not in r and status is not None:
                break
            if fd in r:
                try:
                    d = os.read(fd, 65536)
                except OSError:
                    break
                if not d:
                    break
                os.write(1, d)
                txt = matcher.clean(d.decode("utf8", "replace"))
                match = (match + txt)[-4000:]
                view = (view + txt)[-12000:]
                last_out, view_dirty = now, True
            if 0 in r:
                d = os.read(0, 4096)
                if not d:
                    interactive = False
                else:
                    os.write(fd, d)
                    if not _FOCUS.match(d):
                        last_in = now

            if now - last_beat >= 1.0:
                last_beat = now
                ctl = registry.read_control(pid_self)
                if "paused" in ctl:
                    state["paused"] = bool(ctl["paused"])
                if "danger" in ctl:
                    state["danger"] = bool(ctl["danger"])
                if ctl.get("name"):
                    state["name"] = str(ctl["name"])[:60]
                m = config.mtime()
                if m != cfg_mtime:
                    cfg_mtime, cfg = m, config.load()
                    if key_override:
                        cfg["key"] = key_override
                    key = {"enter": b"\r", "1": b"1"}.get(cfg["key"], b"\r")
                    deny = [re.compile(p, re.I) for p in cfg["deny"] if p]
                if view_dirty and now - last_view >= 1.0:
                    last_view, view_dirty = now, False
                    registry.publish_screen(pid_self, redact("\n".join(view.splitlines()[-60:])))
                beat(now)

            quiet = last_out and now - last_out
            if not match or not quiet or quiet < cfg["delay"] or state["paused"]:
                continue
            if now - last_in < 1.0:
                continue  # a human is typing in this terminal: stay out of the way

            screen = match[-2500:]
            p = matcher.detect(screen, key)
            send, ptype, command, question = None, "", "", ""
            if p:
                send, ptype, command, question = p.key, p.kind, p.command, p.question
            elif state["danger"]:
                g = matcher.generic(screen)
                if g:
                    send, ptype, command = g, "generic", screen.strip().splitlines()[-1][:200]

            if send is not None:
                scope = command or (screen[-600:] if ptype in ("tool", "other", "generic") else "")
                if matcher.is_root_delete(scope) or any(rx.search(scope) for rx in deny):
                    sig = scope[-300:]
                    if sig != blocked_sig:
                        blocked_sig = sig
                        state["blocked"] += 1
                        event("BLOCKED", ptype, command, "", screen)
                        os.write(1, b"\a")
                        if cfg["notify"]:
                            notify.send("agyauto: BLOCKED", "%s: %s" % (state["name"], (command or "?")[:120]))
                    match = ""
                    continue
                os.write(fd, send)
                state["approved"] += 1
                event("APPROVED", ptype, command, send.decode("latin1").replace("\r", "enter").replace("\n", "ctrl+j"), question=question)
                match, blocked_sig, stalled_sig = "", "", ""
                continue

            if quiet >= cfg["stall_after"] and matcher.looks_stalled(screen):
                sig = screen[-300:]
                if sig != stalled_sig:
                    stalled_sig = sig
                    state["stalled"] += 1
                    event("STALLED", "unknown", "", "", screen)
    finally:
        if old is not None:
            termios.tcsetattr(0, termios.TCSADRAIN, old)
        registry.remove(pid_self)
        try:
            db.close()
        except Exception:
            pass
    if status is None:
        try:
            _, status = os.waitpid(child, 0)
        except ChildProcessError:
            status = 0
    return _exit_code(status)
