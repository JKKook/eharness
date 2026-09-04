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

    def test_g1_skill_name(self):
        ev = bus.to_event({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Skill",
                           "tool_input": {"skill": "cctv-register", "args": "SECRET"}})
        self.assertEqual(ev["skill"], "cctv-register")
        self.assertNotIn("SECRET", str(ev))

    def test_g2_agent_type_fallbacks(self):
        ev = bus.to_event({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Agent",
                           "tool_input": {"subagent_type": "cctv-status", "prompt": "SECRET"}})
        self.assertEqual(ev["agent_type"], "cctv-status")
        self.assertNotIn("SECRET", str(ev))
        ev2 = bus.to_event({"session_id": "s", "hook_event_name": "SubagentStop", "subagent_type": "Explore"})
        self.assertEqual(ev2["agent_type"], "Explore")

    def test_g3_event_name_normalized(self):
        self.assertEqual(bus.to_event({"session_id": "s", "hook_event_name": "sessionEnd"})["event"], "SessionEnd")
        self.assertEqual(bus.to_event({"session_id": "s", "hook_event_name": "MysteryEvent"})["event"], "MysteryEvent")

    def test_g4_notification_message(self):
        ev = bus.to_event({"session_id": "s", "hook_event_name": "Notification", "message": "Claude needs your permission to use Bash"})
        self.assertTrue(ev["msg"].startswith("Claude needs your permission"))

    def test_g5_uds_reply_name(self):
        import json, tempfile
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, "sessions"))
        with open(os.path.join(tmp, "sessions", "12345.json"), "w") as f:
            json.dump({"sessionId": "x", "name": "leader-ab"}, f)
        orig = bus.CLAUDE_HOME
        try:
            bus.CLAUDE_HOME = tmp
            ev = bus.to_event({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "SendMessage",
                               "tool_input": {"to": "uds:/tmp/cc-socks/12345.sock", "message": "SECRET"}})
        finally:
            bus.CLAUDE_HOME = orig
        self.assertEqual(ev["to_name"], "leader-ab")
        self.assertNotIn("SECRET", str(ev))


if __name__ == "__main__":
    unittest.main()
