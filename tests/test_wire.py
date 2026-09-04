import json, os, shutil, tempfile, unittest
from wire import core


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class TestWire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.orig = {k: getattr(core, k) for k in ("SCAFFOLD", "SPECS", "CLAUDE_HOME", "EH_HOME")}
        core.SCAFFOLD = os.path.join(self.tmp, "scaffold")
        core.SPECS = os.path.join(self.tmp, "specs")
        core.CLAUDE_HOME = os.path.join(self.tmp, "claude")
        core.EH_HOME = os.path.join(self.tmp, "eh")
        # 더미 능력: 스킬 1 + 에이전트 1 + 훅 1
        w(os.path.join(core.SPECS, "dummy.md"), "# dummy\n")
        w(os.path.join(core.SCAFFOLD, "skills", "dummy-skill", "SKILL.md"),
          "---\nname: dummy-skill\ndescription: t\ncapability: dummy\n---\nbody\n")
        w(os.path.join(core.SCAFFOLD, "agents", "dummy-agent.md"),
          "---\nname: dummy-agent\ncapability: dummy\n---\nbody\n")
        w(os.path.join(core.SCAFFOLD, "hooks", "dummy.json"), json.dumps(
            {"capability": "dummy", "events": ["SessionStart"],
             "hook": {"type": "command", "command": "/bin/true", "async": True, "timeout": 3}}))
        # 기존 settings.json (무관한 훅 포함) — _save_settings 와 같은 포맷으로
        cfg = {"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other.sh"}]}]}}
        w(os.path.join(core.CLAUDE_HOME, "settings.json"), json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")

    def tearDown(self):
        for k, v in self.orig.items():
            setattr(core, k, v)
        shutil.rmtree(self.tmp)

    def _settings_text(self):
        return open(os.path.join(core.CLAUDE_HOME, "settings.json")).read()

    def test_roundtrip_diff_zero(self):
        before = self._settings_text()
        core.install("dummy")
        self.assertTrue(os.path.exists(os.path.join(core.CLAUDE_HOME, "skills", "dummy-skill", "SKILL.md")))
        self.assertTrue(os.path.exists(os.path.join(core.CLAUDE_HOME, "agents", "dummy-agent.md")))
        cfg = json.loads(self._settings_text())
        self.assertEqual(cfg["hooks"]["SessionStart"][0]["hooks"][0]["command"], "/bin/true")
        mid = self._settings_text()
        core.install("dummy")                       # 멱등: 두 번 설치해도 동일
        self.assertEqual(self._settings_text(), mid)
        self.assertEqual(len(json.loads(mid)["hooks"]["SessionStart"]), 1)
        core.uninstall("dummy")
        self.assertEqual(self._settings_text(), before)   # diff 0
        self.assertFalse(os.path.exists(os.path.join(core.CLAUDE_HOME, "skills", "dummy-skill")))
        self.assertFalse(os.path.exists(os.path.join(core.CLAUDE_HOME, "agents", "dummy-agent.md")))
        self.assertNotIn("dummy", json.load(open(os.path.join(core.EH_HOME, "wire.json"))))

    def test_requires_spec(self):
        os.remove(os.path.join(core.SPECS, "dummy.md"))
        with self.assertRaises(SystemExit):
            core.install("dummy")

    def test_refuses_foreign_skill(self):
        w(os.path.join(core.CLAUDE_HOME, "skills", "dummy-skill", "SKILL.md"), "someone else\n")
        with self.assertRaises(SystemExit):
            core.install("dummy")


if __name__ == "__main__":
    unittest.main()
