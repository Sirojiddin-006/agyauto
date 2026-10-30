import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agyauto.vt import Screen  # noqa: E402


class VT(unittest.TestCase):
    def test_spinner_redraw_is_one_line(self):
        s = Screen(10, 40)
        for frame in ("Runni", "Running co", "Running comm", "Running command"):
            s.feed("\r\x1b[2K● " + frame)
        self.assertEqual(s.lines(), ["● Running command"])

    def test_cursor_up_rewrite(self):
        s = Screen(10, 40)
        s.feed("line1\r\nline2\r\nstatus: a\r\n")
        s.feed("\x1b[2A\r\x1b[Kstatus: b\x1b[2B\r")
        self.assertEqual(s.lines(), ["line1", "status: b", "status: a"])

    def test_absolute_positioning_and_erase(self):
        s = Screen(5, 20)
        s.feed("\x1b[2J\x1b[3;5Hhello\x1b[1;1Htitle\x1b[3;1H\x1b[K")
        self.assertEqual(s.lines(), ["title"])

    def test_scroll_keeps_scrollback(self):
        s = Screen(3, 20)
        s.feed("\r\n".join("row%d" % i for i in range(8)))
        self.assertEqual(s.lines(), ["row%d" % i for i in range(8)])
        self.assertEqual(s.lines(2), ["row6", "row7"])

    def test_wrap(self):
        s = Screen(4, 10)
        s.feed("abcdefghijKLM")
        self.assertEqual(s.lines(), ["abcdefghij", "KLM"])

    def test_sequence_split_across_reads(self):
        s = Screen(4, 20)
        s.feed("abc\x1b[")
        s.feed("2Kxyz")
        self.assertEqual(s.lines(), ["   xyz"])

    def test_colours_and_osc_ignored(self):
        s = Screen(4, 30)
        s.feed("\x1b]0;title\x07\x1b[1;36m> 1. Yes\x1b[0m")
        self.assertEqual(s.lines(), ["> 1. Yes"])

    def test_wide_and_combining(self):
        s = Screen(4, 10)
        s.feed("日本é")
        self.assertEqual(s.lines()[0], "日本é")

    def test_delete_insert_lines_and_region(self):
        s = Screen(5, 10)
        s.feed("\x1b[1;4r\x1b[1;1Ha\r\nb\r\nc\r\nd\r\ne")
        self.assertEqual(s.lines(), ["a", "b", "c", "d", "e"])

    def test_resize(self):
        s = Screen(4, 10)
        s.feed("hello")
        s.resize(6, 20)
        s.feed(" world")
        self.assertEqual(s.lines(), ["hello world"])


if __name__ == "__main__":
    unittest.main()
