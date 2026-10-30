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
    elif scenario == "deny":
        out("GOT=%r\n" % prompt("Run this command?", "Yes, run command", "sudo rm -rf /"))
    elif scenario == "unknown":
        out("Deploy to production?\nPress ctrl+j to approve\n")
        out("GOT=%r\n" % key())
    elif scenario == "idle":
        out("hello\n")
        key(30)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
