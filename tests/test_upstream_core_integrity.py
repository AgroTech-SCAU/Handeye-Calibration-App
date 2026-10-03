import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UpstreamCoreIntegrityTests(unittest.TestCase):
    def test_release_core_matches_explicit_manifest(self):
        spec = importlib.util.spec_from_file_location('verify_core', ROOT/'scripts/verify_core.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest, mismatches = module.verify()
        self.assertEqual(manifest['base_commit'], '4bc7dc70af8a5e3ecee49502562bd1dfac0af4a1')
        self.assertIn('calibration_board.py',manifest['files'])
        self.assertIn('capture_sync.py',manifest['files'])
        self.assertEqual(mismatches, [])
