"""Shared subprocess utilities for backend output processing."""

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

PHASE_TIMEOUT = 1800  # 30 minutes per phase

SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

PULSE_STYLES = {
    "aqua": ("#4D6A84", "#75DCE6", "#C6CEE6", "#75DCE6"),
    "amber": ("#77603A", "#F3BB58", "#F7D99C", "#F3BB58"),
    "violet": ("#5F4A87", "#A16EFA", "#D3BCFF", "#A16EFA"),
    "plum": ("#7B4A79", "#D768D2", "#F0B6ED", "#D768D2"),
}


def sanitize_progress_line(line: str) -> str:
    """Normalize backend output into compact text suitable for a loader."""
    clean = ANSI_RE.sub("", line).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean[:120]


def is_noisy_progress_line(line: str) -> bool:
    """Filter out raw lines that are too noisy to show directly in the loader."""
    if not line:
        return True
    noisy_prefixes = (
        "$",
        ">",
        "```",
        "diff --git",
        "@@",
        "+++",
        "---",
        "{",
        "[{",
    )
    if line.startswith(noisy_prefixes):
        return True
    if line.count("/") > 6:
        return True
    return False


def summarize_output_line(line: str) -> str | None:
    """Translate backend output into a clean user-facing progress summary."""
    lowered = line.lower()

    keyword_groups = (
        (
            ("inspect", "review", "analy", "read ", "scan", "explor", "understand"),
            "Reviewing the scaffold brief",
        ),
        (("plan", "approach", "strategy", "outline"), "Planning the next set of changes"),
        (("lint", "eslint", "ruff", "prettier"), "Running lint checks"),
        (("typecheck", "tsc", "mypy", "pyright"), "Running type checks"),
        (("test", "pytest", "vitest", "jest", "playwright", "cypress"), "Running tests and checks"),
        (
            (
                "install",
                "dependencies",
                "dependency",
                "npm ",
                "pnpm ",
                "bun ",
                "pip ",
                "uv sync",
                "poetry ",
            ),
            "Installing project dependencies",
        ),
        (
            (
                "create",
                "created",
                "patch",
                "write",
                "writing",
                "update",
                "updating",
                "edited",
                "edit ",
                "apply_patch",
                "scaffold",
            ),
            "Writing and refining project files",
        ),
        (("schema", "migration", "database", "sql"), "Preparing the data layer"),
        (("build", "compile", "bundle", "transpil"), "Building the project"),
        (
            (
                "localhost",
                "listening",
                "dev server",
                "starting server",
                "ready on",
                "running dev",
                "vite",
            ),
            "Starting the app locally",
        ),
        (("git init", "git add", "git commit", ".git"), "Finalizing the repository"),
        (
            ("error", "failed", "traceback", "exception", "cannot", "unable to", "fixing"),
            "Working through an issue in the scaffold",
        ),
        (("done", "complete", "completed", "finished", "success"), "Wrapping up this phase"),
    )

    for tokens, summary in keyword_groups:
        if any(token in lowered for token in tokens):
            return summary
    return None


def progress_summary_for_line(line: str, current: str) -> str:
    """Pick the best loader summary for a new backend output line."""
    summary = summarize_output_line(line)
    if summary:
        return summary
    if not is_noisy_progress_line(line):
        return line
    return current


def spinner_frame(elapsed: float) -> str:
    """Return the current spinner frame."""
    return SPINNER_FRAMES[int(elapsed * 10) % len(SPINNER_FRAMES)]


def spinner_style(accent: str, elapsed: float) -> str:
    """Return a pulsing spinner color to mimic a subtle fade animation."""
    palette = PULSE_STYLES.get(accent, PULSE_STYLES["violet"])
    return palette[int(elapsed * 6) % len(palette)]


def format_activity(text: str, limit: int = 54) -> str:
    """Clamp activity text so loader surfaces stay compact."""
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"
