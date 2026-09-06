import json, os, shutil, subprocess, tempfile, unittest
from install import merge_settings

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
INSTALL = os.path.join(ROOT, "install")


class TestInstall(unittest.TestCase):
    def test_scripts_syntax(self):
        for p in [os.path.join(INSTALL, "install.sh"), os.path.join(INSTALL, "assets", "statusline.sh")] + \
                 [os.path.join(INSTALL, "assets", "hooks", f) for f in os.listdir(os.path.join(INSTALL, "assets", "hooks"))]:
            self.assertEqual(subprocess.run(["bash", "-n", p], capture_output=True).returncode, 0, p)

    def test_merge_idempotent_and_preserves(self):
        cfg = {"model": "x", "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "~/.claude/hooks/tool-start.sh"}]}],
                                       "Stop": [{"hooks": [{"type": "command", "command": "other.sh"}]}]}}
        add = json.load(open(os.path.join(INSTALL, "assets", "settings-snippet.json")))
        cfg, n = merge_settings.merge(cfg, add)
        self.assertEqual(n, 4)                                   # 훅 3(중복 1 제외) + statusLine 1
        self.assertEqual(len(cfg["hooks"]["PreToolUse"]), 1)     # 중복 안 붙음
        self.assertEqual(cfg["hooks"]["Stop"][0]["hooks"][0]["command"], "other.sh")   # 기존 보존
        self.assertEqual(cfg["model"], "x")
        cfg2, n2 = merge_settings.merge(json.loads(json.dumps(cfg)), add)
        self.assertEqual((n2, cfg2), (0, cfg))

    def test_check_reports_eight_items(self):
        tmp = tempfile.mkdtemp()
        try:
            env = {**os.environ, "HOME": tmp, "EHARNESS_CLAUDE_HOME": os.path.join(tmp, ".claude"), "EHARNESS_PORT": "1"}
            r = subprocess.run(["bash", os.path.join(INSTALL, "install.sh"), "--check"], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 1)
            self.assertIn("결과: 0/8 통과", r.stdout)
        finally:
            shutil.rmtree(tmp)

    def test_ps1_same_check_labels(self):
        """install.ps1 의 검증 8항목이 install.sh 와 같은 이름·순서 — 플랫폼 간 '같은 설치' 기준."""
        import re
        sh = re.findall(r'^\s+t "([^"$]+)', open(os.path.join(INSTALL, "install.sh")).read(), re.M)
        ps = re.findall(r'^\s+T "([^"$]+)', open(os.path.join(INSTALL, "install.ps1")).read(), re.M)
        self.assertEqual(len(sh), 8); self.assertEqual([x.strip() for x in sh], [x.strip() for x in ps])
