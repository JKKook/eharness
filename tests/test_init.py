import os, shutil, socket, subprocess, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
INIT = os.path.join(ROOT, "scaffold", "skills", "cctv-init", "init.sh")


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class TestInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = {**os.environ, "EHARNESS_HOME": self.tmp, "EHARNESS_BIN": os.path.join(ROOT, "bin", "eharness"),
                    "HOME": self.tmp}   # HOME 격리: 이 머신의 launchd/systemd 서비스 경로를 보지 않게
        self.port = free_port()

    def tearDown(self):
        subprocess.run(["bash", INIT, "stop", "--port", str(self.port)], env=self.env, capture_output=True)
        shutil.rmtree(self.tmp)

    def run_init(self, *args):
        return subprocess.run(["bash", INIT, *args, "--port", str(self.port)], env=self.env, capture_output=True, text=True, timeout=30)

    def test_status_without_server_fails(self):
        r = self.run_init("status")
        self.assertEqual(r.returncode, 1)
        self.assertIn("수집기 응답 없음", r.stdout)

    def test_start_reports_and_stop_cleans(self):
        r = self.run_init("start")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("기동: nohup", r.stdout)
        self.assertIn("세션: 살아있음", r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "collect.pid")))
        self.assertIn("이미 실행 중", self.run_init("start").stdout)     # 멱등
        r = self.run_init("stop")
        self.assertIn("중지", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "collect.pid")))
        time.sleep(0.5)
        self.assertEqual(self.run_init("status").returncode, 1)
