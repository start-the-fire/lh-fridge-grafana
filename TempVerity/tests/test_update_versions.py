"""Offline CLI regression tests; no package registries or installs are used."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class UpdateVersionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(Path(__file__).resolve().parents[1] / "update_versions.sh", self.root)
        (self.root / "frontend").mkdir()
        for name in ("package.json", "package-lock.json"):
            (self.root / "frontend" / name).write_text('{}\n')
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        npm = bin_dir / "npm"
        npm.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$CALL_LOG"\n'
                       'printf "%s\\n" "$NPM_REPORT"\nexit "$NPM_STATUS"\n')
        npm.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{bin_dir}:{os.environ["PATH"]}',
                        CALL_LOG=str(self.root / "calls"), NPM_REPORT='{}', NPM_STATUS='0')

    def run_script(self, *args):
        return subprocess.run(['sh', str(self.root / 'update_versions.sh'), *args],
                              env=self.env, capture_output=True, text=True, timeout=10)

    def test_check_is_read_only_and_uses_lockfile(self):
        result = self.run_script('--frontend-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('up to date', result.stdout)
        self.assertIn('--package-lock-only', (self.root / 'calls').read_text())
        for file in (self.root / 'frontend').iterdir():
            self.assertEqual(file.read_text(), '{}\n')

    def test_outdated_exit_one_is_success(self):
        self.env.update(NPM_STATUS='1', NPM_REPORT='{"react":{"current":"18.3.0","wanted":"18.3.1","latest":"19.0.0","type":"dependencies"}}')
        result = self.run_script('--frontend-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('react', result.stdout)

    def test_registry_errors_are_not_swallowed(self):
        self.env.update(NPM_STATUS='1', NPM_REPORT='{"error":{"code":"E401"}}')
        result = self.run_script('--frontend-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('failed', result.stderr)

    def test_update_saves_manifest_and_lockfile(self):
        result = self.run_script('--frontend-only', '--update')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'calls').read_text().strip(),
                         'update --save --package-lock=true --include=dev --ignore-scripts')

    def test_update_failure_propagates(self):
        self.env['NPM_STATUS'] = '2'
        self.assertNotEqual(self.run_script('--frontend-only', '--update').returncode, 0)

    def test_conflicting_modes(self):
        self.assertEqual(self.run_script('--frontend-only', '--python-only').returncode, 2)

    def test_missing_lockfile(self):
        (self.root / 'frontend' / 'package-lock.json').unlink()
        self.assertNotEqual(self.run_script('--frontend-only').returncode, 0)


if __name__ == '__main__':
    unittest.main()
