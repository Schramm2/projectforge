"""Post-scaffold verification — install deps, run checks, probe health endpoint."""

import json
import os
import re
import subprocess
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from rich.console import Console

from projectforge.safety import redact_secrets
from projectforge.stacks import STACK_META
from projectforge.ui import badge, make_table, muted


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    passed: bool
    detail: str = ""
    skipped: bool = False
    command: str = ""
    cwd: str = ""
    timeout_seconds: int | None = None
    request_timeout_seconds: int | None = None
    exit_code: int | None = None
    remediation: str = ""
    attempted_endpoints: tuple[str, ...] = ()
    duration_seconds: float = 0.0


@dataclass
class VerifyReport:
    """Collection of check results from a verification run."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed or c.skipped for c in self.checks)


# Checks to attempt per stack, in order.  Keys must match dev_commands keys
# or the special names "install" and "health".
_CHECK_ORDER = ["install", "lint", "typecheck", "build", "test", "health"]

# Install commands keyed by package_manager value in StackMeta
_INSTALL_COMMANDS: dict[str, str] = {
    "uv": "uv sync",
    "npm": "npm install",
}

# Stacks whose dev_commands include a run/backend_run command on a port
_HEALTH_PORT_RE = re.compile(r"--port\s+(\d+)")
_DEFAULT_HEALTH_PORT = 8000
_DEFAULT_HEALTH_ENDPOINTS = ("/health", "/ready")
_DEFAULT_HEALTH_STARTUP_TIMEOUT = 12
_DEFAULT_HEALTH_REQUEST_TIMEOUT = 3


def _verification_env() -> dict[str, str]:
    """Return an environment isolated from Forge's own active virtual environment."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    return env


def _privacy_safe_text(value: str, project_dir: Path) -> str:
    """Redact credentials and make local filesystem paths non-identifying."""
    if not value:
        return ""
    safe = redact_secrets(value)
    replacements = (
        (str(project_dir.resolve()), "."),
        (str(Path.home().resolve()), "~"),
    )
    for local_path, replacement in replacements:
        safe = safe.replace(local_path, replacement)
    return safe


def _load_pyproject(project_dir: Path) -> dict | None:
    path = project_dir / "pyproject.toml"
    if not path.exists():
        return None
    try:
        return tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _python_dev_dependencies(pyproject: dict) -> set[str]:
    project = pyproject.get("project", {})
    groups = pyproject.get("dependency-groups", {})
    tool_uv = pyproject.get("tool", {}).get("uv", {})
    raw_dependencies = [
        *project.get("dependencies", []),
        *project.get("optional-dependencies", {}).get("dev", []),
        *groups.get("dev", []),
        *tool_uv.get("dev-dependencies", []),
    ]
    names: set[str] = set()
    for value in raw_dependencies:
        if not isinstance(value, str):
            continue
        match = re.match(r"[a-zA-Z0-9_.-]+", value)
        if match:
            names.add(match.group(0).lower())
    return names


def _python_install_command(project_dir: Path) -> str:
    pyproject = _load_pyproject(project_dir)
    if pyproject is None:
        return "uv sync"
    optional = pyproject.get("project", {}).get("optional-dependencies", {})
    if isinstance(optional, dict) and "dev" in optional:
        return "uv sync --extra dev"
    groups = pyproject.get("dependency-groups", {})
    tool_uv = pyproject.get("tool", {}).get("uv", {})
    if (isinstance(groups, dict) and "dev" in groups) or tool_uv.get("dev-dependencies"):
        return "uv sync --dev"
    return "uv sync"


def _effective_dev_commands(stack: str, project_dir: Path) -> dict[str, str]:
    """Derive Python checks from generated metadata, falling back to stack recipes."""
    meta = STACK_META[stack]
    commands = dict(meta.dev_commands)
    if "uv" not in meta.package_manager:
        return commands
    pyproject = _load_pyproject(project_dir)
    if pyproject is None:
        return commands

    dependencies = _python_dev_dependencies(pyproject)
    tool = pyproject.get("tool", {})
    if "ruff" in dependencies or "ruff" in tool:
        commands["lint"] = "uv run ruff check ."
    else:
        commands.pop("lint", None)
    if "mypy" in dependencies or "mypy" in tool:
        commands["typecheck"] = "uv run mypy ."
    else:
        commands.pop("typecheck", None)
    if "pytest" in dependencies or "pytest" in tool or (project_dir / "tests").exists():
        commands["test"] = "uv run pytest -q"
    else:
        commands.pop("test", None)
    return commands


