"""First-run setup wizard for ProjectForge."""

import json
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import questionary
from rich.console import Console

from ubundiforge.config import (
    SUPPORTED_BACKENDS,
    BackendStatus,
    get_backend_statuses,
)
from ubundiforge.conventions import BUNDLED_CONVENTIONS_DIR, CONVENTIONS_PATH, FORGE_DIR
from ubundiforge.questionary_theme import prompt_confirm, prompt_select, prompt_text
from ubundiforge.safety import check_for_secrets
from ubundiforge.ui import (
    badge,
    grouped_lines,
    make_panel,
    make_step_panel,
    make_table,
    muted,
    status_line,
    subtle,
)

CONFIG_PATH = FORGE_DIR / "config.json"
CONFIG_VERSION = 1
_CONFIG_TYPES = {
    "config_version": int,
    "preferred_editor": str,
    "available_backends": list,
    "backend_models": dict,
    "docker_available": bool,
    "projects_dir": str,
    "agents": bool,
    "sound": bool,
    "conventions_profile": str,
}

# (cli_command, display_label, macOS .app bundle name)
SUPPORTED_EDITORS = [
    ("cursor", "Cursor", "Cursor.app"),
    ("code", "VS Code", "Visual Studio Code.app"),
    ("antigravity", "Antigravity", "Antigravity.app"),
    ("windsurf", "Windsurf", "Windsurf.app"),
    ("zed", "Zed", "Zed.app"),
]

_BACKEND_LOGIN_HINTS = {
    "claude": "claude auth login",
    "codex": "codex login",
}
_BACKEND_INSTALL_URLS = {
    "claude": "https://code.claude.com/docs/en/setup",
    "gemini": "https://geminicli.com/docs/get-started/installation/",
    "codex": "https://github.com/openai/codex",
}


def _check_editor_installed(cli_cmd: str, app_bundle: str) -> tuple[bool, bool]:
    """Check if an editor is available via CLI and/or as a macOS .app bundle.

    Returns:
        (cli_available, app_installed) tuple.
    """
    cli_available = shutil.which(cli_cmd) is not None

    app_installed = False
    if platform.system() == "Darwin":
        app_installed = Path(f"/Applications/{app_bundle}").exists()

    return cli_available, app_installed


def _get_git_config(key: str) -> str:
    """Read a git config value, returning empty string if unset."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return ""


def _set_git_config(key: str, value: str) -> bool:
    """Write a git config value, returning whether it succeeded."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", key, value],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def _backend_readiness_cell(status: BackendStatus):
    """Return a badge or muted text for a backend readiness value."""
    if not status.installed:
        return muted("Not found")
    if status.ready is True:
        return badge("Ready", "success")
    if status.ready is False:
        return badge("Needs login", "warning")
    return badge("Not auto-checked", "warning")


def needs_setup() -> bool:
    """Return True if the setup wizard has never been completed."""
    return not CONFIG_PATH.exists()


def _normalize_forge_config(payload: object) -> dict:
    """Validate config shape and migrate the unversioned v0.4.1 format in memory."""
    if not isinstance(payload, dict):
        raise ValueError("config root must be an object")
    unknown_keys = sorted(set(payload) - set(_CONFIG_TYPES))
    if unknown_keys:
        raise ValueError(f"unsupported config key: {unknown_keys[0]}")

    normalized = {"config_version": CONFIG_VERSION, **payload}
    if normalized["config_version"] != CONFIG_VERSION:
        raise ValueError(f"unsupported config version: {normalized['config_version']}")
    for key, value in normalized.items():
        expected_type = _CONFIG_TYPES[key]
        if not isinstance(value, expected_type):
            raise ValueError(f"invalid value type for config key: {key}")

    backends = normalized.get("available_backends", [])
    if any(
        not isinstance(backend, str) or backend not in SUPPORTED_BACKENDS for backend in backends
    ):
        raise ValueError("available_backends contains an unsupported backend")
    backend_models = normalized.get("backend_models", {})
    if any(
        backend not in SUPPORTED_BACKENDS or not isinstance(model, str) or not model.strip()
        for backend, model in backend_models.items()
    ):
        raise ValueError("backend_models contains an invalid override")
    if any(check_for_secrets(model) for model in backend_models.values()):
        raise ValueError("backend_models contains a credential-like value")
    return normalized


