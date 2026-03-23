#!/usr/bin/env python3
"""Tests for app/main.py – HealthHandler and run_server."""
import http.client
import io
import json
import os
import sys
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from http.server import HTTPServer

from main import HealthHandler, run_server


class TestHealthHandlerEndpoints(unittest.TestCase):
    """Integration tests for HealthHandler using a real server running in a thread."""

    @classmethod
    def setUpClass(cls):
        # Port 0 lets the OS pick a free port.
        cls.server = HTTPServer(('', 0), HealthHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def _get(self, path):
        conn = http.client.HTTPConnection('localhost', self.port, timeout=5)
        conn.request('GET', path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp, body

    # -- /health endpoint -------------------------------------------------

    def test_health_returns_200(self):
        resp, _ = self._get('/health')
        self.assertEqual(resp.status, 200)

    def test_health_content_type_is_json(self):
        resp, _ = self._get('/health')
        self.assertEqual(resp.getheader('Content-type'), 'application/json')

    def test_health_body_is_valid_json(self):
        _, body = self._get('/health')
        data = json.loads(body)
        self.assertIsInstance(data, dict)

    def test_health_status_field_is_healthy(self):
        _, body = self._get('/health')
        self.assertEqual(json.loads(body)['status'], 'healthy')

    def test_health_service_field_is_jarvis_test(self):
        _, body = self._get('/health')
        self.assertEqual(json.loads(body)['service'], 'jarvis-test')

    def test_health_has_timestamp_field(self):
        _, body = self._get('/health')
        self.assertIn('timestamp', json.loads(body))

    def test_health_timestamp_ends_with_z(self):
        _, body = self._get('/health')
        self.assertTrue(json.loads(body)['timestamp'].endswith('Z'))

    # -- / (root) endpoint ------------------------------------------------

    def test_root_returns_200(self):
        resp, _ = self._get('/')
        self.assertEqual(resp.status, 200)

    def test_root_content_type_is_json(self):
        resp, _ = self._get('/')
        self.assertEqual(resp.getheader('Content-type'), 'application/json')

    def test_root_body_is_valid_json(self):
        _, body = self._get('/')
        self.assertIsInstance(json.loads(body), dict)

    def test_root_has_message_field(self):
        _, body = self._get('/')
        self.assertIn('message', json.loads(body))

    def test_root_message_mentions_jarvis(self):
        _, body = self._get('/')
        self.assertIn('Jarvis', json.loads(body)['message'])

    def test_root_has_endpoints_field(self):
        _, body = self._get('/')
        self.assertIn('endpoints', json.loads(body))

    def test_root_endpoints_includes_health(self):
        _, body = self._get('/')
        self.assertIn('/health', json.loads(body)['endpoints'])

    def test_root_endpoints_includes_root(self):
        _, body = self._get('/')
        self.assertIn('/', json.loads(body)['endpoints'])

    # -- Unknown / 404 paths ----------------------------------------------

    def test_unknown_path_returns_404(self):
        resp, _ = self._get('/unknown')
        self.assertEqual(resp.status, 404)

    def test_deep_unknown_path_returns_404(self):
        resp, _ = self._get('/api/v1/resource')
        self.assertEqual(resp.status, 404)

    def test_unknown_path_body_is_not_found(self):
        _, body = self._get('/unknown')
        self.assertEqual(body, b'Not Found')

    def test_health_subpath_returns_404(self):
        resp, _ = self._get('/health/extra')
        self.assertEqual(resp.status, 404)

    def test_empty_subpath_returns_404(self):
        resp, _ = self._get('/foo')
        self.assertEqual(resp.status, 404)


class TestHealthHandlerLogMessage(unittest.TestCase):
    """Unit tests for HealthHandler.log_message."""

    def setUp(self):
        self.handler = HealthHandler.__new__(HealthHandler)

    def test_log_message_produces_no_stderr_output(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.handler.log_message('%s %s %s', 'GET', '/health', '200')
        self.assertEqual(buf.getvalue(), '')

    def test_log_message_produces_no_stdout_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.handler.log_message('%s', 'some log entry')
        self.assertEqual(buf.getvalue(), '')

    def test_log_message_returns_none(self):
        result = self.handler.log_message('%s', 'test message')
        self.assertIsNone(result)

    def test_log_message_accepts_multiple_format_args(self):
        # Should not raise regardless of the number of arguments.
        self.handler.log_message('%s - - [%s] %s', '127.0.0.1', 'date', '"GET / HTTP/1.1" 200')


class TestRunServer(unittest.TestCase):
    """Unit tests for the run_server helper."""

    def _run(self, **kwargs):
        """Call run_server with HTTPServer mocked out so serve_forever returns immediately."""
        with patch('main.HTTPServer') as MockHTTPServer:
            mock_server = MagicMock()
            MockHTTPServer.return_value = mock_server
            run_server(**kwargs)
        return MockHTTPServer, mock_server

    def test_default_port_is_8000(self):
        MockHTTPServer, _ = self._run()
        MockHTTPServer.assert_called_once_with(('', 8000), HealthHandler)

    def test_custom_port_is_used(self):
        MockHTTPServer, _ = self._run(port=9999)
        MockHTTPServer.assert_called_once_with(('', 9999), HealthHandler)

    def test_serve_forever_is_called(self):
        _, mock_server = self._run()
        mock_server.serve_forever.assert_called_once()

    def test_prints_port_number(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self._run(port=8888)
        self.assertIn('8888', buf.getvalue())

    def test_uses_health_handler(self):
        MockHTTPServer, _ = self._run()
        _, handler_class = MockHTTPServer.call_args.args
        self.assertIs(handler_class, HealthHandler)


if __name__ == '__main__':
    unittest.main()
