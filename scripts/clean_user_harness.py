#!/usr/bin/env python3
"""Exercise an installed ProjectForge package as an isolated new user."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("no-provider", "logged-out", "ready")
STUB_GENERATION_EXIT = 86
SYSTEM_PATH = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")
SENSITIVE_ENV_MARKERS = ("API_KEY", "CREDENTIAL", "PASSWORD", "SECRET", "TOKEN")


class HarnessError(RuntimeError):
    """Raised when the clean-user environment cannot be prepared or verified."""


@dataclass(frozen=True)
class HarnessPaths:
    """Filesystem boundaries for one harness installation."""

    root: Path

    @property
    def tool_dir(self) -> Path:
        return self.root / "uv-tools"

    @property
    def tool_bin(self) -> Path:
        return self.root / "bin"

    @property
    def cache_dir(self) -> Path:
        return self.root / "uv-cache"

    @property
    def dist_dir(self) -> Path:
        return self.root / "dist"

    def command(self, name: str = "projectforge") -> Path:
        return self.tool_bin / name


def build_child_env(
    root: Path,
    *,
    state_root: Path | None = None,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an environment isolated from real Forge and provider installations."""
    paths = HarnessPaths(root)
    state = state_root or root
    env = {
        key: value
        for key, value in (base_env or os.environ).items()
        if not any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS)
    }
    for startup_variable in ("BASH_ENV", "ENV", "ZDOTDIR"):
        env.pop(startup_variable, None)
    env.update(
        {
            "FORGE_HOME": str(state / "forge-home"),
            "GIT_CONFIG_GLOBAL": str(state / "gitconfig"),
            "NO_COLOR": "1",
            "TERM": "dumb",
            "UV_TOOL_DIR": str(paths.tool_dir),
            "UV_TOOL_BIN_DIR": str(paths.tool_bin),
            "UV_CACHE_DIR": str(paths.cache_dir),
            "PATH": os.pathsep.join(
                [str(paths.tool_bin), str(state / "provider-bin"), *SYSTEM_PATH]
            ),
        }
    )
    return env


