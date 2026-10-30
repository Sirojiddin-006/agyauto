#!/usr/bin/env python3
"""Stand-in for agy: prints permission prompts shaped like the real ones and reports which key arrived."""
import os
import sys
import termios
import tty

scenario = sys.argv[1] if len(sys.argv) > 1 else "basic"
fd = 0
old = termios.tcgetattr(fd)
tty.setraw(fd)


def out(s):
    os.write(1, s.replace("\n", "\r\n").encode())


def key(timeout=6):
    import select
    r, _, _ = select.select([fd], [], [], timeout)
    return os.read(fd, 16) if r else b""


def prompt(question, opt1, cmd=None):
    if cmd is not None:
        out("Requesting permission for:\n   %s\n\n" % cmd)
    out("%s\n> 1. %s\n  2. Yes, and always allow in this conversation for commands that start with 'x'\n"
        "  3. Yes, and always allow for commands that start with 'x' (Persist to settings.json)\n"
        "  4. No, cancel  ↑/↓ Navigate · tab Amend · ctrl+g edit/expand command\nesc to cancel\n" % (question, opt1))
    return key()


try:
    if scenario == "basic":
        for q, o, c in [("Run this command?", "Yes, run command", "npm run check"),
                        ("Accept this file edit?", "Yes, accept this change", None),
                        ("Allow creation of this file?", "Yes, allow creation", None),
                        ("Allow calling this tool?", "Yes, allow tool call", None),
                        ("Run this command?", "Yes, run command", "npm run check")]:
            out("GOT=%r\n" % prompt(q, o, c))
    elif scenario == "overlay":
        # second prompt is drawn over the first in place; under tmux only the changed cells reach the wrapper
        def frame(cmd):
            lines = ["Requesting permission for:", "   " + cmd, "", "Run this command?", "> 1. Yes, run command",
                     "  2. Yes, and always allow in this conversation for commands that start with 'npm'",
                     "  3. Yes, and always allow for commands that start with 'npm' (Persist to settings.json)",
                     "  4. No, cancel  \u2191/\u2193 Navigate", "esc to cancel"]
            return lines
        out("\x1b[2J\x1b[H")
        for n, cmd in enumerate(["npm run lint", "npm run build", "npm run test"]):
            for i, l in enumerate(frame(cmd)):
                out("\x1b[%d;1H\x1b[2K%s" % (i + 1, l))
            out("GOT%d=%r\x1b[12;1H\x1b[2K" % (n, key(8)))
            out("\x1b[11;1H")
    elif scenario == "same":
        # three IDENTICAL prompts; the screen never changes between them, so under tmux the wrapper's raw
        # stream carries nothing after the first one
        for i in range(3):
            if i == 0:
                out("\x1b[2J\x1b[H")
                for j, l in enumerate(["Requesting permission for:", "   node -e 'x'", "", "Run this command?", "> 1. Yes, run command",
                                       "  2. Yes, and always allow in this conversation for commands that start with 'node'",
                                       "  3. Yes, and always allow for commands that start with 'node' (Persist to settings.json)",
                                       "  4. No, cancel  \u2191/\u2193 Navigate", "esc to cancel"]):
                    out("\x1b[%d;1H%s" % (j + 1, l))
            k = key(10)
            with open(os.environ.get("FAKE_LOG", "/dev/null"), "a") as f:
                f.write("GOT%d=%r\n" % (i, k))
    elif scenario == "deny":
        out("GOT=%r\n" % prompt("Run this command?", "Yes, run command", "sudo rm -rf /"))
    elif scenario == "unknown":
        out("Deploy to production?\nPress ctrl+j to approve\n")
        out("GOT=%r\n" % key())
    elif scenario == "spinner":
        import time
        out("task started\n\n")
        for i in range(30):
            out("\r\x1b[2K\x1b[36m\u280b\x1b[0m Running command (%ds)" % i)
            out("\x1b[1A\x1b[2K\rthinking step %d\x1b[1B\r" % i)
            time.sleep(0.05)
        out("\r\nfinal line\r\n")
        key(30)
    elif scenario == "slowframe":
        # every frame is written in two halves 5 ms apart (as happens over ssh / under tmux)
        import time
        for i in range(60):
            out("\x1b[H\x1b[Jframe %d begin" % i)
            time.sleep(0.005)
            out("\r\nframe %d end" % i)
            time.sleep(0.11)
        key(30)
    elif scenario == "idle":
        out("hello\n")
        key(30)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
