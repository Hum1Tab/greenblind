import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from greenblind.core import audit, classify, git, materialize, plan, run_command, safe_path, snapshot
from greenblind.demo import commit, OLD, NEW, TEST
from greenblind.report import html, write


class ProbeTests(unittest.TestCase):
    def test_independent_regions_preserve_crlf_and_missing_final_newline(self):
        base = {'a.py': (b'a=1\r\nx=0\r\nb=2', 0o644)}
        head = {'a.py': (b'a=3\r\nx=0\r\nb=4', 0o644)}
        probes, _ = plan(base, head, ['*.py'], [])
        self.assertEqual([p.replacement for p in probes], [b'a=1\r\nx=0\r\nb=4', b'a=3\r\nx=0\r\nb=2'])

    def test_added_and_deleted_files(self):
        base = {'gone': (b'old', 0o755)}
        head = {'added': (b'new', 0o644)}
        probes, _ = plan(base, head, ['*'], [])
        self.assertIsNone(probes[0].replacement)
        self.assertEqual(probes[1].replacement, b'old')

    def test_delete_and_insert_lines(self):
        base = {'f': (b'a\nb\nc\n', 0o644)}
        head = {'f': (b'a\nc\nd\n', 0o644)}
        probes, _ = plan(base, head, ['*'], [])
        self.assertEqual(probes[0].replacement, b'a\nb\nc\nd\n')
        self.assertEqual(probes[1].replacement, b'a\nc\n')

    def test_filters_and_binary_are_explicit(self):
        head = {'src/a': (b'\0x', 0o644), 'src/test': (b'x', 0o644), 'doc': (b'x', 0o644)}
        probes, skipped = plan({}, head, ['src/*'], ['src/test'])
        self.assertFalse(probes)
        self.assertEqual(len(skipped), 2)

    def test_mode_only_is_skipped(self):
        probes, skipped = plan({'a': (b'x', 0o644)}, {'a': (b'x', 0o755)}, ['*'], [])
        self.assertFalse(probes)
        self.assertEqual(skipped[0]['reason'], 'file mode changed')

    def test_unsafe_paths(self):
        for name in ('../escape', '/escape', 'C:/escape', '.git/config', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(name)

    def test_outcomes_do_not_conflate_timeout_and_nonzero(self):
        ok = {'status': 'completed', 'exit_code': 0}
        fail = {'status': 'completed', 'exit_code': 1}
        timeout = {'status': 'timeout', 'exit_code': -9}
        self.assertEqual(classify([ok, fail]), 'unstable')
        self.assertEqual(classify([fail, fail]), 'rejected')
        self.assertEqual(classify([timeout, fail]), 'inconclusive')


class ExecutionTests(unittest.TestCase):
    def test_missing_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_command(['greenblind-command-does-not-exist'], tmp, 1)['status'], 'error')

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_command([sys.executable, '-c', 'import time; time.sleep(10)'], tmp, .1)
            self.assertEqual(result['status'], 'timeout')
            self.assertLess(result['seconds'], 5)

    def test_output_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_command([sys.executable, '-c', 'print("x" * 50000)'], tmp, 5)
            self.assertLessEqual(len(result['log']), 16000)

    def test_command_arguments_are_not_shell_interpreted(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_command([sys.executable, '-c', 'import sys; print(sys.argv[1])', '$(echo secret); & test'], tmp, 5)
            self.assertIn('$(echo secret); & test', result['log'])


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo with spaces'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo / 'shop.py').write_text(OLD, encoding='utf-8')
        commit(self.repo, 'before')
        (self.repo / 'shop.py').write_text(NEW, encoding='utf-8')
        (self.repo / 'test_shop.py').write_text(TEST, encoding='utf-8')
        commit(self.repo, 'after')

    def check(self, **kwargs):
        command = kwargs.pop('command', [sys.executable, '-m', 'unittest', 'discover'])
        return audit(self.repo, 'HEAD~1', 'HEAD', ['shop.py'], [], command, **kwargs)

    def test_end_to_end_keeps_dirty_workspace_and_index(self):
        (self.repo / 'shop.py').write_text('my uncommitted work', encoding='utf-8')
        (self.repo / 'untracked').write_text('mine', encoding='utf-8')
        before = git(self.repo, 'status', '--porcelain=v1')
        report = self.check()
        self.assertEqual(report['status'], 'complete')
        self.assertEqual([r['outcome'] for r in report['results']], ['rejected', 'unnoticed'])
        self.assertEqual(git(self.repo, 'status', '--porcelain=v1'), before)
        self.assertEqual((self.repo / 'shop.py').read_text(), 'my uncommitted work')

    def test_baseline_failure_stops_probes(self):
        report = self.check(command=[sys.executable, '-c', 'raise SystemExit(1)'])
        self.assertEqual(report['status'], 'baseline_failed')
        self.assertFalse(report['results'])

    def test_budget_is_reported(self):
        report = self.check(limit=1)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['omitted_probes'], 1)

    def test_each_run_has_a_fresh_snapshot(self):
        report = self.check(command=[sys.executable, '-c',
            'from pathlib import Path; p=Path("marker"); assert not p.exists(); p.write_text("x")'])
        self.assertEqual(report['status'], 'complete')
        self.assertTrue(all(r['outcome'] == 'unnoticed' for r in report['results']))

    def test_empty_plan_is_not_success(self):
        report = audit(self.repo, 'HEAD', 'HEAD', ['shop.py'], [], [sys.executable, '-c', 'pass'])
        self.assertEqual(report['status'], 'no_probes')

    def test_git_export_ignore_does_not_hide_files(self):
        (self.repo / '.gitattributes').write_text('shop.py export-ignore\n', encoding='utf-8')
        commit(self.repo, 'attributes')
        files = snapshot(self.repo, 'HEAD')
        self.assertIn('shop.py', files)

    def test_reports_escape_source_and_omit_logs(self):
        report = self.check()
        report['results'][0]['after'] = '<script>alert(1)</script>'
        report['results'][0]['runs'][0]['log'] = 'PRIVATE_OUTPUT_MARKER'
        output = Path(self.tmp.name) / 'reports'
        write(report, output)
        for name in ('report.json', 'report.md', 'report.html'):
            self.assertNotIn('PRIVATE_OUTPUT_MARKER', (output / name).read_text(encoding='utf-8'))
        page = (output / 'report.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertEqual(json.loads((output / 'report.json').read_text())['schema_version'], 1)

    @unittest.skipUnless(shutil.which('node'), 'Node optional')
    def test_javascript_command(self):
        (self.repo / 'value.cjs').write_text('module.exports = 1;\n')
        commit(self.repo, 'JS before')
        (self.repo / 'value.cjs').write_text('module.exports = 2;\n')
        commit(self.repo, 'JS after')
        report = audit(self.repo, 'HEAD~1', 'HEAD', ['value.cjs'], [],
                       [shutil.which('node'), '-e', 'require("node:assert").equal(require("./value.cjs"), 2)'])
        self.assertEqual(report['results'][0]['outcome'], 'rejected')


if __name__ == '__main__':
    unittest.main()
