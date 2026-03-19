"""Post-scaffold verification — install deps, run checks, probe health endpoint."""

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from rich.console import Console

from ubundiforge.stacks import STACK_META
from ubundiforge.ui import badge, make_table, muted


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    passed: bool
    detail: str = ""
    skipped: bool = False


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


def _run_check(
    name: str,
    cmd: str,
    cwd: Path,
    timeout: int = 30,
) -> CheckResult:
    """Run a shell command and return pass/fail."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return CheckResult(name=name, passed=True)
        stderr = result.stderr.strip()
        detail = stderr[:200] if stderr else f"exit code {result.returncode}"
        return CheckResult(name=name, passed=False, detail=detail)
    except subprocess.TimeoutExpired:
        return CheckResult(name=name, passed=False, detail="timed out")


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

    install_cmd = _INSTALL_COMMANDS.get(pkg_mgr)
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
) -> CheckResult:
    """Start the server, poll /health, then kill it."""
    port = _extract_port(run_cmd)
    process = None
    try:
        process = subprocess.Popen(
            run_cmd,
            shell=True,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for attempt in range(8):
            time.sleep(1.5)
            # Check if process died
            if process.poll() is not None:
                stderr = (process.stderr.read() or b"").decode(errors="replace")
                detail = stderr.strip()[:200] if stderr.strip() else "server exited early"
                return CheckResult(name="health", passed=False, detail=detail)
            for path in ("/health", "/ready"):
                try:
                    resp = urlopen(f"http://localhost:{port}{path}", timeout=3)
                    if resp.status == 200:
                        return CheckResult(name="health", passed=True)
                except (URLError, OSError, TimeoutError):
                    continue
        return CheckResult(
            name="health", passed=False, detail=f"no response on :{port}/health after 12s"
        )
    except Exception as exc:
        return CheckResult(name="health", passed=False, detail=str(exc)[:200])
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
    dev = meta.dev_commands

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
        health_result = _check_health(project_dir, run_cmd)
        report.checks.append(health_result)

    return report


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
