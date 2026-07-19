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
_CHECK_ORDER = ["install", "lint", "typecheck", "build", "test", "smoke", "health"]

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


def _python_entrypoint_smoke_command(pyproject: dict) -> str | None:
    """Build a bounded help command for generated Python console entry points."""
    scripts = pyproject.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return None
    names = sorted(
        name
        for name in scripts
        if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
    )
    if not names:
        return None
    return " && ".join(f"uv run {name} --help" for name in names)


def _gitignore_ignores_uv_lock(project_dir: Path) -> bool:
    """Detect the direct lockfile ignore patterns Forge tells generated projects to avoid."""
    gitignore = project_dir / ".gitignore"
    if not gitignore.is_file():
        return False
    ignored = False
    for raw_line in gitignore.read_text().splitlines():
        pattern = raw_line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        normalized = pattern.removeprefix("!").removeprefix("/")
        if normalized in {"uv.lock", "*.lock"}:
            ignored = not negated
    return ignored


def _python_project_files_check(stack: str, project_dir: Path) -> CheckResult | None:
    """Validate Python project files that make the generated handoff reproducible."""
    meta = STACK_META[stack]
    pyproject = _load_pyproject(project_dir)
    if "uv" not in meta.package_manager or pyproject is None:
        return None

    required_pre_commit = any(
        item.split("#", 1)[0].strip() == ".pre-commit-config.yaml"
        for item in meta.default_structure
    )
    remediation: list[str] = []
    if required_pre_commit and not (project_dir / ".pre-commit-config.yaml").is_file():
        remediation.append("Add the required `.pre-commit-config.yaml`.")
    if not (project_dir / "uv.lock").is_file():
        remediation.append("Run `uv lock` and keep `uv.lock` with the project.")
    elif _gitignore_ignores_uv_lock(project_dir):
        remediation.append("Remove `uv.lock` from `.gitignore` so the lockfile can be committed.")

    return CheckResult(
        name="project-files",
        passed=not remediation,
        detail="" if not remediation else "Required project files are missing or ignored.",
        remediation=" ".join(remediation),
    )


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
    smoke_command = _python_entrypoint_smoke_command(pyproject)
    if smoke_command:
        commands["smoke"] = smoke_command
    else:
        commands.pop("smoke", None)
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
        return CheckResult(
            name=name,
            passed=False,
            detail="This check did not pass.",
            exit_code=result.returncode,
            remediation=(
                f"Run `{cmd}` from the recorded project folder to see the full local output."
            ),
            duration_seconds=time.monotonic() - started,
            **metadata,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            passed=False,
            detail="This check took too long and was stopped.",
            remediation=f"Run `{cmd}` from the project folder to inspect it locally.",
            duration_seconds=time.monotonic() - started,
            **metadata,
        )


def _install_deps(stack: str, project_dir: Path) -> CheckResult:
    """Install project dependencies based on the stack's package manager."""
    meta = STACK_META.get(stack)
    if not meta:
        return CheckResult(
            name="install",
            passed=False,
            detail="Forge cannot verify this project type.",
            remediation=(
                "Check the recorded stack, or scaffold a new target with a supported stack."
            ),
        )

    pkg_mgr = meta.package_manager

    # Fullstack "both" needs uv + npm
    if pkg_mgr == "uv + npm":
        uv_result = _run_check("install (python)", "uv sync", project_dir, timeout=60)
        if not uv_result.passed:
            return CheckResult(
                name="install",
                passed=False,
                detail=uv_result.detail,
                remediation=uv_result.remediation,
            )
        frontend_dir = project_dir / "frontend"
        if frontend_dir.exists():
            npm_result = _run_check("install (node)", "npm install", frontend_dir, timeout=60)
            if not npm_result.passed:
                return CheckResult(
                    name="install",
                    passed=False,
                    detail=npm_result.detail,
                    remediation=npm_result.remediation,
                )
        return CheckResult(name="install", passed=True)

    install_cmd = (
        _python_install_command(project_dir) if pkg_mgr == "uv" else _INSTALL_COMMANDS.get(pkg_mgr)
    )
    if not install_cmd:
        return CheckResult(
            name="install",
            passed=False,
            detail="Forge does not know how to install this project's dependencies.",
            remediation=(
                "Install them with the project's documented command, then rerun its checks."
            ),
        )
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
                return CheckResult(
                    name="health",
                    passed=False,
                    detail="The app stopped before the health check could connect.",
                    exit_code=process.returncode,
                    remediation="Run the recorded start command locally and review its output.",
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
            detail="The app started but did not become healthy.",
            remediation=("Confirm the recorded start command and health address, then try again."),
            attempted_endpoints=tuple(attempted_endpoints),
            duration_seconds=time.monotonic() - started,
            **metadata,
        )
    except Exception:
        return CheckResult(
            name="health",
            passed=False,
            detail="Forge could not complete the health check.",
            remediation=(
                "Run the recorded start command locally and confirm the configured address "
                "responds."
            ),
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
            checks=[
                CheckResult(
                    name="verify",
                    passed=False,
                    detail="Forge cannot verify this project type.",
                    remediation=(
                        "Check the recorded stack, or scaffold a new target with a supported stack."
                    ),
                )
            ]
        )

    report = VerifyReport()
    dev = _effective_dev_commands(stack, project_dir)

    # 1. Install dependencies
    install_result = _install_deps(stack, project_dir)
    report.checks.append(install_result)
    project_files_result = _python_project_files_check(stack, project_dir)
    if project_files_result is not None:
        report.checks.append(project_files_result)
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
                    detail=(
                        "Not run because dependency installation did not finish. Fix the install "
                        "step, then rerun the remaining checks."
                    ),
                )
            )
        return report

    # 2. Run dev_commands checks and bounded console-entry-point smoke tests.
    for check_name in ("lint", "typecheck", "build", "test", "smoke"):
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