def _health_settings(project_dir: Path) -> tuple[tuple[str, ...], int, int]:
    """Read bounded localhost-only health settings from generated metadata."""
    defaults = (
        _DEFAULT_HEALTH_ENDPOINTS,
        _DEFAULT_HEALTH_STARTUP_TIMEOUT,
        _DEFAULT_HEALTH_REQUEST_TIMEOUT,
    )
    pyproject = _load_pyproject(project_dir)
    if pyproject is None:
        return defaults
    config = pyproject.get("tool", {}).get("forge", {}).get("verification", {})
    if not isinstance(config, dict):
        return defaults
    endpoints = config.get("health_endpoints", list(_DEFAULT_HEALTH_ENDPOINTS))
    startup_timeout = config.get("health_startup_timeout", _DEFAULT_HEALTH_STARTUP_TIMEOUT)
    request_timeout = config.get("health_request_timeout", _DEFAULT_HEALTH_REQUEST_TIMEOUT)
    if (
        not isinstance(endpoints, list)
        or not 1 <= len(endpoints) <= 8
        or not all(
            isinstance(endpoint, str)
            and re.fullmatch(r"/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*", endpoint) is not None
            for endpoint in endpoints
        )
        or isinstance(startup_timeout, bool)
        or not isinstance(startup_timeout, int)
        or not 1 <= startup_timeout <= 120
        or isinstance(request_timeout, bool)
        or not isinstance(request_timeout, int)
        or not 1 <= request_timeout <= 30
    ):
        return defaults
    return tuple(endpoints), startup_timeout, request_timeout


def _run_check(
    name: str,
    cmd: str,
    cwd: Path,
    timeout: int = 60,
) -> CheckResult:
    """Run a shell command and return pass/fail."""
    started = time.monotonic()
    metadata = {
        "command": cmd,
        "cwd": str(cwd),
        "timeout_seconds": timeout,
    }
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_verification_env(),
        )
        if result.returncode == 0:
            return CheckResult(
                name=name,
                passed=True,
                exit_code=0,
                duration_seconds=time.monotonic() - started,
                **metadata,
            )
        stderr = result.stderr.strip()
        detail = (
            _privacy_safe_text(stderr, cwd)[:200]
            if stderr
            else f"exit code {result.returncode}"
        )
        return CheckResult(
            name=name,
            passed=False,
            detail=detail,
            exit_code=result.returncode,
            remediation=f"Run `{cmd}` in `{cwd}` and inspect the complete output.",
            duration_seconds=time.monotonic() - started,
            **metadata,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            passed=False,
            detail=f"timed out after {timeout}s",
            remediation=f"Run `{cmd}` manually or increase the verification timeout.",
            duration_seconds=time.monotonic() - started,
            **metadata,
        )


def _install_deps(stack: str, project_dir: Path) -> CheckResult:
    """Install project dependencies based on the stack's package manager."""
    meta = STACK_META.get(stack)
    if not meta:
        return CheckResult(name="install", passed=False, detail=f"unknown stack: {stack}")

    pkg_mgr = meta.package_manager

    # Fullstack "both" needs uv + npm
    if pkg_mgr == "uv + npm":
        uv_result = _run_check("install (python)", "uv sync", project_dir, timeout=60)
        if not uv_result.passed:
            return CheckResult(name="install", passed=False, detail=uv_result.detail)
        frontend_dir = project_dir / "frontend"
        if frontend_dir.exists():
            npm_result = _run_check("install (node)", "npm install", frontend_dir, timeout=60)
            if not npm_result.passed:
                return CheckResult(name="install", passed=False, detail=npm_result.detail)
        return CheckResult(name="install", passed=True)

    install_cmd = (
        _python_install_command(project_dir) if pkg_mgr == "uv" else _INSTALL_COMMANDS.get(pkg_mgr)
    )
    if not install_cmd:
        return CheckResult(name="install", passed=False, detail=f"no install cmd for {pkg_mgr}")
    return _run_check("install", install_cmd, project_dir, timeout=60)


def _extract_port(run_cmd: str) -> int:
    """Extract port number from a uvicorn/dev command string."""
    match = _HEALTH_PORT_RE.search(run_cmd)
    return int(match.group(1)) if match else _DEFAULT_HEALTH_PORT


