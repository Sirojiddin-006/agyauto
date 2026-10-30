import json
import os
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

    def test_exit_code_passthrough(self):
        env = make_env()
        p, m = spawn([sys.executable, "-c", "import sys; sys.exit(7)"], env)
        drain(m, p, 5)
        self.assertEqual(p.wait(10), 7)


if __name__ == "__main__":
    unittest.main()
