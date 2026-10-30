import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import unittest

from helpers import FAKE, ROOT, drain, make_env, spawn


def history_rows(env):
    db = sqlite3.connect(env["AGYAUTO_STATE"] + "/history.db")
    return db.execute("SELECT kind,ptype,command,key FROM events ORDER BY id").fetchall()


class E2E(unittest.TestCase):
    def test_basic_prompts_get_option_one_only(self):
        env = make_env()
        p, m = spawn(["--name", "t1", sys.executable, FAKE, "basic"], env)
        out = drain(m, p, 20)
        p.wait(10)
        self.assertEqual(out.count(b"GOT=b'\\r'"), 5, out.decode(errors="replace"))
        rows = history_rows(env)
        self.assertEqual([r[0] for r in rows], ["APPROVED"] * 5)
        self.assertEqual([r[1] for r in rows], ["command", "edit", "create", "tool", "command"])
        self.assertEqual(rows[0][2], "npm run check")

    def test_key_one(self):
        env = make_env()
        p, m = spawn(["--key", "1", sys.executable, FAKE, "basic"], env)
        out = drain(m, p, 20)
        self.assertIn(b"GOT=b'1'", out)

    def test_root_delete_blocked_even_in_danger(self):
        env = make_env()
        p, m = spawn(["--danger", sys.executable, FAKE, "deny"], env)
        out = drain(m, p, 6)
        p.terminate()
        self.assertNotIn(b"GOT=b'\\r'", out)
        self.assertIn(b"\x07", out)
        rows = history_rows(env)
        self.assertEqual(rows[0][0], "BLOCKED")

    def test_unknown_prompt_only_in_danger(self):
        env = make_env()
        p, m = spawn(["--danger", sys.executable, FAKE, "unknown"], env)
        out = drain(m, p, 10)
        self.assertIn(b"GOT=b'\\n'", out)
        env2 = make_env()
        p2, m2 = spawn([sys.executable, FAKE, "unknown"], env2)
        out2 = drain(m2, p2, 10)
        self.assertNotIn(b"GOT=b'\\n'", out2)
        self.assertEqual([r[0] for r in history_rows(env2)], ["STALLED"])

    def _status(self, env):
        out = subprocess.run([sys.executable, "-m", "agyauto", "status", "--json"], cwd=ROOT, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        try:
            return json.loads(out.stdout)
        except ValueError:
            self.fail("status failed rc=%s out=%r err=%r" % (out.returncode, out.stdout, out.stderr))

    def _wait(self, env, cond, timeout=25):
        end, st = time.time() + timeout, []
        while time.time() < end:
            st = self._status(env)
            if cond(st):
                return st
            time.sleep(0.5)
        self.fail("condition not met, last status: %r" % (st,))

    def test_registry_and_live_control(self):
        env = make_env()
        p, m = spawn(["--name", "idle1", sys.executable, FAKE, "idle"], env)
        st = self._wait(env, lambda s: len(s) == 1)
        self.assertEqual(st[0]["name"], "idle1")
        ctl = os.path.join(env["AGYAUTO_STATE"], "sessions", "%d.ctl" % st[0]["pid"])
        with open(ctl, "w") as f:
            json.dump({"danger": True, "name": "renamed"}, f)
        st = self._wait(env, lambda s: s and s[0]["status"] == "danger" and s[0]["name"] == "renamed")
        p.terminate()
        p.wait(10)
        self._wait(env, lambda s: s == [])

    def test_live_screen_is_rendered_not_fragments(self):
        env = make_env()
        p, m = spawn(["--name", "spin", sys.executable, FAKE, "spinner"], env)
        sess = os.path.join(env["AGYAUTO_STATE"], "sessions")
        text, end = "", time.time() + 25
        while time.time() < end and "final line" not in text:
            drain(m, p, 0.5)
            for n in os.listdir(sess) if os.path.isdir(sess) else []:
                if n.endswith(".screen"):
                    with open(os.path.join(sess, n)) as f:
                        text = f.read()
        p.terminate()
        lines = [l for l in text.splitlines() if l.strip()]
        self.assertEqual(lines[0], "task started", text)
        self.assertEqual(lines[1], "thinking step 29", text)
        self.assertEqual(lines[-1], "final line", text)
        self.assertEqual(len(lines), 4, text)

    def test_live_snapshots_are_whole_frames(self):
        env = make_env()
        p, m = spawn([sys.executable, FAKE, "slowframe"], env)
        sess = os.path.join(env["AGYAUTO_STATE"], "sessions")
        seen, last, end = [], None, time.time() + 9
        while time.time() < end:
            drain(m, p, 0.05)
            for n in os.listdir(sess) if os.path.isdir(sess) else []:
                if n.endswith(".screen"):
                    with open(os.path.join(sess, n)) as f:
                        t = f.read()
                    if t != last:
                        seen.append(t)
                        last = t
        p.terminate()
        self.assertGreaterEqual(len(seen), 3, seen)
        # a heuristic (output gap) decides when a redraw is done, so tolerate one scheduler hiccup on a loaded CI box
        partial = [t for t in seen if len(t.split("\n")) != 2 or t.split("\n")[0].split()[1] != t.split("\n")[1].split()[1]]
        self.assertLessEqual(len(partial), max(1, len(seen) // 10), "partial frames published: %r" % partial)

    @unittest.skipUnless(shutil.which("tmux"), "tmux not installed")
    def test_tmux_identical_prompts_all_approved(self):
        # tmux only re-sends changed cells, so the raw stream lacks repeated prompts: the emulated screen must be used
        env = make_env()
        env["FAKE_LOG"] = os.path.join(env["HOME"], "fake.log")
        conf = os.path.join(env["HOME"], "tm.conf")
        with open(conf, "w") as f:
            f.write("set -g status off\n")
        sock = os.path.join(env["HOME"], "tm.sock")
        p, m = spawn(["tmux", "-S", sock, "-f", conf, "new-session", "%s %s same" % (sys.executable, FAKE)], env)
        try:
            end = time.time() + 25
            while time.time() < end and p.poll() is None:
                drain(m, p, 0.3)
        finally:
            p.terminate()
            subprocess.call(["tmux", "-S", sock, "kill-server"], stderr=subprocess.DEVNULL)
        with open(env["FAKE_LOG"]) as f:
            self.assertEqual(f.read().split(), ["GOT0=b'\\r'", "GOT1=b'\\r'", "GOT2=b'\\r'"])

    def test_record_and_replay(self):
        env = make_env()
        rec = os.path.join(env["HOME"], "rec.bin")
        p, m = spawn(["--record", rec, sys.executable, FAKE, "spinner"], env)
        drain(m, p, 25, until=b"final line\r\n")
        p.terminate()
        p.wait(10)
        out = subprocess.run([sys.executable, "-m", "agyauto", "replay", rec], cwd=ROOT, env=env,
                             stdout=subprocess.PIPE, universal_newlines=True).stdout
        self.assertEqual([l for l in out.splitlines() if l.strip()][0], "task started", out)
        self.assertIn("final line", out)

    def test_session_reports_version(self):
        env = make_env()
        p, m = spawn([sys.executable, FAKE, "idle"], env)
        st = self._wait(env, lambda s: len(s) == 1)
        p.terminate()
        with open(os.path.join(ROOT, "VERSION")) as f:
            self.assertEqual(st[0]["version"], f.read().strip())

    def test_exit_code_passthrough(self):
        env = make_env()
        p, m = spawn([sys.executable, "-c", "import sys; sys.exit(7)"], env)
        drain(m, p, 5)
        self.assertEqual(p.wait(10), 7)


if __name__ == "__main__":
    unittest.main()
