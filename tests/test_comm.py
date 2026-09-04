import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cctv.sources import transcript
from cctv import collect as C, bus

FX = os.path.join(os.path.dirname(__file__), "fixtures", "comm.jsonl")


class Comm(unittest.TestCase):
    def test_parse_send_and_recv_without_body(self):
        r = transcript.parse(FX)
        keys = sorted(r["comm"])
        self.assertEqual(keys, ["recv|uds:/tmp/cc-socks/222.sock", "recv|uds:/tmp/cc-socks/999.sock", "send|peer-c", "send|uds:/tmp/cc-socks/222.sock"])
        self.assertEqual(r["comm"]["recv|uds:/tmp/cc-socks/222.sock"]["name"], "peer-b")
        self.assertNotIn("SECRET", str(r["comm"]))

    def test_resolve_groups_live_peers_only(self):
        a = dict(sid="A", name="a", alive=True, started=1, sock="/tmp/cc-socks/111.sock", comm=transcript.parse(FX)["comm"])
        b = dict(sid="B", name="peer-b", alive=True, started=2, sock="/tmp/cc-socks/222.sock", comm={})
        c = dict(sid="C", name="peer-c", alive=True, started=3, sock="/tmp/cc-socks/333.sock", comm={})
        d = dict(sid="D", name="lonely", alive=True, started=4, sock="/tmp/cc-socks/444.sock", comm={})
        rows = [a, b, c, d]; C.resolve_comm(rows)
        self.assertEqual({p["sid"] for p in a["comm_peers"]}, {"B", "C"})
        self.assertEqual([o["label"] for o in a["comm_other"]], ["dead-x"])
        self.assertEqual((a["comm_group"], b["comm_group"], c["comm_group"]), (1, 1, 1))
        self.assertIsNone(d["comm_group"])

    def test_event_keeps_target_only(self):
        ev = bus.to_event({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "SendMessage", "tool_input": {"to": "waste-9c", "message": "SECRET"}})
        self.assertEqual(ev["to"], "waste-9c"); self.assertNotIn("SECRET", str(ev))


if __name__ == "__main__":
    unittest.main()


class ManualComm(unittest.TestCase):
    def test_manual_links_and_named_groups(self):
        a = dict(sid="A", name="a", alive=True, started=1, sock="", comm={})
        b = dict(sid="B", name="b", alive=True, started=2, sock="", comm={})
        c = dict(sid="C-old", name="c", alive=True, started=3, sock="", comm={})
        d = dict(sid="D", name="d", alive=True, started=4, sock="", comm={})
        man = {"groups": [{"id": "g1", "name": "프론트팀", "members": [{"sid": "A", "name": "a"}, {"sid": "GONE", "name": "c"}]}],
               "links": [{"a": {"sid": "B", "name": "b"}, "b": {"sid": "GONE2", "name": "c"}}]}
        rows = [a, b, c, d]; C.resolve_comm(rows, man)
        # 그룹(A,c-이름매칭) + 링크(B,c) → A,B,C 한 컴포넌트, 라벨은 수동 그룹 이름
        self.assertEqual(a["comm_group"], b["comm_group"]); self.assertEqual(b["comm_group"], c["comm_group"])
        self.assertEqual(a["comm_label"], "프론트팀")
        self.assertIsNone(d["comm_group"])
        self.assertTrue(any(p["sid"] == "C-old" and p.get("manual") for p in b["comm_peers"]))
