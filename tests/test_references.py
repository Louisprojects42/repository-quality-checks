from repository_quality_checks.references import main


def test_valid_local_links_and_external_links(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "[Guide](docs/guide.md) [Web](https://example.com) [Anchor](#here)\n", encoding="utf-8"
    )
    (tmp_path / "docs/guide.md").write_text("[Home](../README.md)\n", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 0


def test_missing_or_escaping_links_are_findings(tmp_path, capsys):
    (tmp_path / "README.md").write_text(
        "[Missing](missing.md) [Escape](../outside.md)\n", encoding="utf-8"
    )
    assert main(["--root", str(tmp_path)]) == 1
    error = capsys.readouterr().err
    assert "does not exist" in error
    assert "leaves selected root" in error


def test_inline_document_mentions_and_dependency_pruning(tmp_path):
    (tmp_path / "README.md").write_text("See `guide.md`.\n", encoding="utf-8")
    (tmp_path / "guide.md").write_text("Guide\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/README.md").write_text("[Missing](missing.md)\n", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 0
    (tmp_path / "guide.md").unlink()
    assert main(["--root", str(tmp_path)]) == 1
