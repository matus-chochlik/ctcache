"""Check how the local cache publishes entries to concurrent readers."""

from __future__ import annotations

import builtins
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ctcache.clang_tidy_cache import ClangTidyCacheOpts, ClangTidyLocalCache

DIGEST = "0123456789abcdef0123456789abcdef01234567"


class LocalCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="ctcache local ")
        self.addCleanup(directory.cleanup)
        self.cache_dir = Path(directory.name)
        environment = mock.patch.dict(os.environ, {"CTCACHE_DIR": str(self.cache_dir)})
        environment.start()
        self.addCleanup(environment.stop)
        log = logging.getLogger(__name__)
        self.cache = ClangTidyLocalCache(log, ClangTidyCacheOpts(log, ["clang-tidy"]))
        self.entry = self.cache_dir / DIGEST[:2] / DIGEST[2:]

    def test_store_with_data_never_exposes_a_partial_entry(self) -> None:
        self.cache.store_in_cache_with_data(DIGEST, b"\x00old output")
        seen_by_reader = []
        real_open = builtins.open

        def open_and_read_entry_on_each_write(file, mode="r", *args, **kwargs):
            stream = real_open(file, mode, *args, **kwargs)
            if "w" in mode:
                real_write = stream.write

                def write(data):
                    written = real_write(data)
                    stream.flush()
                    seen_by_reader.append(self.cache.get_cache_data(DIGEST))
                    return written

                stream.write = write
            return stream

        with mock.patch("builtins.open", open_and_read_entry_on_each_write):
            self.cache.store_in_cache_with_data(DIGEST, b"\x00new output")

        self.assertTrue(seen_by_reader)
        self.assertEqual({b"\x00old output"}, set(seen_by_reader))
        self.assertEqual(b"\x00new output", self.cache.get_cache_data(DIGEST))

    def test_store_with_data_keeps_an_entry_a_reader_holds_open(self) -> None:
        self.cache.store_in_cache_with_data(DIGEST, b"\x00output")

        with mock.patch("ctcache.clang_tidy_cache.os.replace", side_effect=PermissionError):
            self.cache.store_in_cache_with_data(DIGEST, b"\x00output again")

        self.assertEqual(b"\x00output", self.cache.get_cache_data(DIGEST))
        self.assertEqual([self.entry], list(self.entry.parent.iterdir()))

    def test_store_with_data_raises_when_it_cannot_publish_a_new_entry(self) -> None:
        with mock.patch("ctcache.clang_tidy_cache.os.replace", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                self.cache.store_in_cache_with_data(DIGEST, b"\x00output")

        self.assertEqual([], list(self.entry.parent.iterdir()))

    def test_store_with_data_leaves_only_the_entry(self) -> None:
        self.cache.store_in_cache_with_data(DIGEST, b"\x00output")

        self.assertEqual([self.entry], list(self.entry.parent.iterdir()))


if __name__ == "__main__":
    unittest.main()
