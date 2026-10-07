import os
import subprocess

import pytest

from repository_quality_checks import check
from repository_quality_checks.hygiene import iter_files


def test_detects_encoding_newlines_whitespace_and_sizes(tmp_path, monkeypatch):
    (tmp_path / "note.md").write_bytes(b"hello \r\n")
    (tmp_path / "broken.txt").write_bytes(b"\xff")
    (tmp_path / "code.py").write_bytes(b"\tpass")
    monkeypatch.setattr("repository_quality_checks.hygiene.MAX_BYTES", 5)
    kinds = {problem.kind for problem in check(tmp_path)}
    assert {
        "line-endings",
        "trailing-whitespace",
        "encoding",
        "final-newline",
        "tab-indent",
        "large-file",
    } <= kinds


def test_fix_preserves_final_newline_and_is_idempotent(tmp_path):
    path = tmp_path / "note.md"
    path.write_bytes(b"line   \nsecond ")
    assert check(tmp_path, fix=True)
    assert path.read_bytes() == b"line\nsecond\n"
    assert check(tmp_path, fix=True) == []


def test_dependency_trees_are_pruned(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/README.md").write_bytes(b"bad ")
    (tmp_path / "README.md").write_bytes(b"good\n")
    assert [path.relative_to(tmp_path).as_posix() for path in iter_files(tmp_path)] == ["README.md"]
    assert check(tmp_path) == []


def test_possible_secret_does_not_echo_value(tmp_path):
    value = "gh" + "p_" + "X" * 36
    (tmp_path / "example.txt").write_text("example\n", encoding="utf-8")
    (tmp_path / "config.py").write_text("credential = " + repr(value) + "\n", encoding="utf-8")
    problems = check(tmp_path)
    findings = [problem for problem in problems if problem.kind == "possible-secret"]
    assert findings
    assert value not in str(findings[0])


def test_whitespace_exception_does_not_skip_secret_check(tmp_path, monkeypatch):
    value = "gh" + "p_" + "X" * 36
    (tmp_path / "fixture").mkdir()
    (tmp_path / "fixture/data.py").write_text(
        "credential = " + repr(value) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        "repository_quality_checks.hygiene.WHITESPACE_EXEMPT_PREFIXES",
        {"fixture/": "intentional fixture"},
    )
    assert any(problem.kind == "possible-secret" for problem in check(tmp_path))


def test_linked_directory_is_not_followed(tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    (target / "bad.md").write_bytes(b"bad ")
    root = tmp_path / "root"
    root.mkdir()
    link = root / "escape"
    if os.name == "nt":
        env = {**os.environ, "CHECK_LINK": str(link), "CHECK_TARGET": str(target)}
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "New-Item -ItemType Junction -Path $env:CHECK_LINK -Target $env:CHECK_TARGET | Out-Null",
            ],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 0
    else:
        link.symlink_to(target, target_is_directory=True)
    assert list(iter_files(root)) == []
    assert check(root) == []


def test_invalid_root_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        check(tmp_path / "missing")
