"""Regression tests for the production HTTP server (requires server extras)."""
import importlib.util
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SERVER_DEPS = all(importlib.util.find_spec(name) for name in ("flask", "gevent", "matplotlib"))


@unittest.skipUnless(SERVER_DEPS, "Install ctcache server extras")
class ServerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.log_path = self.root / "server.log"
        self.log = self.log_path.open("w+")
        self.addCleanup(self.log.close)
        self.process = None
        self.addCleanup(self.stop)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.base = "http://127.0.0.1:%d" % self.port
        self.key = "regression-test-write-key"
        self.digest = "a" * 40

    def start(self, authenticated=True):
        command = [sys.executable, str(ROOT / "src/ctcache/clang_tidy_cache_server.py"),
                   "--port", str(self.port), "--save-path", str(self.root / "index.json.gz"),
                   "--save-interval", "3600", "--max-cache-size", "1"]
        if authenticated:
            command.extend(["--auth-key-writes", self.key])
        environment = dict(os.environ, CTCACHE_WEBROOT=str(self.root),
                           MPLCONFIGDIR=str(self.root / "matplotlib"), MPLBACKEND="Agg")
        self.process = subprocess.Popen(command, env=environment, stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail("Server exited: " + self.log_path.read_text())
            try:
                if self.request("/stats")[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.05)
        self.fail("Server did not become ready")

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                raise

    def request(self, path, data=None):
        request = urllib.request.Request(self.base + path, data=data,
                                         method="GET" if data is None else "PUT")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def put(self, key=None):
        query = "?" + urllib.parse.urlencode({"key": key}) if key is not None else ""
        return self.request("/cache/" + self.digest + query,
                            urllib.parse.urlencode({"data": "cached diagnostics"}).encode())

    def test_authenticated_writes_and_public_reads(self):
        self.start()
        self.assertEqual(self.put()[0], 403)
        self.assertEqual(self.put("incorrect")[0], 403)
        self.assertEqual(self.put(self.key)[0], 200)
        self.assertEqual(self.request("/cache/" + self.digest), (200, b"cached diagnostics"))

    def test_authenticated_server_rejects_get_purge(self):
        self.start()
        self.assertEqual(self.put(self.key)[0], 200)
        self.assertEqual(self.request("/purge_cache")[0], 403)
        self.assertEqual(self.request("/cache/" + self.digest), (200, b"cached diagnostics"))

    def test_unauthenticated_server_still_allows_purge(self):
        self.start(authenticated=False)
        self.assertEqual(self.put()[0], 200)
        self.assertEqual(self.request("/purge_cache")[0], 200)
        self.assertEqual(self.request("/is_cached/" + self.digest), (200, b"false"))

    def test_access_log_does_not_disclose_write_key(self):
        self.start()
        self.assertEqual(self.put(self.key)[0], 200)
        self.stop()
        self.assertNotIn(self.key, self.log_path.read_text())

    @unittest.skipUnless(os.name == "posix", "POSIX shutdown signals")
    def test_sigterm_saves_index_before_periodic_save(self):
        self.start()
        self.assertEqual(self.put(self.key)[0], 200)
        self.process.send_signal(signal.SIGTERM)
        self.process.wait(timeout=15)
        self.assertEqual(self.process.returncode, 0)
        self.start()
        self.assertEqual(self.request("/cache/" + self.digest), (200, b"cached diagnostics"))


if __name__ == "__main__":
    unittest.main()
