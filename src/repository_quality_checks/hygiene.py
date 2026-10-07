"""Repository hygiene checks that need no third-party tooling.

Covers the file-integrity part of the toolchain (trailing whitespace, final newline,
encoding, line endings, large files, stray build artefacts, obvious secrets). ruff owns code
style; this owns everything ruff does not look at, including non-Python files.

Run as ``repo-hygiene --root PATH``. The default root is the current directory.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass

ROOT = pathlib.Path.cwd()

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".cfg",
    ".ini",
    ".txt",
    ".dat",
    ".gitignore",
    ".editorconfig",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    "htmlcov",
    "node_modules",
    ".eggs",
    "external",
}
#: Files that legitimately exceed the size limit, with the reason.
LARGE_FILE_ALLOWANCE: dict[str, str] = {}
MAX_BYTES = 512 * 1024

# Caller-controlled exceptions; no project-specific fixtures are exempt by default.
WHITESPACE_EXEMPT_PREFIXES: dict[str, str] = {}

SECRET_PATTERNS = (
    (re.compile(r"(?i)aws_secret_access_key\s*[:=]"), "AWS secret key assignment"),
    (re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{16,}"), "inline API key"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\bpassword\s*[:=]\s*['\"][^'\"]{6,}"), "inline password"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
)


@dataclass
class Problem:
    path: str
    line: int | None
    kind: str
    detail: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"  [{self.kind}] {where}: {self.detail}"


def linked(path: pathlib.Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def iter_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Walk with dependency pruning; do not follow symlinks or Windows junctions."""
    for parent, dirs, files in os.walk(root):
        dirs[:] = sorted(
            d for d in dirs if d not in SKIP_DIRS and not linked(pathlib.Path(parent) / d)
        )
        base = pathlib.Path(parent)
        for name in sorted(files):
            if not linked(base / name):
                yield base / name


def check(root: pathlib.Path, fix: bool = False) -> list[Problem]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("root must be an existing directory")
    problems: list[Problem] = []
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        if size > MAX_BYTES and rel not in LARGE_FILE_ALLOWANCE:
            problems.append(
                Problem(
                    rel,
                    None,
                    "large-file",
                    f"{size / 1024:.0f} KiB exceeds {MAX_BYTES // 1024} KiB",
                )
            )
        if path.suffix not in TEXT_SUFFIXES and path.name not in TEXT_SUFFIXES:
            continue

        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            problems.append(Problem(rel, None, "encoding", f"not valid UTF-8: {exc}"))
            continue

        if b"\r\n" in raw:
            problems.append(Problem(rel, None, "line-endings", "contains CRLF; the policy is LF"))

        if (
            raw
            and not raw.endswith(b"\n")
            and not any(rel.startswith(prefix) for prefix in WHITESPACE_EXEMPT_PREFIXES)
        ):
            problems.append(Problem(rel, None, "final-newline", "missing trailing newline"))
            if fix:
                path.write_bytes(raw + b"\n")

        if path.suffix in {".py", ".toml", ".yaml", ".yml", ".json", ".md"}:
            for number, line in enumerate(text.splitlines(), start=1):
                for pattern, label in SECRET_PATTERNS:
                    if pattern.search(line):
                        problems.append(Problem(rel, number, "possible-secret", label))

        exempt = any(rel.startswith(prefix) for prefix in WHITESPACE_EXEMPT_PREFIXES)
        if exempt:
            continue

        changed = False
        lines = text.split("\n")
        for number, line in enumerate(lines, start=1):
            if line.rstrip("\r") != line.rstrip():
                problems.append(Problem(rel, number, "trailing-whitespace", "trailing whitespace"))
                changed = True
            if "\t" in line and path.suffix == ".py":
                problems.append(Problem(rel, number, "tab-indent", "tab in a Python source line"))
        if fix and changed:
            # Preserve the trailing newline: joining stripped lines would drop it and the
            # next run would report a final-newline problem the previous run created.
            repaired = "\n".join(entry.rstrip() for entry in lines)
            if text and not repaired.endswith("\n"):
                repaired += "\n"
            path.write_text(repaired, encoding="utf-8", newline="\n")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--fix", action="store_true", help="repair whitespace issues in place")
    args = parser.parse_args(argv)

    try:
        problems = check(args.root, fix=args.fix)
    except (OSError, ValueError) as error:
        parser.exit(2, str(error) + "\n")
    counts: dict[str, int] = {}
    for problem in problems:
        counts[problem.kind] = counts.get(problem.kind, 0) + 1

    n_files = sum(1 for _ in iter_files(args.root))
    print(f"hygiene: {n_files} files checked, {len(problems)} problem(s)")
    for problem in problems[:60]:
        print(str(problem), file=sys.stderr)
    if len(problems) > 60:
        print(f"  ... and {len(problems) - 60} more", file=sys.stderr)
    if counts:
        print("  " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())), file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
