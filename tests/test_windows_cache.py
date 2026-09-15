"""Check real cache reuse with Windows command strings and spaced paths."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    os.name == "nt" and shutil.which("clang-tidy") and shutil.which("clang++"),
    "Native Windows LLVM tools are required",
)
class WindowsCacheTest(unittest.TestCase):
    def test_command_string_reuses_findings(self) -> None:
        self.check_cache_reuse(is_spaced_compiler_path=False)

    def test_spaced_compiler_path_reuses_findings(self) -> None:
        self.check_cache_reuse(is_spaced_compiler_path=True)

    def check_cache_reuse(self, is_spaced_compiler_path: bool) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcache Windows paths ") as directory:
            root = Path(directory)
            source = root / "source file.cpp"
            source.write_text("int* pointer = 0;\n", encoding="utf-8")
            (root / ".clang-tidy").write_text(
                "Checks: '-*,modernize-use-nullptr'\nWarningsAsErrors: '*'\n",
                encoding="utf-8",
            )
            compiler = (
                root
                / ("compiler tools" if is_spaced_compiler_path else "compiler")
                / "clang++.exe"
            )
            if not is_spaced_compiler_path:
                # The installed path has no spaces on the qualification host.
                compiler = Path(str(shutil.which("clang++")))
            else:
                compiler.parent.mkdir()
                # Use a separate executable path without copying its large contents.
                os.link(str(shutil.which("clang++")), compiler)
            arguments = [str(compiler), '-DNAME="two words"', "-c", str(source)]
            database = root / "compile_commands.json"
            database.write_text(
                json.dumps(
                    [
                        {
                            "directory": str(root),
                            "file": str(source),
                            "command": subprocess.list2cmdline(arguments),
                        }
                    ]
                ),
                encoding="utf-8",
            )
            environment = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("CTCACHE_")
            }
            environment.update(
                CTCACHE_DIR=str(root / "cache"),
                CTCACHE_SAVE_OUTPUT="1",
                CTCACHE_KEEP_COMMENTS="1",
            )
            direct = [str(shutil.which("clang-tidy")), "-p", str(root), str(source)]
            cached = [
                sys.executable,
                str(ROOT / "src/ctcache/clang_tidy_cache.py"),
                *direct,
            ]

            def run(command: list[str]) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    command,
                    cwd=root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )

            expected = run(direct)
            cold = run(cached)
            warm = run(cached)
            self.assertEqual(1, expected.returncode, expected.stdout + expected.stderr)
            self.assertEqual(
                (1, expected.stdout), (cold.returncode, cold.stdout), cold.stderr
            )
            self.assertNotIn("ERROR:", cold.stderr)
            self.assertTrue(cold.stderr)
            self.assertEqual(
                (1, expected.stdout), (warm.returncode, warm.stdout), warm.stderr
            )
            self.assertEqual("", warm.stderr)
            self.assertTrue(list((root / "cache").rglob("*")))
            source.write_text("int* pointer = nullptr;\n", encoding="utf-8")
            self.assertEqual(0, run(cached).returncode)
