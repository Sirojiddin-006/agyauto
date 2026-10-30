"""btop-style curses dashboard."""
import curses
import locale
import os
import time

from . import __version__, config, history, registry
from .i18n import get_lang, set_lang, t

TABS = ["tab_sessions", "tab_live", "tab_history", "tab_stats", "tab_settings"]
KINDS = ["ALL", "APPROVED", "BLOCKED", "STALLED"]
SPARK = "▁▂▃▄▅▆▇█"
C_BORDER, C_TITLE, C_OK, C_WARN, C_BAD, C_DIM, C_ACC, C_SEL, C_BANNER = range(1, 10)


def fmt_dur(sec):
    sec = int(max(0, sec))
    if sec >= 86400:
        return "%dd%02dh" % (sec // 86400, sec % 86400 // 3600)
    if sec >= 3600:
        return "%dh%02dm" % (sec // 3600, sec % 3600 // 60)
    return "%dm%02ds" % (sec // 60, sec % 60)


def clip(s, n):
    s = s.replace("\n", " ").replace("\t", " ")
    return s if len(s) <= n else s[:max(0, n - 1)] + "…"


class App:
    def __init__(self, scr):
        self.scr = scr
        self.cfg = config.load()
        set_lang(self.cfg["lang"])
        self.db = history.connect()
        self.tab = 0
        self.sel_pid = None
        self.kind_i = 0
        self.text = ""
        self.hist_sel = 0
        self.set_sel = 0
        self.sessions = []
        self.msg = ("", 0)
        self.popup = None
        self._init_colors()
        curses.curs_set(0)
        scr.keypad(True)
        scr.timeout(500)

    # ---- drawing primitives -------------------------------------------------------------
    def _init_colors(self):
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        rich = curses.COLORS >= 256
        pairs = {
            C_BORDER: (37 if rich else curses.COLOR_CYAN, -1),
            C_TITLE: (255 if rich else curses.COLOR_WHITE, -1),
            C_OK: (78 if rich else curses.COLOR_GREEN, -1),
            C_WARN: (220 if rich else curses.COLOR_YELLOW, -1),
            C_BAD: (203 if rich else curses.COLOR_RED, -1),
            C_DIM: (244 if rich else curses.COLOR_WHITE, -1),
            C_ACC: (141 if rich else curses.COLOR_MAGENTA, -1),
            C_SEL: (16 if rich else curses.COLOR_BLACK, 37 if rich else curses.COLOR_CYAN),
            C_BANNER: (231 if rich else curses.COLOR_WHITE, 160 if rich else curses.COLOR_RED),
        }
        for i, (fg, bg) in pairs.items():
            try:
                curses.init_pair(i, fg, bg)
            except curses.error:
                pass

    def put(self, y, x, s, attr=0, maxw=None):
        h, w = self.scr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        n = (w - x) if maxw is None else min(maxw, w - x)
        if n <= 0:
            return
        try:
            self.scr.addstr(y, x, s[:n], attr)
        except curses.error:
            pass

    def box(self, y, x, h, w, title="", color=C_BORDER, right=""):
        if h < 3 or w < 4:
            return
        a = curses.color_pair(color)
        self.put(y, x, "╭" + "─" * (w - 2) + "╮", a)
        self.put(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", a)
        for i in range(1, h - 1):
            self.put(y + i, x, "│", a)
            self.put(y + i, x + w - 1, "│", a)
        if title:
            self.put(y, x + 2, " " + clip(title, w - 8) + " ", curses.color_pair(C_TITLE) | curses.A_BOLD)
        if right:
            self.put(y, x + w - len(right) - 4, " " + right + " ", curses.color_pair(C_DIM))

    def flash(self, text):
        self.msg = (text, time.time())

    # ---- data ---------------------------------------------------------------------------
    def refresh_data(self):
        self.sessions = registry.sessions()
        pids = [s["pid"] for s in self.sessions]
        if self.sel_pid not in pids:
            self.sel_pid = pids[0] if pids else None

    def selected(self):
        for s in self.sessions:
            if s["pid"] == self.sel_pid:
                return s
        return None

    def move_sel(self, d):
        pids = [s["pid"] for s in self.sessions]
        if pids:
            i = pids.index(self.sel_pid) if self.sel_pid in pids else 0
            self.sel_pid = pids[(i + d) % len(pids)]

    # ---- frame --------------------------------------------------------------------------
    def draw(self):
        scr = self.scr
        scr.erase()
        h, w = scr.getmaxyx()
        if h < 18 or w < 70:
            self.put(0, 0, t("too_small"), curses.color_pair(C_WARN))
            scr.refresh()
            return
        danger_n = sum(1 for s in self.sessions if s.get("danger"))
        # header
        self.put(0, 1, "◆ agyauto", curses.color_pair(C_ACC) | curses.A_BOLD)
        self.put(0, 11, "v" + __version__, curses.color_pair(C_DIM))
        x = 20
        compact = w < 100
        for i, key in enumerate(TABS):
            label = " %d %s " % (i + 1, t(key)) if i == self.tab or not compact else " %d " % (i + 1)
            self.put(0, x, label, curses.color_pair(C_SEL) | curses.A_BOLD if i == self.tab else curses.color_pair(C_DIM))
            x += len(label) + 1
        right = "%s  %s " % (get_lang().upper(), time.strftime("%H:%M:%S"))
        if x < w - len(right) - 1:
            self.put(0, w - len(right) - 1, right, curses.color_pair(C_DIM))
        top = 1
        if danger_n:
            self.put(1, 0, t("danger_banner").center(w), curses.color_pair(C_BANNER) | curses.A_BOLD)
            top = 2
        body_h = h - top - 1
        [self.draw_sessions, self.draw_live, self.draw_history, self.draw_stats, self.draw_settings][self.tab](top, body_h, w)
        self.draw_footer(h - 1, w)
        if self.popup:
            self.draw_popup(h, w)
        scr.refresh()
        dump = os.environ.get("AGYAUTO_DUMP")
        if dump:
            try:
                with open(dump, "w") as f:
                    for y in range(h):
                        f.write(scr.instr(y, 0, w * 4).decode("utf8", "replace").rstrip() + "\n")
            except (curses.error, OSError):
                pass

    def draw_footer(self, y, w):
        hints = {
            0: [("j/k", "k_nav"), ("p", "k_pause"), ("d", "k_danger"), ("r", "k_rename")],
            1: [("j/k", "k_nav"), ("p", "k_pause"), ("d", "k_danger")],
            2: [("j/k", "k_nav"), ("f", "k_filter"), ("/", "k_search"), ("Enter", "k_detail")],
            3: [], 4: [("j/k", "k_nav"), ("Enter", "k_lang")],
        }[self.tab]
        hints += [("1-5", "k_tabs"), ("L", "k_lang"), ("q", "k_quit")]
        x = 1
        for k, lab in hints:
            if x + len(k) + len(t(lab)) + 2 > w:
                break
            self.put(y, x, k, curses.color_pair(C_ACC) | curses.A_BOLD)
            self.put(y, x + len(k) + 1, t(lab), curses.color_pair(C_DIM))
            x += len(k) + len(t(lab)) + 4
        text, at = self.msg
        if text and time.time() - at < 4:
            self.put(y, max(x, w - len(text) - 2), text, curses.color_pair(C_WARN))

    # ---- tabs ---------------------------------------------------------------------------
    def state_cell(self, s):
        if s.get("stale"):
            return t("st_stale"), C_BAD
        st = s.get("status", "watching")
        if st == "danger":
            return t("st_danger"), C_BAD
        if st == "paused":
            return t("st_paused"), C_WARN
        return t("st_watching"), C_OK

    def draw_sessions(self, y, h, w):
        rows_h = min(max(len(self.sessions), 1) + 4, max(6, h * 6 // 10))
        self.box(y, 0, rows_h, w, t("tab_sessions"), right="%d" % len(self.sessions))
        cols = [(t("col_state"), 14), (t("col_pid"), 8), (t("col_name"), max(10, w - 14 - 8 - 9 - 10 - 9 - 9 - 30 - 6)),
                (t("col_uptime"), 9), (t("col_ok"), 10), (t("col_blocked"), 9), (t("col_stalled"), 9), (t("col_last"), 0)]
        x = 2
        for name, cw in cols:
            self.put(y + 1, x, name, curses.color_pair(C_DIM) | curses.A_BOLD)
            x += cw
        if not self.sessions:
            self.put(y + 3, 3, clip(t("no_sessions"), w - 6), curses.color_pair(C_DIM))
        now = time.time()
        for i, s in enumerate(self.sessions[:rows_h - 4]):
            row = y + 2 + i
            sel = s["pid"] == self.sel_pid
            base = curses.color_pair(C_SEL) if sel else 0
            if sel:
                self.put(row, 1, " " * (w - 2), base)
            label, col = self.state_cell(s)
            x = 2
            cells = ["● " + label, str(s["pid"]), s.get("name", ""), fmt_dur(now - s.get("started", now)),
                     str(s.get("approved", 0)), str(s.get("blocked", 0)), str(s.get("stalled", 0)), s.get("last_event", "")]
            for j, (c, (_, cw)) in enumerate(zip(cells, cols)):
                attr = base if sel else (curses.color_pair(col) if j == 0 else
                                         curses.color_pair(C_BAD) if j == 5 and s.get("blocked") else
                                         curses.color_pair(C_WARN) if j == 6 and s.get("stalled") else 0)
                self.put(row, x, clip(c, (cw - 1) if cw else w - x - 2), attr)
                x += cw
        self.draw_events(y + rows_h, h - rows_h, w, t("recent"), None)

    def draw_events(self, y, h, w, title, session_id):
        if h < 4:
            return
        self.box(y, 0, h, w, title)
        for i, r in enumerate(history.query(self.db, limit=h - 2, session_id=session_id)):
            _id, ts, _sid, sess, kind, ptype, cmd, _k, _scr = r
            col = {"APPROVED": C_OK, "BLOCKED": C_BAD, "STALLED": C_WARN}.get(kind, 0)
            self.put(y + 1 + i, 2, time.strftime("%H:%M:%S", time.localtime(ts)), curses.color_pair(C_DIM))
            self.put(y + 1 + i, 11, kind, curses.color_pair(col) | curses.A_BOLD, 9)
            tail = "%s  %s" % (clip(sess, 18), cmd or ptype) if session_id is None else (cmd or ptype)
            self.put(y + 1 + i, 21, clip(tail, w - 24))

    def draw_live(self, y, h, w):
        s = self.selected()
        wide = w >= 110
        lw = w * 65 // 100 if wide else w
        lh = h if wide else max(8, h * 65 // 100)
        title = "%s%s" % (t("live_title"), " - " + s["name"] if s else "")
        self.box(y, 0, lh, lw, title, color=C_BAD if s and s.get("danger") else C_BORDER)
        if s:
            lines = [l for l in registry.read_screen(s["pid"]).splitlines() if l.strip()]
            lines = lines[-(lh - 2):] or [t("no_screen")]
            for i, l in enumerate(lines):
                self.put(y + 1 + i, 2, clip(l, lw - 4))
        else:
            self.put(y + 1, 2, clip(t("no_sessions"), lw - 4), curses.color_pair(C_DIM))
        sid = s["pid"] if s else -1
        if wide:
            self._events_at(y, lw, h, w - lw, sid)
        else:
            self._events_at(y + lh, 0, h - lh, w, sid)

    def _events_at(self, y, x, h, w, sid):
        if h < 4:
            return
        self.box(y, x, h, w, t("events"))
        for i, r in enumerate(history.query(self.db, limit=h - 2, session_id=sid)):
            _id, ts, _s, _n, kind, ptype, cmd, _k, _scr = r
            col = {"APPROVED": C_OK, "BLOCKED": C_BAD, "STALLED": C_WARN}.get(kind, 0)
            self.put(y + 1 + i, x + 2, time.strftime("%H:%M:%S", time.localtime(ts)), curses.color_pair(C_DIM))
            self.put(y + 1 + i, x + 11, kind[:4], curses.color_pair(col) | curses.A_BOLD)
            self.put(y + 1 + i, x + 16, clip(cmd or ptype, w - 19))

    def draw_history(self, y, h, w):
        kind = KINDS[self.kind_i]
        info = "%s: %s%s" % (t("filter"), kind, "   %s: %s" % (t("search"), self.text) if self.text else "")
        self.box(y, 0, h, w, t("history_title"), right=info)
        rows = history.query(self.db, kind=kind, text=self.text, limit=h - 3)
        self.hist_sel = max(0, min(self.hist_sel, len(rows) - 1))
        self.hist_rows = rows
        heads = [(t("col_time"), 12), (t("col_kind"), 10), (t("col_session"), 21), (t("col_type"), 9), (t("col_command"), 0)]
        x = 2
        for name, cw in heads:
            self.put(y + 1, x, name, curses.color_pair(C_DIM) | curses.A_BOLD)
            x += cw
        for i, r in enumerate(rows):
            _id, ts, _sid, sess, k, ptype, cmd, _key, _scr = r
            row = y + 2 + i
            sel = i == self.hist_sel
            base = curses.color_pair(C_SEL) if sel else 0
            if sel:
                self.put(row, 1, " " * (w - 2), base)
            col = {"APPROVED": C_OK, "BLOCKED": C_BAD, "STALLED": C_WARN}.get(k, 0)
            self.put(row, 2, time.strftime("%m-%d %H:%M", time.localtime(ts)), base or curses.color_pair(C_DIM))
            self.put(row, 14, k, base or (curses.color_pair(col) | curses.A_BOLD))
            self.put(row, 24, clip(sess, 20), base)
            self.put(row, 45, clip(ptype, 8), base)
            self.put(row, 54, clip(cmd, w - 57), base)

    def draw_stats(self, y, h, w):
        tot = history.totals(self.db)
        self.box(y, 0, 5, w, t("stats_totals"))
        items = [(tot.get("today", 0), "today", C_OK), (tot.get("APPROVED", 0), "total_approved", C_OK),
                 (tot.get("BLOCKED", 0), "total_blocked", C_BAD), (tot.get("STALLED", 0), "total_stalled", C_WARN)]
        cw = max(18, (w - 4) // 4)
        for i, (n, lab, col) in enumerate(items):
            self.put(y + 1, 2 + i * cw, str(n), curses.color_pair(col) | curses.A_BOLD)
            self.put(y + 2, 2 + i * cw, clip(t(lab), cw - 2), curses.color_pair(C_DIM))
        hy = y + 5
        hh = 7
        self.box(hy, 0, hh, w, t("stats_hourly"))
        data = history.hourly(self.db, 24)
        mx = max(data) or 1
        cell = max(1, min(3, (w - 6) // 24))
        for i, v in enumerate(data):
            lvl = 0 if v == 0 else 1 + int((v / mx) * (len(SPARK) - 2))
            ch = SPARK[min(len(SPARK) - 1, lvl)] if v else "·"
            self.put(hy + 2, 3 + i * cell, ch * cell, curses.color_pair(C_OK if v else C_DIM))
            if i % 6 == 0:
                self.put(hy + 4, 3 + i * cell, "-%dh" % (24 - i), curses.color_pair(C_DIM))
        self.put(hy + 5, 3, "max %d/h" % mx, curses.color_pair(C_DIM))
        by = hy + hh
        bh = h - 5 - hh
        if bh < 4:
            return
        half = w // 2
        self.box(by, 0, bh, half, t("stats_sessions"))
        rows = history.per_session(self.db, bh - 2)
        top = max([r[1] for r in rows] or [1])
        for i, (name, c) in enumerate(rows):
            self.put(by + 1 + i, 2, clip(name, 18))
            bar = int((half - 32) * c / top)
            self.put(by + 1 + i, 21, "█" * max(1, bar) + " %d" % c, curses.color_pair(C_ACC))
        self.box(by, half, bh, w - half, t("stats_commands"))
        rows = history.top_commands(self.db, bh - 2)
        top = max([r[1] for r in rows] or [1])
        for i, (name, c) in enumerate(rows):
            self.put(by + 1 + i, half + 2, clip(name, 16))
            bar = int((w - half - 28) * c / top)
            self.put(by + 1 + i, half + 19, "█" * max(1, bar) + " %d" % c, curses.color_pair(C_OK))

    def settings_items(self):
        c = self.cfg
        onoff = lambda v: t("on") if v else t("off")
        return [
            ("lang", t("set_lang"), "English" if c["lang"] == "en" else "O'zbekcha"),
            ("key", t("set_key"), "Enter" if c["key"] == "enter" else "1"),
            ("delay", t("set_delay"), "%.1f" % c["delay"]),
            ("notify", t("set_notify"), onoff(c["notify"])),
            ("retention_days", t("set_retention"), str(c["retention_days"])),
            ("danger_default", t("set_danger"), onoff(c["danger_default"])),
            ("deny", t("set_deny"), "%d" % len(c["deny"])),
        ]

    def draw_settings(self, y, h, w):
        self.box(y, 0, h, w, t("tab_settings"), right=config_path_short())
        items = self.settings_items()
        self.set_sel = max(0, min(self.set_sel, len(items) - 1))
        for i, (_k, label, val) in enumerate(items):
            sel = i == self.set_sel
            base = curses.color_pair(C_SEL) if sel else 0
            if sel:
                self.put(y + 2 + i, 1, " " * (w - 2), base)
            self.put(y + 2 + i, 3, label, base)
            self.put(y + 2 + i, 38, val, base or (curses.color_pair(C_BAD) if _k == "danger_default" and self.cfg[_k]
                                                   else curses.color_pair(C_ACC) | curses.A_BOLD))
        r = y + 3 + len(items)
        self.put(r, 3, t("deny_always"), curses.color_pair(C_BAD))
        for j, rule in enumerate(self.cfg["deny"][:max(0, h - len(items) - 8)]):
            self.put(r + 1 + j, 5, "- " + clip(rule, w - 10))
        self.put(y + h - 2, 3, t("set_hint"), curses.color_pair(C_DIM))

    def draw_popup(self, h, w):
        title, lines = self.popup
        pw, ph = min(w - 4, 100), min(h - 4, max(8, len(lines) + 4))
        py, px = (h - ph) // 2, (w - pw) // 2
        for i in range(ph):
            self.put(py + i, px, " " * pw)
        self.box(py, px, ph, pw, title, color=C_ACC, right="Esc")
        for i, l in enumerate(lines[:ph - 2]):
            self.put(py + 1 + i, px + 2, clip(l, pw - 4))

    # ---- input --------------------------------------------------------------------------
    def read_line(self, prompt, initial=""):
        h, w = self.scr.getmaxyx()
        buf = initial
        curses.curs_set(1)
        self.scr.timeout(-1)
        try:
            while True:
                self.put(h - 1, 0, " " * (w - 1))
                self.put(h - 1, 1, prompt, curses.color_pair(C_WARN) | curses.A_BOLD)
                self.put(h - 1, 1 + len(prompt), buf[-(w - len(prompt) - 4):])
                self.scr.refresh()
                ch = self.scr.get_wch()
                if ch in ("\n", "\r") or ch == curses.KEY_ENTER:
                    return buf
                if ch == "\x1b":
                    return None
                if ch in ("\x7f", "\b") or ch == curses.KEY_BACKSPACE:
                    buf = buf[:-1]
                elif isinstance(ch, str) and ch.isprintable():
                    buf += ch
        finally:
            curses.curs_set(0)
            self.scr.timeout(500)

    def ask_yes(self, prompt):
        h, w = self.scr.getmaxyx()
        self.put(h - 1, 0, " " * (w - 1))
        self.put(h - 1, 1, clip(prompt, w - 3), curses.color_pair(C_BAD) | curses.A_BOLD)
        self.scr.refresh()
        self.scr.timeout(-1)
        try:
            return self.scr.getch() in (ord("y"), ord("Y"))
        finally:
            self.scr.timeout(500)

    def set_cfg(self, key, value):
        self.cfg[key] = value
        config.save(self.cfg)
        if key == "lang":
            set_lang(value)

    def settings_change(self, direction):
        key = self.settings_items()[self.set_sel][0]
        c = self.cfg
        if key == "lang":
            self.set_cfg("lang", "uz" if c["lang"] == "en" else "en")
        elif key == "key":
            self.set_cfg("key", "1" if c["key"] == "enter" else "enter")
        elif key == "delay":
            self.set_cfg("delay", round(min(3.0, max(0.1, c["delay"] + 0.1 * direction)), 1))
        elif key in ("notify", "danger_default"):
            if key == "danger_default" and not c[key] and not self.ask_yes(t("confirm_danger")):
                return
            self.set_cfg(key, not c[key])
        elif key == "retention_days":
            opts = [7, 30, 60, 90, 180, 365]
            i = opts.index(c[key]) if c[key] in opts else 3
            self.set_cfg(key, opts[(i + direction) % len(opts)])
        elif key == "deny":
            v = self.read_line(t("add_rule"))
            if v:
                self.set_cfg("deny", c["deny"] + [v])

    def handle(self, ch):
        if self.popup:
            if ch in (27, ord("q"), 10, 13):
                self.popup = None
            return True
        if ch in (ord("q"), ord("Q")):
            return False
        if ch in (ord("L"),):
            self.set_cfg("lang", "uz" if self.cfg["lang"] == "en" else "en")
        elif ord("1") <= ch <= ord("5"):
            self.tab = ch - ord("1")
        elif ch == 9:
            self.tab = (self.tab + 1) % len(TABS)
        elif ch == curses.KEY_BTAB:
            self.tab = (self.tab - 1) % len(TABS)
        elif ch in (ord("j"), curses.KEY_DOWN, ord("k"), curses.KEY_UP):
            d = 1 if ch in (ord("j"), curses.KEY_DOWN) else -1
            if self.tab in (0, 1):
                self.move_sel(d)
            elif self.tab == 2:
                self.hist_sel = max(0, self.hist_sel + d)
            elif self.tab == 4:
                self.set_sel = max(0, self.set_sel + d)
        elif self.tab in (0, 1):
            s = self.selected()
            if s and ch == ord("p"):
                paused = not s.get("paused")
                registry.write_control(s["pid"], paused=paused)
                self.flash("%s: %s" % (s["name"], t("st_paused") if paused else t("st_watching")))
            elif s and ch == ord("d"):
                if s.get("danger"):
                    registry.write_control(s["pid"], danger=False)
                elif self.ask_yes(t("confirm_danger")):
                    registry.write_control(s["pid"], danger=True)
            elif s and ch == ord("r") and self.tab == 0:
                v = self.read_line(t("rename_prompt"), s["name"])
                if v:
                    registry.write_control(s["pid"], name=v)
        elif self.tab == 2:
            if ch == ord("f"):
                self.kind_i = (self.kind_i + 1) % len(KINDS)
            elif ch == ord("/"):
                v = self.read_line(t("search_prompt"), self.text)
                if v is not None:
                    self.text = v
            elif ch in (10, 13, curses.KEY_ENTER) and getattr(self, "hist_rows", None):
                r = self.hist_rows[self.hist_sel]
                lines = ["%s  %s  %s  [%s]" % (time.strftime("%F %T", time.localtime(r[1])), r[4], r[3], r[5]), ""]
                lines += (r[6] or "").splitlines() + [""] + (r[8] or "").splitlines()
                self.popup = (t("detail_title"), lines)
        elif self.tab == 4:
            if ch in (10, 13, curses.KEY_ENTER, curses.KEY_RIGHT):
                self.settings_change(1)
            elif ch == curses.KEY_LEFT:
                self.settings_change(-1)
            elif ch == ord("a"):
                self.set_sel = len(self.settings_items()) - 1
                self.settings_change(1)
            elif ch == ord("x") and self.cfg["deny"]:
                self.set_cfg("deny", self.cfg["deny"][:-1])
        return True

    def run(self):
        while True:
            self.refresh_data()
            self.draw()
            ch = self.scr.getch()
            if ch == curses.KEY_RESIZE:
                continue
            if ch != -1 and not self.handle(ch):
                return


def config_path_short():
    from . import paths
    p = paths.config_file()
    home = os.path.expanduser("~")
    return "~" + p[len(home):] if p.startswith(home) else p


def run():
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")

    def main(scr):
        App(scr).run()
    curses.wrapper(main)
