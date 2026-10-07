# Repository Quality Checks

Small repository checks for file hygiene and local Markdown references. Extracted from tooling developed while working on personal engineering projects. The runtime uses only the Python standard library.

## Install and use

Requires Python 3.11+. From this folder:

```text
python -m pip install .
repo-hygiene --root .
repo-doc-links --root .
```

The default root is the current working directory. The first command checks UTF-8 text, LF line endings, final newlines, trailing whitespace, Python tab characters, file size and a small set of obvious credential patterns. Dependency/cache/build directories are pruned; linked descendant directories and files are skipped. See [the Python example](examples/check_repository.py) for library use.

The second command checks local Markdown target existence and containment, plus simple inline document-name mentions. It does not fetch remote URLs or check heading anchors, and it does not assume project-specific decision or checklist numbering.

## Optional repairs

```text
repo-hygiene --root . --fix
```

This explicitly edits trailing whitespace and missing final newlines. It reports the findings observed before repair, so run the read-only command again to confirm the resulting state. Other issue types require a separate decision. Keep a version-controlled or backed-up copy when repairing files.

Exit codes are 0 for no findings, 1 for findings, and 2 for invalid invocation or a reported input error. Constants and extension/skip sets are exposed in the hygiene module for callers that need a custom policy. Defaults include a 512 KiB file-size limit; this is an ordinary repository policy, not an engineering accuracy threshold.

## Limits and development

Read [limitations](docs/limitations.md). The secret patterns are heuristics, not a security certification or a replacement for a dedicated scanner. Findings show labels and locations rather than credential values. The Markdown matcher is intentionally simple and can flag examples inside code blocks; it does not fully parse Markdown syntax.

```text
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check .
python -m build
```

Tests cover repair idempotence, encodings, directory pruning, link escape rejection, Windows junctions and safe findings with synthetic values. See [provenance](docs/provenance.md), [contribution guidance](CONTRIBUTING.md) and [LICENSE](LICENSE).
