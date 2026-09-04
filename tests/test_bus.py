import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cctv import bus


class EventSchema(unittest.TestCase):
    def test_keeps_metadata_only(self):
        ev = bus.to_event({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_use_id": "t1",
                           "tool_input": {"command": "SECRET"}, "tool_response": "BODY", "transcript_path": "/p", "cwd": "/x",
                           "agent_id": "a", "agent_type": "Explore"})
        self.assertEqual(ev["v"], 1)
        self.assertEqual((ev["sid"], ev["event"], ev["tool"], ev["tool_use_id"], ev["cwd"]), ("s1", "PostToolUse", "Bash", "t1", "/x"))
        self.assertNotIn("SECRET", str(ev)); self.assertNotIn("BODY", str(ev)); self.assertNotIn("transcript_path", ev)

    def test_failure_and_session_start_flags(self):
        self.assertIs(bus.to_event({"session_id": "s", "hook_event_name": "PostToolUseFailure"})["ok"], False)
        self.assertEqual(bus.to_event({"session_id": "s", "hook_event_name": "SessionStart", "source": "resume"})["source"], "resume")


if __name__ == "__main__":
    unittest.main()