def _check_health(
    project_dir: Path,
    run_cmd: str,
    *,
    endpoints: tuple[str, ...] = _DEFAULT_HEALTH_ENDPOINTS,
    startup_timeout: int = _DEFAULT_HEALTH_STARTUP_TIMEOUT,
    request_timeout: int = _DEFAULT_HEALTH_REQUEST_TIMEOUT,
) -> CheckResult:
    """Start the server, poll configured endpoints, then stop it."""
    port = _extract_port(run_cmd)
    process = None
    started = time.monotonic()
    attempted_endpoints: list[str] = []
    metadata = {
        "command": run_cmd,
        "cwd": str(project_dir),
        "timeout_seconds": startup_timeout,
        "request_timeout_seconds": request_timeout,
    }
    try:
        process = subprocess.Popen(
            run_cmd,
            shell=True,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_verification_env(),
        )
        attempts = max(1, startup_timeout // 2)
        for _attempt in range(attempts):
            time.sleep(1.5)
            # Check if process died
            if process.poll() is not None:
                stderr = (process.stderr.read() or b"").decode(errors="replace")
                detail = (
                    _privacy_safe_text(stderr.strip(), project_dir)[:200]
                    if stderr.strip()
                    else "server exited early"
                )
                return CheckResult(
                    name="health",
                    passed=False,
                    detail=detail,
                    exit_code=process.returncode,
                    remediation="Inspect the server command and startup output.",
                    attempted_endpoints=tuple(attempted_endpoints),
                    duration_seconds=time.monotonic() - started,
                    **metadata,
                )
            for path in endpoints:
                url = f"http://localhost:{port}{path}"
                attempted_endpoints.append(url)
                try:
                    resp = urlopen(url, timeout=request_timeout)
                    if resp.status == 200:
                        return CheckResult(
                            name="health",
                            passed=True,
                            attempted_endpoints=tuple(attempted_endpoints),
                            duration_seconds=time.monotonic() - started,
                            **metadata,
                        )
                except (URLError, OSError, TimeoutError):
                    continue
        return CheckResult(
            name="health",
            passed=False,
            detail=f"no successful response on port {port} after {startup_timeout}s",
            remediation="Confirm the server command, port, and configured health endpoints.",
            attempted_endpoints=tuple(attempted_endpoints),
            duration_seconds=time.monotonic() - started,
            **metadata,
        )
    except Exception as exc:
        return CheckResult(
            name="health",
            passed=False,
            detail=_privacy_safe_text(str(exc), project_dir)[:200],
            remediation="Run the server command manually and inspect startup output.",
            attempted_endpoints=tuple(attempted_endpoints),
            duration_seconds=time.monotonic() - started,
            **metadata,
        )
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def verify_scaffold(
    stack: str,
    project_dir: Path,
    verbose: bool = False,
) -> VerifyReport:
    """Run post-scaffold verification checks for the given stack."""
    meta = STACK_META.get(stack)
    if not meta:
        return VerifyReport(
            checks=[CheckResult(name="verify", passed=False, detail=f"unknown stack: {stack}")]
        )

    report = VerifyReport()
    dev = _effective_dev_commands(stack, project_dir)

    # 1. Install dependencies
    install_result = _install_deps(stack, project_dir)
    report.checks.append(install_result)
    if not install_result.passed:
        # Skip everything else — deps are required
        for check_name in _CHECK_ORDER[1:]:
            if check_name == "health":
                run_cmd = dev.get("run") or dev.get("backend_run")
                if not run_cmd:
                    continue
            elif check_name not in dev:
                continue
            report.checks.append(
                CheckResult(
                    name=check_name,
                    passed=False,
                    skipped=True,
                    detail="deps not installed",
                )
            )
        return report

    # 2. Run dev_commands checks (lint, typecheck, build, test)
    for check_name in ("lint", "typecheck", "build", "test"):
        cmd = dev.get(check_name)
        if not cmd:
            continue
        result = _run_check(check_name, cmd, project_dir)
        report.checks.append(result)

    # 3. Health check for backend stacks
    run_cmd = dev.get("run") or dev.get("backend_run")
    if run_cmd:
        endpoints, startup_timeout, request_timeout = _health_settings(project_dir)
        health_result = _check_health(
            project_dir,
            run_cmd,
            endpoints=endpoints,
            startup_timeout=startup_timeout,
            request_timeout=request_timeout,
        )
        report.checks.append(health_result)

    return report


def _portable_cwd(cwd: str, project_dir: Path) -> str:
    if not cwd:
        return ""
    try:
        relative = Path(cwd).resolve().relative_to(project_dir.resolve())
    except (OSError, ValueError):
        return "<external>"
    return "." if str(relative) == "." else f"./{relative.as_posix()}"


def write_verification_report(report: VerifyReport, project_dir: Path) -> Path:
    """Persist a privacy-safe, reproducible verification evidence report."""

    def _safe(value: str) -> str:
        return _privacy_safe_text(value, project_dir)

    payload = {
        "schema_version": 1,
        "all_passed": report.all_passed,
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "skipped": check.skipped,
                "detail": _safe(check.detail),
                "command": _safe(check.command),
                "cwd": _portable_cwd(check.cwd, project_dir),
                "timeout_seconds": check.timeout_seconds,
                "request_timeout_seconds": check.request_timeout_seconds,
                "exit_code": check.exit_code,
                "remediation": _safe(check.remediation),
                "attempted_endpoints": [_safe(endpoint) for endpoint in check.attempted_endpoints],
                "duration_seconds": round(check.duration_seconds, 3),
            }
            for check in report.checks
        ],
    }
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)
    output_path = forge_dir / "verification.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return output_path


def print_report(report: VerifyReport, console: Console) -> None:
    """Render the verification report as a Rich table."""
    table = make_table(title="Scaffold Verification", accent="plum")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail", style="#8893B3")

    for check in report.checks:
        if check.skipped:
            status = muted("skipped")
        elif check.passed:
            status = badge("pass", "success")
        else:
            status = badge("fail", "error")
        table.add_row(check.name, status, check.detail or "")

    console.print()
    console.print(table)
