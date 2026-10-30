import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agyauto import matcher, redact  # noqa: E402

REAL = """● Ran (npx playwright test) (ctrl+o to expand)Command
────────────────────────────────────────────────────────────────────
Requesting permission for:
   npx playwright test tests/e2e/admin.e2e.ts --project=mobile-chrome

Run this command?
> 1. Yes, run command
  2. Yes, and always allow in this conversation for commands that start with 'npx playwright test
tests/e2e/admin.e2e.ts'
  3. Yes, and always allow for commands that start with 'npx' (Persist to settings.json)
  4. No, cancel  ↑/↓ Navigate · tab Amend · ctrl+g edit/expand command
esc to cancelGemini 3.8 Flash · high"""


class Detect(unittest.TestCase):
    def test_real_prompt(self):
        p = matcher.detect(REAL)
        self.assertEqual((p.kind, p.key), ("command", b"\r"))
        self.assertIn("playwright test", p.command)

    def test_key_one(self):
        self.assertEqual(matcher.detect(REAL, b"1").key, b"1")

    def test_never_picks_always_options(self):
        self.assertIsNone(matcher.detect(REAL.replace("> 1.", "  1.").replace("  2. Yes", "> 2. Yes")))
        self.assertIsNone(matcher.detect(REAL.replace("> 1.", "  1.").replace("  3. Yes", "> 3. Yes")))

    def test_cancel_selected_is_ignored(self):
        self.assertIsNone(matcher.detect(REAL.replace("> 1.", "  1.").replace("  4. No", "> 4. No")))

    def test_other_kinds(self):
        for q, o, k in [("Accept this file edit?", "Yes, accept this change", "edit"),
                        ("Allow creation of this file?", "Yes, allow creation", "create"),
                        ("Allow calling this tool?", "Yes, allow tool call", "tool")]:
            self.assertEqual(matcher.detect("diff...\n%s\n> 1. %s\n  2. No, reject\n" % (q, o)).kind, k)

    def test_plain_text_is_not_a_prompt(self):
        self.assertIsNone(matcher.detect("> yes I think so\nWhat now?\n"))
        self.assertIsNone(matcher.detect("Do you want tea?\n\n\n\n\n\n\n\n\n> Yes\n"))

    def test_trust_prompt_not_auto_approved(self):
        self.assertIsNone(matcher.detect("Do you trust the contents of this project?\n> Yes, I trust this folder\n  No, exit\n"))

    def test_clean_collapses_cursor_moves(self):
        s = matcher.clean("npm run check\x1b[2;1HRun this command?\x1b[3;1H\x1b[36m> 1. Yes, run command\x1b[0m")
        self.assertIn("\nRun this command?\n", s)
        self.assertIsNotNone(matcher.detect(s))


class RootDelete(unittest.TestCase):
    def test_blocked(self):
        for c in ["rm -rf /", "rm -rf /*", "sudo rm -fr /", "cd x && rm -rf /", "rm -r -f /", "rm -rf ~", "rm -rf $HOME",
                  "rm --recursive --force /", "rm -rf --no-preserve-root /x"]:
            self.assertTrue(matcher.is_root_delete(c), c)

    def test_allowed(self):
        for c in ["rm -rf /tmp/x", "rm -rf node_modules", "rm file", "rm -rf ~/proj", "echo rm -rf /x", "ls /"]:
            self.assertFalse(matcher.is_root_delete(c), c)


class Generic(unittest.TestCase):
    def test_ctrl_approve(self):
        self.assertEqual(matcher.generic("Deploy?\nPress ctrl+j to approve"), b"\n")

    def test_normal_footer_ignored(self):
        self.assertIsNone(matcher.generic("Working...\n(ctrl+o to expand)"))
        self.assertFalse(matcher.looks_stalled("done\n● Ran 2 commands (ctrl+o to expand)"))

    def test_yn(self):
        self.assertEqual(matcher.generic("Overwrite? (y/n)"), b"y\r")


class Redact(unittest.TestCase):
    def test_secrets(self):
        for s in ["curl https://api.telegram.org/bot8858694651:AAErYL_pP2hWabcdefghijklmnopqrstu/sendMessage",
                  "export API_KEY=abcd1234efgh", "Authorization: Bearer abcdefghijklmnop12345", "ghp_abcdefghijklmnopqrstuvwx1234"]:
            r = redact.redact(s)
            self.assertIn("redacted", r)
            self.assertNotIn("AAErYL", r)
            self.assertNotIn("abcd1234efgh", r)


if __name__ == "__main__":
    unittest.main()
