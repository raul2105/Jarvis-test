#!/usr/bin/env python3
"""Tests for openclaw/skills/simple_monitor/scripts/monitor.py."""
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        'openclaw',
        'skills',
        'simple_monitor',
        'scripts',
    )
)
sys.path.insert(0, _SCRIPTS_DIR)

import monitor  # noqa: E402 -- must come after sys.path manipulation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int) -> MagicMock:
    """Return a mock urllib response that reports the given HTTP status code."""
    resp = MagicMock()
    resp.getcode.return_value = status_code
    return resp


# ---------------------------------------------------------------------------
# Missing / invalid arguments
# ---------------------------------------------------------------------------

class TestMonitorMissingArgs(unittest.TestCase):
    """monitor.main() should exit immediately when no URL is supplied."""

    def test_exits_with_code_1_when_no_url(self):
        with patch.object(sys, 'argv', ['monitor.py']):
            with self.assertRaises(SystemExit) as ctx:
                monitor.main()
        self.assertEqual(ctx.exception.code, 1)

    def test_prints_usage_message_when_no_url(self):
        with patch.object(sys, 'argv', ['monitor.py']):
            buf = StringIO()
            with redirect_stdout(buf):
                try:
                    monitor.main()
                except SystemExit:
                    pass
        self.assertIn('Usage', buf.getvalue())


# ---------------------------------------------------------------------------
# Normal operation (mocked network + file-system)
# ---------------------------------------------------------------------------

class TestMonitorMain(unittest.TestCase):
    """Comprehensive tests for monitor.main() with all I/O mocked out."""

    def setUp(self):
        self.mock_urlopen = patch('urllib.request.urlopen').start()
        self.mock_makedirs = patch('os.makedirs').start()
        self.mock_open_obj = mock_open()
        patch('builtins.open', self.mock_open_obj).start()

    def tearDown(self):
        patch.stopall()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, url='http://example.com/health', timeout=None) -> str:
        """Run monitor.main() with given args and return captured stdout."""
        argv = ['monitor.py', url]
        if timeout is not None:
            argv.append(str(timeout))
        buf = StringIO()
        with patch.object(sys, 'argv', argv):
            with redirect_stdout(buf):
                monitor.main()
        return buf.getvalue()

    def _written_content(self) -> str:
        """Return everything that was written to the mocked memory file."""
        return ''.join(
            c.args[0]
            for c in self.mock_open_obj.return_value.write.call_args_list
        )

    # ------------------------------------------------------------------
    # Healthy results (2xx status codes)
    # ------------------------------------------------------------------

    def test_200_produces_healthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'healthy')

    def test_201_produces_healthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(201)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'healthy')

    def test_299_produces_healthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(299)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'healthy')

    # ------------------------------------------------------------------
    # Unhealthy results (non-2xx status codes)
    # ------------------------------------------------------------------

    def test_300_produces_unhealthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(300)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'unhealthy')

    def test_404_produces_unhealthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(404)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'unhealthy')

    def test_500_produces_unhealthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(500)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'unhealthy')

    def test_199_produces_unhealthy_result(self):
        self.mock_urlopen.return_value = _make_mock_response(199)
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'unhealthy')

    # ------------------------------------------------------------------
    # Result payload fields
    # ------------------------------------------------------------------

    def test_url_field_matches_argument(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        url = 'http://myservice.internal/health'
        output = self._run(url=url)
        self.assertEqual(json.loads(output)['url'], url)

    def test_status_code_field_matches_response(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        self.assertEqual(json.loads(output)['status_code'], 200)

    def test_error_field_is_none_on_success(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        self.assertIsNone(json.loads(output)['error'])

    def test_timestamp_field_present(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        self.assertIn('timestamp', json.loads(output))

    def test_timestamp_ends_with_z(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        self.assertTrue(json.loads(output)['timestamp'].endswith('Z'))

    def test_output_is_valid_json(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        result = json.loads(output)
        self.assertIsInstance(result, dict)

    def test_result_has_all_required_fields(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        output = self._run()
        result = json.loads(output)
        for field in ('url', 'timestamp', 'status_code', 'result', 'error'):
            self.assertIn(field, result, msg=f'Missing field: {field}')

    # ------------------------------------------------------------------
    # Exception / error handling
    # ------------------------------------------------------------------

    def test_exception_produces_error_result(self):
        self.mock_urlopen.side_effect = Exception('Connection refused')
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'error')

    def test_exception_message_is_recorded(self):
        self.mock_urlopen.side_effect = Exception('Connection refused')
        output = self._run()
        self.assertEqual(json.loads(output)['error'], 'Connection refused')

    def test_status_code_is_none_on_exception(self):
        self.mock_urlopen.side_effect = Exception('Timeout')
        output = self._run()
        self.assertIsNone(json.loads(output)['status_code'])

    def test_url_is_present_in_error_result(self):
        self.mock_urlopen.side_effect = Exception('DNS error')
        url = 'http://bad.example.com/health'
        output = self._run(url=url)
        self.assertEqual(json.loads(output)['url'], url)

    def test_url_error_produces_error_result(self):
        import urllib.error
        self.mock_urlopen.side_effect = urllib.error.URLError('unreachable')
        output = self._run()
        self.assertEqual(json.loads(output)['result'], 'error')

    # ------------------------------------------------------------------
    # Timeout argument
    # ------------------------------------------------------------------

    def test_default_timeout_is_10(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run()
        _, kwargs = self.mock_urlopen.call_args
        self.assertEqual(kwargs['timeout'], 10)

    def test_custom_timeout_30_is_used(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run(timeout=30)
        _, kwargs = self.mock_urlopen.call_args
        self.assertEqual(kwargs['timeout'], 30)

    def test_custom_timeout_5_is_used(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run(timeout=5)
        _, kwargs = self.mock_urlopen.call_args
        self.assertEqual(kwargs['timeout'], 5)

    # ------------------------------------------------------------------
    # Memory file writing
    # ------------------------------------------------------------------

    def test_makedirs_called_with_exist_ok_true(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run()
        self.mock_makedirs.assert_called_once()
        _, kwargs = self.mock_makedirs.call_args
        self.assertTrue(kwargs.get('exist_ok', False))

    def test_memory_file_opened_for_append(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run()
        open_args = self.mock_open_obj.call_args
        self.assertEqual(open_args.args[1], 'a')

    def test_memory_file_content_contains_url(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        url = 'http://example.com/health'
        self._run(url=url)
        self.assertIn(url, self._written_content())

    def test_memory_file_content_contains_healthy(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run()
        self.assertIn('healthy', self._written_content())

    def test_memory_file_content_contains_result_on_unhealthy(self):
        self.mock_urlopen.return_value = _make_mock_response(500)
        self._run()
        self.assertIn('unhealthy', self._written_content())

    def test_memory_file_content_contains_error_result_on_exception(self):
        self.mock_urlopen.side_effect = Exception('Connection refused')
        self._run()
        self.assertIn('error', self._written_content())

    def test_memory_file_content_contains_error_details_on_exception(self):
        self.mock_urlopen.side_effect = Exception('Connection refused')
        self._run()
        self.assertIn('Connection refused', self._written_content())

    def test_memory_file_no_error_parenthetical_on_success(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run()
        # The "(Error: ...)" clause must be absent when there is no error.
        self.assertNotIn('Error:', self._written_content())

    def test_memory_file_written_at_least_once(self):
        self.mock_urlopen.return_value = _make_mock_response(200)
        self._run()
        self.assertTrue(self.mock_open_obj.return_value.write.called)


if __name__ == '__main__':
    unittest.main()
