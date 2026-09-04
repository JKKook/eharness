import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cctv.sources import transcript

FX = os.path.join(os.path.dirname(__file__), "fixtures")


class TranscriptEdgeCases(unittest.TestCase):
    def test_zero_usage_tail_does_not_reset_ctx(self):
        r = transcript.parse(os.path.join(FX, "zero_usage_tail.jsonl"))
        self.assertEqual(r["ctx"], 2 + 196726 + 943)
        self.assertEqual(r["title"], "이미지 파이프라인 상한선")
        self.assertEqual(dict(r["tools"]), {"Edit": 1, "Bash": 1})
        self.assertEqual(r["turns"], 1)

    def test_no_title_falls_back_to_last_user_text(self):
        r = transcript.parse(os.path.join(FX, "no_title_resumed.jsonl"))
        self.assertEqual(r["title"], "")
        self.assertEqual(r["last_user"], "`/tabs` 로 이미 연결된 Chrome 탭 정리")   # system-reminder·tool_result 제외
        self.assertEqual(r["ctx"], 10 + 150000 + 2000)
        self.assertEqual(r["turns"], 3)                                          # 깨진 줄은 무시하고 계속

    def test_open_tasks_bg_survives_ack_done_kept_until_next_prompt(self):
        r = transcript.parse(os.path.join(FX, "tasks_open.jsonl"))
        # fg_old 는 tool_result 로, bg1 은 task-notification 으로 완료 표시 — 다음 사용자 입력 전까지 목록에 유지
        self.assertEqual([(t["tool"], t["bg"], bool(t.get("done"))) for t in r["tasks"]],
                         [("Bash", False, True), ("Agent", True, False), ("Bash", True, True), ("Bash", False, False)])

    def test_user_prompt_expires_done_and_stale_fg_keeps_running_bg(self):
        r = transcript.parse(os.path.join(FX, "tasks_wipe.jsonl"))
        # bgA(완료)·fgC(완료)는 다음 사용자 턴에 일괄 만료, 실행 중 bgB(Agent)만 남는다
        self.assertEqual([(t["tool"], t["bg"], bool(t.get("done"))) for t in r["tasks"]],
                         [("Agent", True, False)])

    def test_user_turn_closes_stale_foreground_tasks(self):
        r = transcript.parse(os.path.join(FX, "no_title_resumed.jsonl"))
        self.assertTrue(all(t["bg"] or t.get("done") for t in r["tasks"]))

    def test_missing_transcript_is_empty_not_error(self):
        r = transcript.parse(os.path.join(FX, "does-not-exist.jsonl"))
        self.assertEqual(r["ctx"], 0)
        self.assertEqual(r["turns"], 0)
        self.assertEqual(len(r["tools"]), 0)


if __name__ == "__main__":
    unittest.main()
