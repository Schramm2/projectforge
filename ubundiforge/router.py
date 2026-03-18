"""AI backend routing — picks the best CLI tool for each scaffold phase.

Strengths:
  - Claude Code: complex reasoning, multi-file architecture, backend work, self-correction
  - Gemini CLI: frontend and UI work, richer aesthetics, sophisticated UI components
  - Codex CLI: tests, automation, mechanical refactors, backward compatibility checks

When all three are installed each phase routes to the strongest backend.
When fewer are available the installed backends absorb the missing ones' work.
--use always overrides everything to a single backend.
"""

from ubundiforge.config import check_backend_installed

# Scaffold phases (execution order matters)
PHASE_ARCHITECTURE = "architecture"
PHASE_FRONTEND = "frontend"
PHASE_TESTS = "tests"
PHASE_VERIFY = "verify"

PHASE_LABELS = {
    PHASE_ARCHITECTURE: "Architecture & Core",
    PHASE_FRONTEND: "Frontend & UI",
    PHASE_TESTS: "Tests & Automation",
    PHASE_VERIFY: "Verify & Fix",
}

# Which phases each stack needs
STACK_PHASES: dict[str, list[str]] = {
    "nextjs": [PHASE_ARCHITECTURE, PHASE_FRONTEND, PHASE_TESTS, PHASE_VERIFY],
    "fastapi": [PHASE_ARCHITECTURE, PHASE_TESTS, PHASE_VERIFY],
    "fastapi-ai": [PHASE_ARCHITECTURE, PHASE_TESTS, PHASE_VERIFY],
    "both": [PHASE_ARCHITECTURE, PHASE_FRONTEND, PHASE_TESTS, PHASE_VERIFY],
    "python-cli": [PHASE_ARCHITECTURE, PHASE_TESTS, PHASE_VERIFY],
    "ts-package": [PHASE_ARCHITECTURE, PHASE_TESTS, PHASE_VERIFY],
    "python-worker": [PHASE_ARCHITECTURE, PHASE_TESTS, PHASE_VERIFY],
}

# Ideal backend for each phase
PHASE_IDEAL_BACKEND: dict[str, str] = {
    PHASE_ARCHITECTURE: "claude",
    PHASE_FRONTEND: "gemini",
    PHASE_TESTS: "codex",
    PHASE_VERIFY: "claude",
}

# Description keywords that signal a testing/automation project → Codex for architecture
_CODEX_KEYWORDS = {"test", "testing", "ci/cd", "ci", "automation", "pipeline", "refactor"}

FALLBACK_ORDER = ("claude", "gemini", "codex")


def _detect_codex_project(description: str) -> bool:
    """Check if the project description suggests a testing/automation project."""
    words = set(description.lower().split())
    return bool(words & _CODEX_KEYWORDS)


def pick_phase_backends(
    stack: str,
    override: str | None = None,
    description: str = "",
) -> list[tuple[str, str]]:
    """Pick the best backend for each scaffold phase.

    Args:
        stack: The stack identifier.
        override: Force a single backend for all phases (--use flag).
        description: Project description, used for keyword-based routing.

    Returns:
        List of (phase, backend) tuples in execution order.
    """
    phases = STACK_PHASES.get(stack, [PHASE_ARCHITECTURE, PHASE_TESTS])

    if override:
        return [(phase, override) for phase in phases]

    available = {b for b in FALLBACK_ORDER if check_backend_installed(b)}
    codex_project = _detect_codex_project(description)

    result = []
    for phase in phases:
        if codex_project and phase == PHASE_ARCHITECTURE and "codex" in available:
            backend = "codex"
        else:
            ideal = PHASE_IDEAL_BACKEND.get(phase, "claude")
            if ideal in available:
                backend = ideal
            elif "claude" in available:
                backend = "claude"
            elif available:
                backend = next(iter(available))
            else:
                backend = "claude"  # Will fail at install check later
        result.append((phase, backend))

    return result


def merge_adjacent_phases(
    phase_backends: list[tuple[str, str]],
) -> list[tuple[list[str], str]]:
    """Merge adjacent phases that use the same backend into groups.

    Returns:
        List of (phases, backend) tuples where phases is a list of phase names.
    """
    if not phase_backends:
        return []

    merged: list[tuple[list[str], str]] = []
    current_phases = [phase_backends[0][0]]
    current_backend = phase_backends[0][1]

    for phase, backend in phase_backends[1:]:
        if backend == current_backend:
            current_phases.append(phase)
        else:
            merged.append((current_phases, current_backend))
            current_phases = [phase]
            current_backend = backend

    merged.append((current_phases, current_backend))
    return merged


# Legacy single-backend functions (kept for backward compat)


def pick_backend(stack: str, override: str | None = None) -> str:
    """Pick a single AI CLI backend (legacy — use pick_phase_backends instead)."""
    if override:
        return override
    return "claude"


def pick_backend_with_fallback(stack: str, override: str | None = None) -> tuple[str, bool]:
    """Pick a backend with fallback (legacy — use pick_phase_backends instead)."""
    primary = pick_backend(stack, override)

    if check_backend_installed(primary):
        return primary, False

    for fallback in FALLBACK_ORDER:
        if fallback != primary and check_backend_installed(fallback):
            return fallback, True

    return primary, False
