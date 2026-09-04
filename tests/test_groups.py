import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cctv.sources import terminal


class GroupWorkspaces(unittest.TestCase):
    def test_keeps_sidebar_order_and_buckets_ungrouped(self):
        ginfo = {"groups": {"g1": dict(id="g1", name="ETHAN", collapsed=False, pinned=False, order=0),
                            "g2": dict(id="g2", name="BIBIM", collapsed=True, pinned=False, order=1)},
                 "ws_group": {"a": "g1", "b": "g1", "c": None, "d": "g2", "e": "g1"}}
        ws = [dict(id=i) for i in "abcde"]
        out = terminal.group_workspaces(ws, ginfo)
        self.assertEqual([(g["title"], [w["id"] for w in g["workspaces"]]) for g in out],
                         [("ETHAN", ["a", "b", "e"]), (None, ["c"]), ("BIBIM", ["d"])])
        self.assertTrue(out[2]["collapsed"])

    def test_no_group_info(self):
        out = terminal.group_workspaces([dict(id="x"), dict(id="y")], {"groups": {}, "ws_group": {}})
        self.assertEqual(len(out), 1); self.assertIsNone(out[0]["title"]); self.assertEqual(len(out[0]["workspaces"]), 2)


if __name__ == "__main__":
    unittest.main()