def load_forge_config() -> dict:
    """Load the saved Forge config, or return defaults if none exists."""
    if CONFIG_PATH.exists():
        try:
            return _normalize_forge_config(json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, ValueError):
            from ubundiforge.ui import create_console, status_line

            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup_path = CONFIG_PATH.with_name(f"{CONFIG_PATH.name}.corrupt-{timestamp}")
            try:
                CONFIG_PATH.replace(backup_path)
                recovery = f"The original was preserved at {backup_path}."
            except OSError:
                recovery = "The original could not be moved; it was left unchanged."
            console = create_console()
            console.print(
                status_line(
                    f"Config file is corrupted: {CONFIG_PATH}. {recovery} "
                    "Run forge --setup to recreate it.",
                    accent="amber",
                )
            )
            return {}
        except OSError:
            return {}
    return {}


def save_forge_config(config: dict) -> None:
    """Atomically write Forge config with user-only permissions."""
    normalized = _normalize_forge_config(config)
    FORGE_DIR.mkdir(parents=True, exist_ok=True)
    fd, raw_temp_path = tempfile.mkstemp(
        prefix=f".{CONFIG_PATH.name}.",
        suffix=".tmp",
        dir=FORGE_DIR,
        text=True,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(json.dumps(normalized, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(0o600)
        temp_path.replace(CONFIG_PATH)
    finally:
        temp_path.unlink(missing_ok=True)


def _routing_summary(available: list[str], console: Console) -> None:
    """Print a summary of how multi-backend routing will work."""
    if not available:
        body = grouped_lines(
            [
                subtle("No ready backends detected yet."),
                muted("Finish logging into an installed backend to enable scaffolding."),
                muted("Use --use after login if you want to force a specific backend."),
            ]
        )
        console.print(make_panel(body, title="Routing", accent="amber"))
        return

    has_claude = "claude" in available
    has_gemini = "gemini" in available
    has_codex = "codex" in available

    if has_claude and has_gemini and has_codex:
        body = grouped_lines(
            [
                subtle("All three backends detected. Specialist routing is available."),
                subtle("Architecture & backend code -> claude"),
                subtle("Frontend & UI -> gemini"),
                subtle("Tests & automation -> codex"),
                muted("Use --use to override routing for any run."),
            ]
        )
        console.print(make_panel(body, title="Routing", accent="aqua"))
    elif has_claude and has_gemini:
        body = grouped_lines(
            [
                subtle("claude + gemini detected."),
                subtle("Architecture, backend & tests -> claude"),
                subtle("Frontend & UI -> gemini"),
                muted("Use --use to override routing for any run."),
            ]
        )
        console.print(make_panel(body, title="Routing", accent="aqua"))
    elif has_claude and has_codex:
        body = grouped_lines(
            [
                subtle("claude + codex detected."),
                subtle("Architecture & backend -> claude"),
                subtle("Tests & automation -> codex"),
                muted("Use --use to override routing for any run."),
            ]
        )
        console.print(make_panel(body, title="Routing", accent="aqua"))
    elif has_claude:
        body = grouped_lines(
            [
                subtle("Only claude detected. It will handle all scaffolding."),
                muted("Install gemini and/or codex to enable specialist routing."),
                muted("Use --use to override routing for any run."),
            ]
        )
        console.print(make_panel(body, title="Routing", accent="amber"))
    else:
        backend = available[0] if available else "?"
        body = grouped_lines(
            [
                subtle(f"Only {backend} detected. It will handle all scaffolding."),
                muted("Use --use to override routing for any run."),
            ]
        )
        console.print(make_panel(body, title="Routing", accent="amber"))


def run_setup(console: Console) -> dict:
    """Run the interactive setup wizard. Returns the saved config dict."""
    console.print()
    console.print(
        make_panel(
            grouped_lines(
                [
                    "Welcome to ProjectForge Setup",
                    subtle("Let's configure the tools and defaults behind each scaffold."),
                ]
            ),
            title="Setup",
            accent="violet",
        )
    )

    # --- Step 1: Detect AI CLI tools ---
    console.print()
    console.print(make_step_panel(1, 8, "Checking AI coding assistants", accent="aqua"))

    table = make_table(title="AI Assistants", accent="aqua")
    table.add_column("Tool")
    table.add_column("Strength")
    table.add_column("Status")
    table.add_column("Readiness")

    strengths = {
        "claude": "Architecture & backend",
        "gemini": "Frontend & UI",
        "codex": "Tests & automation",
    }

    backend_statuses = get_backend_statuses()
    available: list[str] = []
    for backend in SUPPORTED_BACKENDS:
        status = backend_statuses[backend]
        strength = strengths.get(backend, "")
        if status.usable:
            available.append(backend)
        if status.installed:
            table.add_row(
                backend,
                strength,
                badge("Installed", "success"),
                _backend_readiness_cell(status),
            )
        else:
            table.add_row(backend, strength, muted("Not found"), muted("Not found"))

    console.print(table)
    console.print()

    if not any(status.installed for status in backend_statuses.values()):
        console.print(
            make_panel(
                grouped_lines(
                    [
                        "No AI CLI tools found.",
                        subtle("Forge needs at least one of: claude, gemini, or codex."),
                        *[
                            muted(f"{backend}: {_BACKEND_INSTALL_URLS[backend]}")
                            for backend in SUPPORTED_BACKENDS
                        ],
                        muted(
                            "Install one, complete its provider-owned login, then run "
                            "forge doctor and forge --setup."
                        ),
                    ]
                ),
                title="Setup",
                accent="amber",
            )
        )
        raise SystemExit(1)

    not_ready_backends = [
        backend
        for backend, status in backend_statuses.items()
        if status.installed and status.ready is False
    ]
    if not_ready_backends:
        lines = [
            subtle(
                f"{backend} is installed but not ready for scaffolding. "
                f"Run {_BACKEND_LOGIN_HINTS.get(backend, backend)}."
            )
            for backend in not_ready_backends
        ]
        lines.append(
            muted(
                "Complete provider-owned login, then run forge doctor. Automatic routing skips "
                "these backends until they are ready."
            )
        )
        console.print(make_panel(grouped_lines(lines), title="Backend Login", accent="amber"))

    unknown_backends = [
        backend
        for backend, status in backend_statuses.items()
        if status.installed and status.ready is None
    ]
    if unknown_backends:
        lines = [
            subtle(f"{backend} is installed, but Forge could not auto-check readiness safely.")
            for backend in unknown_backends
        ]
        lines.append(
            muted(
                "Forge will not route to these backends until readiness is confirmed by a "
                "provider-specific preflight. Complete official authentication, then run "
                "forge doctor for the current classification."
            )
        )
        console.print(make_panel(grouped_lines(lines), title="Backend Checks", accent="amber"))

    # --- Step 2: Routing summary ---
    console.print(make_step_panel(2, 8, "Backend routing", accent="violet"))
    _routing_summary(available, console)

    # --- Step 3: Model selection per backend ---
    console.print(make_step_panel(3, 8, "Model preferences", accent="plum"))

    existing_models = load_forge_config().get("backend_models", {})
    backend_models: dict[str, str] = {}

    if len(available) > 0:
        console.print(
            status_line(
                "Use each provider's current default, or enter an advanced override.",
                accent="plum",
            )
        )
        console.print()

        for backend in available:
            existing = existing_models.get(backend, "")
            choices = [
                questionary.Choice(
                    "Provider default / auto (recommended)",
                    value="_provider_default",
                )
            ]
            if existing:
                choices.append(
                    questionary.Choice(
                        f"Keep existing override: {existing}",
                        value=existing,
                    )
                )
            choices.append(questionary.Choice("Custom model ID...", value="_custom"))

            model_val = prompt_select(
                f"Choose the model for {backend}",
                choices=choices,
                default=existing or "_provider_default",
            ).ask()
            if model_val is None:
                raise SystemExit(0)

            if model_val == "_custom":
                model_val = prompt_text(
                    f"Enter a custom model ID for {backend}",
                    default=existing,
                ).ask()
                if model_val is None:
                    raise SystemExit(0)
                model_val = model_val.strip()

            if model_val and model_val != "_provider_default":
                backend_models[backend] = model_val

        if backend_models:
            model_table = make_table(title="Saved Models", accent="plum")
            model_table.add_column("Backend")
            model_table.add_column("Model")
            for b, m in backend_models.items():
                model_table.add_row(b, m)
            console.print(model_table)
        else:
            console.print(status_line("Using default models for all backends.", accent="plum"))
        console.print()

    # --- Step 4: Pick preferred editor ---
    console.print(make_step_panel(4, 8, "Detecting editors", accent="amber"))

    editor_table = make_table(title="Editors", accent="amber")
    editor_table.add_column("Editor")
    editor_table.add_column("Status")

    available_editors: list[tuple[str, str]] = []

    for cmd, label, app_bundle in SUPPORTED_EDITORS:
        cli_ok, app_ok = _check_editor_installed(cmd, app_bundle)
        if cli_ok:
            available_editors.append((cmd, label))
            editor_table.add_row(label, badge("Installed", "success"))
        elif app_ok:
            available_editors.append((cmd, label))
            editor_table.add_row(label, badge("Installed", "success"))
        else:
            editor_table.add_row(label, muted("Not found"))

    console.print(editor_table)
    console.print()

    if not available_editors:
        preferred_editor = ""
        console.print(
            status_line(
                "No editors with CLI access found. Open projects manually.",
                accent="amber",
            )
        )
    elif len(available_editors) == 1:
        preferred_editor = available_editors[0][0]
        console.print(
            status_line(
                f"Only {available_editors[0][1]} found — using it as default.",
                accent="amber",
            )
        )
    else:
        choices = [questionary.Choice(label, value=cmd) for cmd, label in available_editors]
        choices.append(questionary.Choice("None — I'll open projects manually", value=""))
        preferred_editor = prompt_select(
            "Choose the editor Forge should open by default",
            choices=choices,
        ).ask()
        if preferred_editor is None:
            raise SystemExit(0)
        console.print()

    # --- Step 5: Git check ---
    console.print(make_step_panel(5, 8, "Checking git", accent="aqua"))

    git_table = make_table(title="Git", accent="aqua")
    git_table.add_column("Check")
    git_table.add_column("Status")

    git_installed = shutil.which("git") is not None
    git_table.add_row(
        "git",
        badge("Installed", "success") if git_installed else badge("Not found", "error"),
    )

    if git_installed:
        git_name = _get_git_config("user.name")
        git_email = _get_git_config("user.email")
        git_table.add_row(
            "user.name",
            git_name if git_name else badge("Not set", "warning"),
        )
        git_table.add_row(
            "user.email",
            git_email if git_email else badge("Not set", "warning"),
        )

    console.print(git_table)
    console.print()

    if not git_installed:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        "Git is not installed. Forge uses git init on every scaffold.",
                        subtle("Install git and run forge --setup again."),
                    ]
                ),
                title="Git",
                accent="amber",
            )
        )
    elif not git_name or not git_email:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        "Git user.name or user.email is not configured.",
                        subtle("Forge runs git init + commit on scaffolded projects."),
                        subtle('git config --global user.name "Your Name"'),
                        subtle('git config --global user.email "you@example.com"'),
                    ]
                ),
                title="Git",
                accent="amber",
            )
        )
        configure_git = prompt_confirm("Configure git identity now", default=True).ask()
        if configure_git is None:
            raise SystemExit(0)
        if configure_git:
            entered_name = prompt_text("Git user.name", default=git_name).ask()
            if entered_name is None:
                raise SystemExit(0)

            entered_email = prompt_text("Git user.email", default=git_email).ask()
            if entered_email is None:
                raise SystemExit(0)

            entered_name = entered_name.strip()
            entered_email = entered_email.strip()

            name_ok = bool(entered_name) and _set_git_config("user.name", entered_name)
            email_ok = bool(entered_email) and _set_git_config("user.email", entered_email)
            if name_ok and email_ok:
                git_name = entered_name
                git_email = entered_email
                console.print(status_line("Saved git identity for new scaffolds.", accent="aqua"))
            else:
                console.print(
                    status_line(
                        "Could not save git identity automatically. You can rerun "
                        "forge --setup later.",
                        accent="amber",
                    )
                )

    # --- Step 6: Docker check ---
    console.print(make_step_panel(6, 8, "Checking Docker", accent="violet"))

    docker_installed = shutil.which("docker") is not None
    if docker_installed:
        console.print(status_line("Docker is installed.", accent="aqua"))
    else:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        "Docker not found.",
                        subtle("Forge can still scaffold Docker support."),
                        muted(
                            "You will not be able to validate Dockerfiles until Docker is "
                            "installed."
                        ),
                    ]
                ),
                title="Docker",
                accent="violet",
            )
        )

    # --- Step 7: Default project directory ---
    console.print(make_step_panel(7, 8, "Default project directory", accent="plum"))

    existing_dir = load_forge_config().get("projects_dir", "")
    default_dir = existing_dir or ""

    console.print(
        make_panel(
            grouped_lines(
                [
                    "Where should Forge create new projects?",
                    subtle(
                        "Leave empty to create each new project inside the directory "
                        "where you run forge."
                    ),
                ]
            ),
            title="Projects",
            accent="plum",
        )
    )
    projects_dir = prompt_text(
        "Set the default project directory",
        default=default_dir,
    ).ask()
    if projects_dir is None:
        raise SystemExit(0)
    projects_dir = projects_dir.strip()

    if projects_dir:
        expanded = Path(projects_dir).expanduser().resolve()
        if not expanded.exists():
            create = prompt_confirm(
                f"Create {expanded}",
                default=True,
            ).ask()
            if create is None:
                raise SystemExit(0)
            if create:
                expanded.mkdir(parents=True, exist_ok=True)
                console.print(status_line(f"Created {expanded}", accent="aqua"))
        else:
            console.print(status_line(f"Using {expanded}", accent="plum"))
        projects_dir = str(expanded)
    else:
        console.print(
            status_line(
                "New projects will be created inside the current directory you run forge from.",
                accent="plum",
            )
        )

    # --- Step 8: Conventions & media ---
    console.print(make_step_panel(8, 8, "Conventions & media", accent="aqua"))

    console.print(
        make_panel(
            grouped_lines(
                [
                    "Forge now compiles bundled conventions for each scaffolded stack.",
                    subtle(f"Bundled source tree: {BUNDLED_CONVENTIONS_DIR}"),
                    muted(
                        "Repo admins can inspect or customize bundled sources with "
                        "forge admin conventions."
                    ),
                ]
            ),
            title="Conventions",
            accent="aqua",
        )
    )
    if CONVENTIONS_PATH.exists():
        console.print(
            status_line(
                (
                    f"Legacy user conventions file detected at {CONVENTIONS_PATH}. "
                    "Forge no longer creates this file during setup."
                ),
                accent="amber",
            )
        )

    # Check media collections in the repo's media/ folder
    from ubundiforge.media_assets import MEDIA_DIR, list_collections

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    collections = list_collections()
    if collections:
        names = ", ".join(f"{c.name} ({c.file_count})" for c in collections)
        console.print(status_line(f"Media collections: {names}", accent="aqua"))
    else:
        console.print(
            make_panel(
                grouped_lines(
                    [
                        f"Media folder: {MEDIA_DIR}",
                        subtle(
                            "Create a named subfolder and drop images, fonts, or icons inside it."
                        ),
                        subtle("Example: media/my-brand/logo.svg"),
                        muted("Forge will offer to import the collection during each scaffold."),
                    ]
                ),
                title="Media Assets",
                accent="aqua",
            )
        )

    # --- Save config ---
    config = {
        "preferred_editor": preferred_editor,
        "available_backends": available,
        "backend_models": backend_models,
        "docker_available": docker_installed,
        "projects_dir": projects_dir,
    }
    save_forge_config(config)

    console.print(
        make_panel(
            grouped_lines(
                [
                    subtle("Setup complete."),
                    subtle(f"Config saved to {CONFIG_PATH}"),
                    muted("Run forge --setup anytime to reconfigure."),
                ]
            ),
            title="Setup Complete",
            accent="aqua",
        )
    )

    return config
