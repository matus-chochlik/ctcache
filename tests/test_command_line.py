"""Check native compilation command parsing without running a compiler."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ctcache.clang_tidy_cache import ClangTidyCacheOpts, split_command


class CommandLineTest(unittest.TestCase):
    def compiler_arguments(self, entry: dict) -> list:
        with tempfile.TemporaryDirectory(prefix="ctcache paths ") as directory:
            source = Path(directory) / "source file.cpp"
            source.touch()
            options = ClangTidyCacheOpts(logging.getLogger(__name__), ["clang-tidy"])
            options._compile_commands_db = [dict(entry, file=str(source))]
            return options._compiler_args_for(str(source))

    @unittest.skipUnless(os.name == "nt", "Native Windows command parsing")
    def test_windows_command_preserves_arguments(self) -> None:
        arguments = [
            r"C:\Program Files\LLVM\bin\clang++.exe",
            "-IC:\\include path\\",
            '-DNAME="quoted value"',
            "-DEMPTY=",
            "",
            "-DQUOTE=it's",
            r"-DPATH=C:\plain\path",
            "-c",
            r"C:\source tree\main.cpp",
        ]
        self.assertEqual(
            arguments,
            self.compiler_arguments({"command": subprocess.list2cmdline(arguments)}),
        )

    @unittest.skipUnless(os.name == "nt", "Native Windows command parsing")
    def test_windows_unquoted_path_keeps_backslashes(self) -> None:
        self.assertEqual(
            [r"C:\LLVM\bin\clang++.exe", "-c", r"C:\source\main.cpp"],
            self.compiler_arguments(
                {"command": r"C:\LLVM\bin\clang++.exe -c C:\source\main.cpp"}
            ),
        )

    def test_arguments_array_does_not_change(self) -> None:
        arguments = [r"C:\Program Files\LLVM\bin\clang++.exe", "", '-DNAME="x"']
        self.assertEqual(arguments, self.compiler_arguments({"arguments": arguments}))

    def test_posix_quotes_and_escapes(self) -> None:
        with mock.patch("ctcache.clang_tidy_cache.os.name", "posix"):
            self.assertEqual(
                ["/opt/compiler tools/clang++", "-DNAME=two words", "source file.cpp"],
                split_command(
                    "'/opt/compiler tools/clang++' '-DNAME=two words' source\\ file.cpp"
                ),
            )

    def test_client_can_run_as_one_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = Path(directory) / "clang-tidy-cache.py"
            shutil.copy2(
                Path(__file__).resolve().parents[1] / "src/ctcache/clang_tidy_cache.py",
                client,
            )
            process = subprocess.run(
                [sys.executable, str(client)],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, process.returncode, process.stderr)

    def test_empty_command(self) -> None:
        self.assertEqual([], split_command(" \t"))

    @unittest.skipUnless(os.name == "nt", "Native Windows command parsing")
    def test_windows_leading_whitespace(self) -> None:
        self.assertEqual(
            ["clang++", "-c", "a.cpp"], split_command(" \tclang++ -c a.cpp")
        )


if __name__ == "__main__":
    unittest.main()
