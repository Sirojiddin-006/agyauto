"""Pure prompt-matching logic (no I/O) so it can be unit-tested against recorded screens."""
import re
from collections import namedtuple

# CSI sequences that move the cursor to another line become newlines, "cursor forward" becomes a
# space, everything else (colours, modes, OSC titles) is dropped.
_NEWLINE_CSI = re.compile(r"\x1b\[[0-9;]*[ABEFHdf]")
_SPACE_CSI = re.compile(r"\x1b\[[0-9;]*C")
_ANSI = re.compile(r"\x1b\[[0-9;?<>=]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Z0-9]|\x1b[=>78M]")


def clean(data):
    """Terminal bytes (decoded) -> plain text suitable for matching and display."""
    data = _NEWLINE_CSI.sub("\n", data)
    data = _SPACE_CSI.sub(" ", data)
    data = _ANSI.sub("", data)
    data = data.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[\x00-\x08\x0b-\x1a\x1c-\x1f\x7f]", "", data)


Prompt = namedtuple("Prompt", "kind command question key")  # key: bytes to send

_SELECTED = re.compile(r"^[ \t]*[>❯›▶●◉][ \t]*(?:(\d+)[.)][ \t]*)?(\S.*)$", re.M)
_YES = re.compile(r"^(yes|allow|accept|approve|run|proceed|ok|ha)\b", re.I)
_PERSIST = re.compile(r"always|don'?t ask|persist|settings\.json|for this (session|conversation)|and remember", re.I)
_QUESTION = re.compile(r"^[ \t]*(\S.*\?)[ \t]*$", re.M)
_KINDS = [
    (re.compile(r"run this command", re.I), "command"),
    (re.compile(r"file edit|accept this", re.I), "edit"),
    (re.compile(r"creation of this file|create (this|the) file", re.I), "create"),
    (re.compile(r"calling this tool|tool call", re.I), "tool"),
]
_ASK = re.compile(r"permission|allow|approve|accept|do you want|would you like|run this|execute|confirm|proceed", re.I)

# Things that must never be auto-approved, not even in dangermode: deleting the filesystem root / home.
_ROOT_TARGETS = {"/", "/*", "/.", "/..", "~", "~/", "~/*", "$HOME", "${HOME}", "$HOME/", "$HOME/*", "${HOME}/*"}
_SPLIT = re.compile(r"&&|\|\||[;|&\n(){}`]|\$\(")


def is_root_delete(text):
    if "--no-preserve-root" in text:
        return True
    for seg in _SPLIT.split(text):
        toks = seg.replace('"', " ").replace("'", " ").split()
        for i, t in enumerate(toks):
            if t.rsplit("/", 1)[-1] != "rm":
                continue
            args = toks[i + 1:]
            recursive = any((a.startswith("--") and a == "--recursive") or
                            (a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a))
                            for a in args if a.startswith("-"))
            if recursive and any(a in _ROOT_TARGETS or re.fullmatch(r"/+\*?", a) for a in args if not a.startswith("-")):
                return True
    return False


def _section(screen, q_start):
    """Text of the command that is being asked about: from 'Requesting permission for:' to the question."""
    head = screen[:q_start]
    i = head.rfind("Requesting permission for:")
    if i >= 0:
        body = head[i + len("Requesting permission for:"):]
    else:
        return ""
    return "\n".join(l.strip() for l in body.splitlines() if l.strip())[:2000]


_OPTION = re.compile(r"^[ \t]*(\d+)[.)][ \t]+(\S.*)$", re.M)


