import os, unittest
from cctv.sources import registry


class TestRegistry(unittest.TestCase):
    def test_slug_posix_and_windows(self):
        self.assertEqual(registry.slug("/Users/ethan/tools/eharness"), "-Users-ethan-tools-eharness")
        self.assertEqual(registry.slug(r"C:\Users\ethan\tools\eharness"), "C--Users-ethan-tools-eharness")
        self.assertTrue(registry.transcript_path(r"C:\Users\e\p", "sid").endswith(os.path.join("C--Users-e-p", "sid.jsonl")))

    def test_alive_self_and_bogus(self):
        self.assertTrue(registry.alive(os.getpid()))
        self.assertFalse(registry.alive(None))
        self.assertFalse(registry.alive(2**22 + 12345))
