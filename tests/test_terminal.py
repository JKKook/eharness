import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cctv.sources import terminal


class PsParse(unittest.TestCase):
    def test_extracts_tty_and_cmux_ids(self):
        line = "12136 ttys012 claude --foo PATH=/x CMUX_WORKSPACE_ID=CA83-1 CMUX_SURFACE_ID=D79E-2 HOME=/h"
        self.assertEqual(terminal.parse_ps_line(line), {12136: {"tty": "ttys012", "cmux_workspace_id": "CA83-1", "cmux_surface_id": "D79E-2"}})

    def test_headless_without_tty(self):
        self.assertEqual(terminal.parse_ps_line("99 ?? claude -p hi"), {99: {"tty": ""}})
        self.assertEqual(terminal.parse_ps_line("garbage"), {})


if __name__ == "__main__":
    unittest.main()