def _detect_unmarked(screen, key):
    """Newer agy builds draw the menu without a '>' marker (the cursor is colour only, which the
    emulated screen loses): "Accept this file edit?" / " 1. Yes, accept this change" / "  2. No, ...".
    A menu is still only answered when: a permission question sits right above it, option 1 is a
    plain 'Yes' (not an 'always'/persist one), options are numbered 1..n, NO option carries a marker
    (a marked option is handled by the strict path, which may refuse it), and only a short footer follows.
    The cursor starts on option 1, so the default answer is Enter (or '1' if configured)."""
    opts = list(_OPTION.finditer(screen))
    first = None
    for i in range(len(opts) - 1, -1, -1):
        if opts[i].group(1) == "1":
            first = i
            break
    if first is None:
        return None
    block = opts[first:]
    if len(block) < 2 or [m.group(1) for m in block] != [str(n) for n in range(1, len(block) + 1)]:
        return None
    for m in block:  # any marker on an option line -> not our case
        line = screen[m.start():m.end()]
        if _SELECTED.match(line):
            return None
    # the option lines must be contiguous (only option continuation lines in between)
    if block[-1].end() - block[0].start() > 1500:
        return None
    text = block[0].group(2).strip()
    if not _YES.match(text) or _PERSIST.search(text):
        return None
    if sum(1 for l in screen[block[-1].end():].splitlines() if l.strip()) > 8:
        return None
    qs = list(_QUESTION.finditer(screen[:block[0].start()]))
    question = qs[-1] if qs else None
    if question is None or not _ASK.search(question.group(1)) or screen[question.end():block[0].start()].count("\n") > 3:
        return None
    kind = "other"
    for rx, k in _KINDS:
        if rx.search(question.group(1)):
            kind = k
            break
    return Prompt(kind, _section(screen, question.start()), question.group(1).strip(), key if key in (b"\r", b"1") else b"\r")


def detect(screen, key=b"\r"):
    """Return a Prompt if the screen ends in an approvable permission prompt, else None.

    Only ever answers option 1 (Enter or '1'); 'always allow' options are never chosen.
    """
    screen = screen[-2500:]
    p = _detect_marked(screen, key)
    if p is None and not _numbered_marker_after_question(screen):
        p = _detect_unmarked(screen, key)
    return p


def _numbered_marker_after_question(screen):
    """True if any numbered option line (e.g. '> 2. No') carries a selection marker."""
    return any(m.group(1) for m in _SELECTED.finditer(screen))


def _detect_marked(screen, key):
    sel = None
    for m in _SELECTED.finditer(screen):
        sel = m
    if sel is None:
        return None
    num, text = sel.group(1), sel.group(2).strip()
    if (num not in (None, "1")) or not _YES.match(text) or _PERSIST.search(text):
        return None
    qs = [m for m in _QUESTION.finditer(screen[:sel.start()])]
    question = qs[-1] if qs else None
    if question is None or not _ASK.search(question.group(1)) or screen[question.end():sel.start()].count("\n") > 6:
        return None
    kind = "other"
    for rx, k in _KINDS:
        if rx.search(question.group(1)):
            kind = k
            break
    cmd = _section(screen, question.start())
    k = key if (key == b"\r" or num == "1") else b"\r"
    return Prompt(kind, cmd, question.group(1).strip(), k)


# --- generic (dangermode) and stall detection -------------------------------------------------
_HINTS = [
    (re.compile(r"\(y/n\)|\[y/n\]|\(yes/no\)", re.I), b"y\r"),
    (re.compile(r"\[y/N\]|\[Y/n\]"), b"y\r"),
    (re.compile(r"press (?:enter|return)\b|enter to (?:confirm|continue|accept|approve|proceed|run|allow)", re.I), b"\r"),
    (re.compile(r"press any key", re.I), b"\r"),
]
_CTRL = re.compile(r"ctrl\+([a-z])\s+(?:to\s+)?(approve|accept|confirm|continue|proceed|submit|run|execute|allow|yes|send)\b", re.I)
_ANY_HINT = re.compile(r"ctrl\+[a-z]\b|esc to cancel|navigate|\(y/n\)|\[y/n\]|press |enter to|continue\?|confirm", re.I)
_NORMAL_FOOTER = re.compile(r"ctrl\+o to expand|ctrl\+g edit", re.I)


def _footer(screen, n=4):
    lines = [l for l in screen.splitlines() if l.strip()]
    return "\n".join(lines[-n:])


def generic(screen):
    """Dangermode fallback for prompts we have no recorded shape for. Returns bytes to send or None."""
    foot = _footer(screen)
    m = _CTRL.search(foot)
    if m:
        return bytes([ord(m.group(1).lower()) - 96])
    for rx, k in _HINTS:
        if rx.search(foot):
            return k
    return None


def looks_stalled(screen):
    """A key-hint footer is on screen but nothing handled it (used to record unknown prompt shapes)."""
    foot = _footer(screen)
    return bool(_ANY_HINT.search(foot)) and not (_NORMAL_FOOTER.search(foot) and "?" not in foot)
