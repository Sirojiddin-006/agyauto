"""Minimal VT100/xterm screen emulator (stdlib only) used for the dashboard's live view.

TUIs such as agy redraw with cursor movement, so concatenating the raw stream gives broken fragments.
This keeps a real character grid plus a short scrollback and renders what a user would actually see.
It only understands what a text view needs: cursor motion, erase, insert/delete, scroll regions,
save/restore cursor. Colours and modes are ignored.
"""
import re
import unicodedata
from collections import deque

# text run | C0 control | CSI | OSC | other ESC sequence
_TOKEN = re.compile(
    r"([^\x00-\x1f\x7f\x9b]+)"
    r"|([\x00-\x1a\x1c-\x1f\x7f])"
    r"|\x1b\[([0-9;?<>=!]*)([ -/]*)([@-~])"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    r"|\x1b([()#][0-9A-Za-z]|[=>78MDEHc])"
)


def _width(ch):
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


class Screen:
    def __init__(self, rows=24, cols=80, scrollback=300):
        self.rows, self.cols = max(2, rows), max(10, cols)
        self.scroll = deque(maxlen=scrollback)
        self._carry = ""
        self.reset()

    def reset(self):
        self.grid = [[" "] * self.cols for _ in range(self.rows)]
        self.x = self.y = 0
        self.top, self.bot = 0, self.rows - 1
        self.saved = (0, 0)
        self.wrap_pending = False

    def resize(self, rows, cols):
        rows, cols = max(2, rows), max(10, cols)
        if (rows, cols) == (self.rows, self.cols):
            return
        new = [[" "] * cols for _ in range(rows)]
        for r in range(min(rows, self.rows)):
            for c in range(min(cols, self.cols)):
                new[r][c] = self.grid[r][c]
        self.grid, self.rows, self.cols = new, rows, cols
        self.x, self.y = min(self.x, cols - 1), min(self.y, rows - 1)
        self.top, self.bot = 0, rows - 1

    # ---- primitives ---------------------------------------------------------------------
    def _blank(self):
        return [" "] * self.cols

    def _scroll_up(self, n=1):
        for _ in range(n):
            line = self.grid.pop(self.top)
            if self.top == 0:
                self.scroll.append("".join(line).rstrip())
            self.grid.insert(self.bot, self._blank())

    def _scroll_down(self, n=1):
        for _ in range(n):
            self.grid.pop(self.bot)
            self.grid.insert(self.top, self._blank())

    def _lf(self):
        if self.y == self.bot:
            self._scroll_up()
        elif self.y < self.rows - 1:
            self.y += 1

    def _put(self, text):
        row = self.grid[self.y]
        for ch in text:
            w = _width(ch)
            if w == 0:
                # combining mark: attach to the previous cell
                px = self.x - 1 if not self.wrap_pending else self.x
                if 0 <= px < self.cols and row[px] != " ":
                    row[px] += ch
                continue
            if self.wrap_pending or self.x + w > self.cols:
                self.x = 0
                self._lf()
                row = self.grid[self.y]
                self.wrap_pending = False
            row[self.x] = ch
            if w == 2 and self.x + 1 < self.cols:
                row[self.x + 1] = ""
            self.x += w
            if self.x >= self.cols:
                self.x = self.cols - 1
                self.wrap_pending = True

    # ---- control / escape handling ------------------------------------------------------
    def _ctl(self, c):
        self.wrap_pending = False
        if c == "\n" or c == "\x0b" or c == "\x0c":
            self._lf()
        elif c == "\r":
            self.x = 0
        elif c == "\b":
            self.x = max(0, self.x - 1)
        elif c == "\t":
            self.x = min(self.cols - 1, (self.x // 8 + 1) * 8)

    def _csi(self, params, final):
        private = params[:1] in ("?", "<", ">", "=", "!")
        if private:
            return  # modes (cursor visibility, alt screen, bracketed paste, ...) are ignored
        a = [int(p) if p.isdigit() else 0 for p in params.split(";")] if params else []
        n = a[0] if a and a[0] else 1
        self.wrap_pending = False
        if final == "A":
            self.y = max(self.top if self.y >= self.top else 0, self.y - n)
        elif final == "B" or final == "e":
            self.y = min(self.bot if self.y <= self.bot else self.rows - 1, self.y + n)
        elif final == "C" or final == "a":
            self.x = min(self.cols - 1, self.x + n)
        elif final == "D":
            self.x = max(0, self.x - n)
        elif final == "E":
            self.y, self.x = min(self.rows - 1, self.y + n), 0
        elif final == "F":
            self.y, self.x = max(0, self.y - n), 0
        elif final == "G" or final == "`":
            self.x = min(self.cols - 1, max(0, n - 1))
        elif final == "d":
            self.y = min(self.rows - 1, max(0, n - 1))
        elif final in ("H", "f"):
            r = a[0] if a and a[0] else 1
            c = a[1] if len(a) > 1 and a[1] else 1
            self.y, self.x = min(self.rows - 1, r - 1), min(self.cols - 1, c - 1)
        elif final == "J":
            mode = a[0] if a else 0
            if mode == 0:
                self.grid[self.y][self.x:] = [" "] * (self.cols - self.x)
                for r in range(self.y + 1, self.rows):
                    self.grid[r] = self._blank()
            elif mode == 1:
                self.grid[self.y][:self.x + 1] = [" "] * (self.x + 1)
                for r in range(self.y):
                    self.grid[r] = self._blank()
            else:
                for r in range(self.rows):
                    self.grid[r] = self._blank()
        elif final == "K":
            mode = a[0] if a else 0
            if mode == 0:
                self.grid[self.y][self.x:] = [" "] * (self.cols - self.x)
            elif mode == 1:
                self.grid[self.y][:self.x + 1] = [" "] * (self.x + 1)
            else:
                self.grid[self.y] = self._blank()
        elif final == "L" and self.top <= self.y <= self.bot:
            for _ in range(min(n, self.bot - self.y + 1)):
                self.grid.pop(self.bot)
                self.grid.insert(self.y, self._blank())
        elif final == "M" and self.top <= self.y <= self.bot:
            for _ in range(min(n, self.bot - self.y + 1)):
                self.grid.pop(self.y)
                self.grid.insert(self.bot, self._blank())
        elif final == "P":
            row = self.grid[self.y]
            del row[self.x:self.x + n]
            row.extend([" "] * (self.cols - len(row)))
        elif final == "@":
            row = self.grid[self.y]
            row[self.x:self.x] = [" "] * n
            del row[self.cols:]
        elif final == "X":
            end = min(self.cols, self.x + n)
            self.grid[self.y][self.x:end] = [" "] * (end - self.x)
        elif final == "S":
            self._scroll_up(n)
        elif final == "T":
            self._scroll_down(n)
        elif final == "r":
            t = (a[0] if a and a[0] else 1) - 1
            b = (a[1] if len(a) > 1 and a[1] else self.rows) - 1
            if 0 <= t < b < self.rows:
                self.top, self.bot = t, b
            else:
                self.top, self.bot = 0, self.rows - 1
            self.y = self.x = 0
        elif final == "s":
            self.saved = (self.x, self.y)
        elif final == "u":
            self.x, self.y = self.saved
        # m (colours), n (reports), t (window ops), c, q ... are intentionally ignored

    def _esc(self, code):
        self.wrap_pending = False
        if code == "7":
            self.saved = (self.x, self.y)
        elif code == "8":
            self.x, self.y = self.saved
        elif code == "M":
            if self.y == self.top:
                self._scroll_down()
            elif self.y > 0:
                self.y -= 1
        elif code == "D":
            self._lf()
        elif code == "E":
            self.x = 0
            self._lf()
        elif code == "c":
            self.reset()

    # ---- public -------------------------------------------------------------------------
    def feed(self, data):
        data = self._carry + data
        self._carry = ""
        i = data.rfind("\x1b")
        if i >= 0 and i > len(data) - 64 and _TOKEN.match(data, i) is None:
            self._carry, data = data[i:], data[:i]  # escape sequence split across reads
        for m in _TOKEN.finditer(data):
            text, ctl, params, _inter, final, esc = m.groups()
            if text is not None:
                self._put(text)
            elif ctl is not None:
                self._ctl(ctl)
            elif final is not None:
                self._csi(params, final)
            elif esc is not None:
                self._esc(esc)

    def lines(self, tail=None):
        """Scrollback + visible screen as text lines, trailing blanks removed."""
        vis = ["".join(r).rstrip() for r in self.grid]
        while vis and not vis[-1]:
            vis.pop()
        out = list(self.scroll) + vis
        return out[-tail:] if tail else out

    def text(self, tail=None):
        return "\n".join(self.lines(tail))
