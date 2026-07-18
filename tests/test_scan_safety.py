"""Tests for the public working-tree safety scanner."""

import subprocess
from pathlib import Path

from scripts import scan_safety


def test_public_files_include_untracked_non_ignored_files(monkeypatch):
    """New public files are scanned before they are staged."""

    def fake_run(command, **kwargs):
        assert command == ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
        return subprocess.CompletedProcess(command, 0, stdout="README.md\ndocs/new.md\n")

    monkeypatch.setattr(scan_safety.subprocess, "run", fake_run)

    assert scan_safety.get_public_files() == ["README.md", "docs/new.md"]


def test_scanner_rejects_generic_personal_paths_and_email_addresses(tmp_path):
    unsafe = tmp_path / "unsafe.md"
    unsafe.write_text(
        "Local source: /Users/example-person/private-project\n"
        "Contact: developer@example-company.test\n"
    )

    violations = scan_safety.scan_file("unsafe.md", Path(unsafe))

    names = {name for _, name, _ in violations}
    assert names == {"email address", "local user path"}
