"""Check where cache statistics are kept."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ctcache.clang_tidy_cache import ClangTidyCacheOpts, ClangTidyCacheStats

DIGEST = "0123456789abcdef0123456789abcdef01234567"


class StatsTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="ctcache stats ")
        self.addCleanup(directory.cleanup)
        self.cache_dir = Path(directory.name) / "cache"
        self.stats_dir = Path(directory.name) / "stats"
        self.cache_dir.mkdir()

    def stats(self, environment: dict) -> ClangTidyCacheStats:
        patch = mock.patch.dict(os.environ, environment)
        patch.start()
        self.addCleanup(patch.stop)
        log = logging.getLogger(__name__)
        return ClangTidyCacheStats(log, ClangTidyCacheOpts(log, ["clang-tidy"]), "stats")

    def test_stats_dir_keeps_counters_out_of_the_cache_dir(self) -> None:
        stats = self.stats({"CTCACHE_DIR": str(self.cache_dir), "CTCACHE_STATS_DIR": str(self.stats_dir)})

        stats.update(DIGEST, True)
        stats.update(DIGEST, False)

        self.assertEqual((1, 1), stats.read())
        self.assertEqual([], list(self.cache_dir.iterdir()))

    def test_counters_default_to_the_cache_dir(self) -> None:
        stats = self.stats({"CTCACHE_DIR": str(self.cache_dir)})

        stats.update(DIGEST, True)

        self.assertTrue((self.cache_dir / DIGEST[:2] / "stats").is_file())


if __name__ == "__main__":
    unittest.main()
