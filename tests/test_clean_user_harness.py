"""Tests for the isolated clean-user development harness."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from scripts import clean_user_harness


def test_build_child_env_isolates_forge_and_provider_discovery(tmp_path: Path) -> None:
    base_env = {
        "HOME": "test-home",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "KEEP_ME": "yes",
        "OPENAI_API_KEY": "must-not-leak",
        "ZDOTDIR": "/tmp/host-shell-config",
    }

    env = clean_user_harness.build_child_env(tmp_path, base_env=base_env)

    assert env["FORGE_HOME"] == str(tmp_path / "forge-home")
    assert env["UV_TOOL_DIR"] == str(tmp_path / "uv-tools")
    assert env["UV_TOOL_BIN_DIR"] == str(tmp_path / "bin")
    assert env["UV_CACHE_DIR"] == str(tmp_path / "uv-cache")
    assert env["GIT_CONFIG_GLOBAL"] == str(tmp_path / "gitconfig")
    assert env["HOME"] == "test-home"
    assert env["KEEP_ME"] == "yes"
    assert "OPENAI_API_KEY" not in env
    assert "ZDOTDIR" not in env
    assert env["PATH"].split(os.pathsep) == [
        str(tmp_path / "bin"),
        str(tmp_path / "provider-bin"),
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]


def test_ready_provider_shim_reports_installed_and_authenticated(tmp_path: Path) -> None:
    shim = clean_user_harness.write_provider_shim(tmp_path, "ready")

    version = subprocess.run([shim, "--version"], capture_output=True, text=True)
    status = subprocess.run([shim, "login", "status"], capture_output=True, text=True)
    generation = subprocess.run([shim, "exec", "prompt"], capture_output=True, text=True)

    assert version.returncode == 0
    assert "clean-user-harness" in version.stdout
    assert status.returncode == 0
    assert "Logged in using ChatGPT" in status.stdout
    assert generation.returncode == clean_user_harness.STUB_GENERATION_EXIT
    assert "generation is disabled" in generation.stderr


def test_logged_out_provider_shim_reports_login_required(tmp_path: Path) -> None:
    shim = clean_user_harness.write_provider_shim(tmp_path, "logged-out")

    status = subprocess.run([shim, "login", "status"], capture_output=True, text=True)

    assert status.returncode == 1
    assert "Not logged in" in status.stderr


def test_no_provider_scenario_creates_no_shim(tmp_path: Path) -> None:
    assert clean_user_harness.write_provider_shim(tmp_path, "no-provider") is None
    assert list(tmp_path.iterdir()) == []


def test_seed_config_creates_minimal_valid_first_run_state(tmp_path: Path) -> None:
    config_path = clean_user_harness.seed_config(tmp_path)

    assert config_path == tmp_path / "forge-home" / "config.json"
    assert json.loads(config_path.read_text()) == {"config_version": 1}