def write_provider_shim(root: Path, scenario: str) -> Path | None:
    """Create a deterministic Codex readiness shim for a harness scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown clean-user scenario: {scenario}")
    if scenario == "no-provider":
        return None

    shim_dir = root / "provider-bin"
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / "codex"
    if scenario == "ready":
        status_body = 'echo "Logged in using ChatGPT"\n  exit 0'
    else:
        status_body = 'echo "Not logged in" >&2\n  exit 1'

    shim.write_text(
        "#!/bin/sh\n"
        "if [ \"${1:-}\" = \"--version\" ]; then\n"
        '  echo "codex-cli clean-user-harness"\n'
        "  exit 0\n"
        "fi\n"
        "if [ \"${1:-}\" = \"login\" ] && [ \"${2:-}\" = \"status\" ]; then\n"
        f"  {status_body}\n"
        "fi\n"
        'echo "clean-user harness provider stub: generation is disabled" >&2\n'
        f"exit {STUB_GENERATION_EXIT}\n"
    )
    shim.chmod(0o755)
    return shim


def seed_config(root: Path) -> Path:
    """Create the smallest valid config representing completed first-run setup."""
    config_path = root / "forge-home" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"config_version": 1}, indent=2) + "\n")
    config_path.chmod(0o600)
    return config_path


def _display_command(command: Sequence[str | Path]) -> str:
    return " ".join(str(part) for part in command)


def _run(
    command: Sequence[str | Path],
    *,
    cwd: Path,
    env: Mapping[str, str],
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=dict(env),
        capture_output=capture,
        text=True,
    )


def _require_process(
    result: subprocess.CompletedProcess[str],
    *,
    expected_exit: int,
    command: Sequence[str | Path],
) -> None:
    if result.returncode == expected_exit:
        return
    detail = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    raise HarnessError(
        f"Expected exit {expected_exit}, got {result.returncode}: {_display_command(command)}"
        + (f"\n{detail}" if detail else "")
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def _uv_install_env(paths: HarnessPaths) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "UV_TOOL_DIR": str(paths.tool_dir),
            "UV_TOOL_BIN_DIR": str(paths.tool_bin),
            "UV_CACHE_DIR": str(paths.cache_dir),
        }
    )
    return env


def _find_uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        raise HarnessError("uv is required. Install uv, then rerun the clean-user harness.")
    return uv


def _build_wheel(paths: HarnessPaths, uv: str) -> Path:
    paths.dist_dir.mkdir(parents=True, exist_ok=True)
    command = [
        uv,
        "build",
        "--wheel",
        "--out-dir",
        paths.dist_dir,
        "--no-create-gitignore",
        ROOT,
    ]
    print(f"[build] {_display_command(command)}", flush=True)
    result = _run(command, cwd=ROOT, env=_uv_install_env(paths))
    _require_process(result, expected_exit=0, command=command)
    wheels = sorted(paths.dist_dir.glob("*.whl"))
    _require(len(wheels) == 1, f"Expected one wheel in {paths.dist_dir}, found {len(wheels)}")
    return wheels[0]


def install_projectforge(
    root: Path,
    *,
    python_version: str,
    wheel: Path | None = None,
    editable: bool = False,
) -> HarnessPaths:
    """Install the wheel or editable source into an isolated uv tool directory."""
    if editable and wheel is not None:
        raise HarnessError("Choose either an editable install or a wheel, not both.")

    paths = HarnessPaths(root.resolve())
    paths.root.mkdir(parents=True, exist_ok=True)
    uv = _find_uv()
    package = ROOT if editable else (wheel.resolve() if wheel else _build_wheel(paths, uv))
    if not package.exists():
        raise HarnessError(f"Install source does not exist: {package}")

    command: list[str | Path] = [
        uv,
        "tool",
        "install",
        "--python",
        python_version,
        "--no-config",
        "--force",
    ]
    if editable:
        command.append("--editable")
    command.append(package)
    print(f"[install] {_display_command(command)}", flush=True)
    result = _run(command, cwd=ROOT, env=_uv_install_env(paths))
    _require_process(result, expected_exit=0, command=command)
    for name in ("projectforge", "forge"):
        _require(
            paths.command(name).is_file(),
            f"Installed command is missing: {paths.command(name)}",
        )
    return paths


def _run_installed(
    paths: HarnessPaths,
    state_root: Path,
    args: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    work_dir = state_root / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    command = [paths.command(), *args]
    return _run(command, cwd=work_dir, env=build_child_env(paths.root, state_root=state_root))


def _doctor_payload(
    paths: HarnessPaths,
    state_root: Path,
    *,
    expected_exit: int,
) -> dict:
    command = [paths.command(), "doctor", "--json"]
    result = _run_installed(paths, state_root, ["doctor", "--json"])
    _require_process(result, expected_exit=expected_exit, command=command)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HarnessError(f"Doctor did not emit valid JSON:\n{result.stdout}") from exc


def verify_clean_install(
    root: Path,
    *,
    python_version: str,
    wheel: Path | None = None,
) -> None:
    """Run the deterministic installed-package clean-user scenario suite."""
    paths = install_projectforge(root, python_version=python_version, wheel=wheel)

    pristine = paths.root / "scenarios" / "no-provider"
    version_command = [paths.command(), "--version"]
    version = _run_installed(paths, pristine, ["--version"])
    _require_process(version, expected_exit=0, command=version_command)
    _require("projectforge " in version.stdout.lower(), "Version output lacks ProjectForge name")

    alias_command = [paths.command("forge"), "--version"]
    alias = _run(
        alias_command,
        cwd=pristine / "work",
        env=build_child_env(paths.root, state_root=pristine),
    )
    _require_process(alias, expected_exit=0, command=alias_command)

    help_command = [paths.command(), "--help"]
    help_result = _run_installed(paths, pristine, ["--help"])
    _require_process(help_result, expected_exit=0, command=help_command)
    _require("Usage:" in help_result.stdout, "Installed help output lacks a Usage section")

    pristine_doctor = _doctor_payload(paths, pristine, expected_exit=1)
    _require(pristine_doctor["config"]["status"] == "missing", "Fresh config was not missing")
    _require(
        all(
            provider["readiness"] == "not_installed"
            for provider in pristine_doctor["providers"].values()
        ),
        "Fresh no-provider scenario discovered a provider outside the harness",
    )

    setup_command = [paths.command(), "--setup"]
    setup = _run_installed(paths, pristine, ["--setup"])
    _require_process(setup, expected_exit=1, command=setup_command)
    _require(
        "could not find a supported ai tool" in setup.stdout.lower(),
        "First-run no-provider setup did not show the expected recovery guidance",
    )

    dry_run_args = [
        "--dry-run",
        "--name",
        "clean-install-smoke",
        "--stack",
        "python-cli",
        "--description",
        "Clean install smoke test",
        "--no-docker",
        "--no-open",
        "--no-verify",
    ]
    dry_run_command = [paths.command(), *dry_run_args]
    dry_run = _run_installed(paths, pristine, dry_run_args)
    _require_process(dry_run, expected_exit=0, command=dry_run_command)
    _require("Clean install smoke test" in dry_run.stdout, "Dry run omitted the project brief")
    _require("no model calls made" in dry_run.stdout.lower(), "Dry run omitted its safety receipt")
    _require(
        not (pristine / "work" / "clean-install-smoke").exists(),
        "Dry run unexpectedly created a project directory",
    )
    _require(
        not (pristine / "forge-home" / "config.json").exists(),
        "Prompt-only use unexpectedly created user configuration",
    )
    print("[pass] pristine install, help, no-provider setup, doctor, and dry-run")

    logged_out = paths.root / "scenarios" / "logged-out"
    write_provider_shim(logged_out, "logged-out")
    logged_out_doctor = _doctor_payload(paths, logged_out, expected_exit=1)
    codex = logged_out_doctor["providers"]["codex"]
    _require(codex["installed"] is True, "Logged-out Codex shim was not discovered")
    _require(codex["readiness"] == "needs_login", "Logged-out Codex was misclassified")
    print("[pass] installed provider requiring login")

    ready = paths.root / "scenarios" / "ready"
    write_provider_shim(ready, "ready")
    unconfigured_doctor = _doctor_payload(paths, ready, expected_exit=1)
    _require(
        unconfigured_doctor["providers"]["codex"]["readiness"] == "ready",
        "Ready Codex shim was not classified as ready",
    )
    _require(
        unconfigured_doctor["config"]["status"] == "missing",
        "Ready but unconfigured scenario did not preserve fresh-user state",
    )
    seed_config(ready)
    configured_doctor = _doctor_payload(paths, ready, expected_exit=0)
    _require(configured_doctor["status"] == "ready", "Configured ready scenario was not ready")
    _require(configured_doctor["config"]["status"] == "valid", "Seed config was not valid")
    print("[pass] ready provider before and after first-run configuration")
    print(f"Clean-user verification passed: {paths.root}")


@contextmanager
def harness_root(path: Path | None, *, keep: bool) -> Iterator[Path]:
    """Yield a caller-owned, preserved, or automatically cleaned harness root."""
    if path is not None:
        resolved = path.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        yield resolved
        return
    if keep:
        resolved = Path(tempfile.mkdtemp(prefix="projectforge-clean-user-"))
        print(f"Harness files will be preserved at {resolved}")
        yield resolved
        return
    with tempfile.TemporaryDirectory(prefix="projectforge-clean-user-") as temp_dir:
        yield Path(temp_dir)


def _prepare_scenario(root: Path, scenario: str, *, configured: bool) -> Path:
    state_root = root / "scenarios" / scenario
    write_provider_shim(state_root, scenario)
    if configured:
        seed_config(state_root)
    return state_root


def _normalize_user_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        command = command[1:]
    return command or ["projectforge", "doctor", "--json"]


def run_user_command(
    paths: HarnessPaths,
    state_root: Path,
    command: list[str],
) -> int:
    """Run a user-selected command with inherited terminal IO inside the harness."""
    work_dir = state_root / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_user_command(command)
    print(f"Harness: {paths.root}", flush=True)
    print(f"Scenario: {state_root.name}", flush=True)
    print(f"Forge data: {state_root / 'forge-home'}", flush=True)
    print(f"Workspace: {work_dir}", flush=True)
    print(f"$ {_display_command(normalized)}", flush=True)
    result = _run(
        normalized,
        cwd=work_dir,
        env=build_child_env(paths.root, state_root=state_root),
        capture=False,
    )
    return result.returncode


def open_harness_shell(paths: HarnessPaths, state_root: Path) -> int:
    """Open an interactive shell for exploratory clean-user testing."""
    shell = "/bin/sh"
    print(
        "Try: projectforge --version; projectforge doctor; projectforge; exit",
        flush=True,
    )
    return run_user_command(paths, state_root, [shell])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install and exercise ProjectForge without touching real user state.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--root", type=Path, help="Persistent harness directory.")
        target.add_argument("--keep", action="store_true", help="Preserve an automatic temp root.")
        current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        target.add_argument(
            "--python",
            default=current_python,
            help=f"Python version for uv tool install (default: {current_python}).",
        )

    verify = subparsers.add_parser("verify", help="Run the automated clean-install scenarios.")
    add_common(verify)
    verify.add_argument("--wheel", type=Path, help="Install an existing wheel instead of building.")

    def add_interactive(target: argparse.ArgumentParser) -> None:
        add_common(target)
        target.add_argument("--scenario", choices=SCENARIOS, default="no-provider")
        target.add_argument(
            "--configured",
            action="store_true",
            help="Seed valid first-run config.",
        )
        install = target.add_mutually_exclusive_group()
        install.add_argument(
            "--editable",
            action="store_true",
            help="Install source editable for rapid fix-and-rerun work.",
        )
        install.add_argument("--wheel", type=Path, help="Install an existing wheel.")

    run = subparsers.add_parser("run", help="Run one command inside the harness.")
    add_interactive(run)
    run.add_argument("command", nargs=argparse.REMAINDER)

    shell = subparsers.add_parser("shell", help="Open an interactive isolated shell.")
    add_interactive(shell)
    shell.set_defaults(editable=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with harness_root(args.root, keep=args.keep) as root:
            if args.action == "verify":
                verify_clean_install(root, python_version=args.python, wheel=args.wheel)
                return 0

            paths = install_projectforge(
                root,
                python_version=args.python,
                wheel=args.wheel,
                editable=args.editable and args.wheel is None,
            )
            state_root = _prepare_scenario(
                paths.root,
                args.scenario,
                configured=args.configured,
            )
            if args.action == "run":
                return run_user_command(paths, state_root, args.command)
            return open_harness_shell(paths, state_root)
    except (HarnessError, OSError) as exc:
        print(f"Clean-user harness failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
