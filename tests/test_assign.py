"""세션 그룹 배정(assign_group): 이동·해제·이름 재매칭·빈 그룹 소멸."""
import os, tempfile, unittest
from unittest import mock
from cctv import manual


class TestAssignGroup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(manual, "PATH", os.path.join(self.tmp.name, "manual.json"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_assign_move_unassign(self):
        out = manual.assign_group("s1", "n1", "A")
        self.assertEqual(out["groups"][0]["name"], "A")
        out = manual.assign_group("s2", "n2", "A")
        self.assertEqual(len(out["groups"][0]["members"]), 2)
        out = manual.assign_group("s1", "n1", "B")            # 이동: A에서 빠지고 B로
        a = next(g for g in out["groups"] if g["name"] == "A")
        self.assertEqual([m["sid"] for m in a["members"]], ["s2"])
        self.assertEqual([m["sid"] for m in next(g for g in out["groups"] if g["name"] == "B")["members"]], ["s1"])
        out = manual.assign_group("s2", "n2", None)           # 해제 → 빈 A 소멸
        self.assertEqual([g["name"] for g in out["groups"]], ["B"])

    def test_name_rematch(self):
        manual.assign_group("old-sid", "n1", "A")
        out = manual.assign_group("new-sid", "n1", "B")       # 재시작(sid 변경) → 이름으로 옮겨짐, 중복 없음
        self.assertEqual([g["name"] for g in out["groups"]], ["B"])
        self.assertEqual(out["groups"][0]["members"], [{"sid": "new-sid", "name": "n1"}])
