"""Check that CTCACHE_HASH_INCLUDED_FILES sees comments in every included file."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ctcache.clang_tidy_cache import ClangTidyCacheOpts, hash_inputs


@unittest.skipUnless(shutil.which("gcc") and shutil.which("clang-tidy"), "needs gcc and clang-tidy")
class HashIncludedFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="ctcache included ")
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.source = self.directory / "main.cpp"
        self.source.write_text('#include "outer.h"\nint main() { return inner; }\n')
        (self.directory / "outer.h").write_text('#include "inner.h"\n')
        self.inner = self.directory / "inner.h"
        self.inner.write_text("int inner;\n")
        environment = mock.patch.dict(os.environ, {"CTCACHE_HASH_INCLUDED_FILES": "1"})
        environment.start()
        self.addCleanup(environment.stop)

    def digest(self) -> str:
        log = logging.getLogger(__name__)
        source = str(self.source)
        return hash_inputs(log, ClangTidyCacheOpts(log, ["clang-tidy", source, "--", "gcc", "-c", source]))

    def test_same_inputs_give_same_digest(self) -> None:
        self.assertEqual(self.digest(), self.digest())

    def test_comment_edit_in_transitive_header_changes_digest(self) -> None:
        before = self.digest()
        self.inner.write_text("int inner;  // NOLINT\n")
        self.assertNotEqual(before, self.digest())

    def test_comment_edit_in_source_changes_digest(self) -> None:
        before = self.digest()
        self.source.write_text(self.source.read_text() + "// NOLINT\n")
        self.assertNotEqual(before, self.digest())


if __name__ == "__main__":
    unittest.main()
