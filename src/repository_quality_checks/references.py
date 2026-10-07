#!/usr/bin/env python3
"""Check that documentation cross-references resolve.

Only *local* references are checked: relative Markdown links, and inline references of the
form ``foo.md``. Project-specific decision/checklist numbering is not assumed. External URLs are deliberately not fetched —
a CI job that fails because a third-party site is down is a job people learn to ignore.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path.cwd()

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
DOC_MENTION = re.compile(r"`([a-z0-9-]+\.md)`")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root

    from .hygiene import iter_files

    if not root.is_dir():
        parser.exit(2, "root must be an existing directory\n")
    root = root.resolve()
    docs = sorted(path for path in iter_files(root) if path.suffix.lower() == ".md")
    known_docs = {p.name for p in docs}
    problems: list[str] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        rel = doc.relative_to(root)

        for target in MARKDOWN_LINK.findall(text):
            if target.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            resolved = (doc.parent / target.split("#")[0]).resolve()
            if not resolved.is_relative_to(root):
                problems.append(f"{rel}: link leaves selected root: {target}")
            elif not resolved.exists():
                problems.append(f"{rel}: link target does not exist: {target}")

        for name in DOC_MENTION.findall(text):
            if name not in known_docs:
                problems.append(f"{rel}: references unknown document `{name}`")

    print(f"documentation references: {len(docs)} documents, {len(problems)} problem(s)")
    for problem in problems[:60]:
        print(f"  {problem}", file=sys.stderr)
    if len(problems) > 60:
        print(f"  ... and {len(problems) - 60} more", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
