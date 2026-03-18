"""First-run setup wizard for UbundiForge."""

import json
import platform
import shutil
import subprocess
from pathlib import Path

import questionary
from rich.console import Console
from rich.table import Table

from ubundiforge.config import SUPPORTED_BACKENDS, check_backend_installed
from ubundiforge.conventions import CONVENTIONS_PATH, DEFAULT_CONVENTIONS, FORGE_DIR

CONFIG_PATH = FORGE_DIR / "config.json"

# (cli_command, display_label, macOS .app bundle name)
SUPPORTED_EDITORS = [
    ("cursor", "Cursor", "Cursor.app"),
    ("code", "VS Code", "Visual Studio Code.app"),
    ("antigravity", "Antigravity", "Antigravity.app"),
    ("windsurf", "Windsurf", "Windsurf.app"),
    ("zed", "Zed", "Zed.app"),
]


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


def needs_setup() -> bool:
    """Return True if the setup wizard has never been completed."""
    return not CONFIG_PATH.exists()


def load_forge_config() -> dict:
    """Load the saved Forge config, or return defaults if none exists."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_forge_config(config: dict) -> None:
    """Write Forge config to ~/.forge/config.json."""
    FORGE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def run_setup(console: Console) -> dict:
    """Run the interactive setup wizard. Returns the saved config dict."""
    console.print()
    console.print("[bold cyan]Welcome to UbundiForge Setup[/bold cyan]")
    console.print(
        "[dim]Let's make sure everything is configured before your first scaffold.[/dim]\n"
    )

    # --- Step 1: Detect AI CLI tools ---
    console.print("[bold]Step 1:[/bold] Checking for AI coding assistants...\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Tool")
    table.add_column("Status")

    available: list[str] = []
    for backend in SUPPORTED_BACKENDS:
        installed = check_backend_installed(backend)
        if installed:
            available.append(backend)
            table.add_row(backend, "[green]Installed[/green]")
        else:
            table.add_row(backend, "[dim]Not found[/dim]")

    console.print(table)
    console.print()

    if not available:
        console.print(
            "[red bold]No AI CLI tools found.[/red bold]\n"
            "[red]Forge needs at least one of: claude, gemini, or codex.[/red]\n"
            "[dim]Install one and run [bold]forge --setup[/bold] again.[/dim]"
        )
        raise SystemExit(1)

    # --- Step 2: Pick default backend ---
    console.print("[bold]Step 2:[/bold] Choose your default AI backend.\n")

    if len(available) == 1:
        default_backend = available[0]
        console.print(f"[dim]Only {default_backend} is installed — using it as default.[/dim]\n")
    else:
        existing = load_forge_config().get("default_backend")
        preselect = existing if existing in available else None
        choices = [questionary.Choice(b, value=b) for b in available]
        default_backend = questionary.select(
            "Which AI tool should Forge use by default?",
            choices=choices,
            default=preselect,
        ).ask()
        if default_backend is None:
            raise SystemExit(0)
        console.print()

    # --- Step 3: Pick preferred editor ---
    console.print("[bold]Step 3:[/bold] Detecting editors...\n")

    editor_table = Table(show_header=True, header_style="bold")
    editor_table.add_column("Editor")
    editor_table.add_column("Status")

    available_editors: list[tuple[str, str]] = []

    for cmd, label, app_bundle in SUPPORTED_EDITORS:
        cli_ok, app_ok = _check_editor_installed(cmd, app_bundle)
        if cli_ok:
            available_editors.append((cmd, label))
            editor_table.add_row(label, "[green]Installed[/green]")
        elif app_ok:
            available_editors.append((cmd, label))
            editor_table.add_row(label, "[green]Installed[/green]")
        else:
            editor_table.add_row(label, "[dim]Not found[/dim]")

    console.print(editor_table)
    console.print()

    if not available_editors:
        preferred_editor = ""
        console.print(
            "[dim]No editors with CLI access found. "
            "You can open projects manually after scaffolding.[/dim]\n"
        )
    elif len(available_editors) == 1:
        preferred_editor = available_editors[0][0]
        console.print(
            f"[dim]Only {available_editors[0][1]} found "
            f"— using it as default.[/dim]\n"
        )
    else:
        choices = [
            questionary.Choice(label, value=cmd)
            for cmd, label in available_editors
        ]
        choices.append(
            questionary.Choice("None — I'll open projects manually", value="")
        )
        preferred_editor = questionary.select(
            "Which editor should Forge open projects in?",
            choices=choices,
        ).ask()
        if preferred_editor is None:
            raise SystemExit(0)
        console.print()

    # --- Step 4: Git check ---
    console.print("[bold]Step 4:[/bold] Checking git...\n")

    git_table = Table(show_header=True, header_style="bold")
    git_table.add_column("Check")
    git_table.add_column("Status")

    git_installed = shutil.which("git") is not None
    git_table.add_row(
        "git",
        "[green]Installed[/green]" if git_installed else "[red]Not found[/red]",
    )

    if git_installed:
        git_name = _get_git_config("user.name")
        git_email = _get_git_config("user.email")
        git_table.add_row(
            "user.name",
            f"[green]{git_name}[/green]" if git_name else "[yellow]Not set[/yellow]",
        )
        git_table.add_row(
            "user.email",
            f"[green]{git_email}[/green]" if git_email else "[yellow]Not set[/yellow]",
        )

    console.print(git_table)
    console.print()

    if not git_installed:
        console.print(
            "[red]Git is not installed. Forge uses git init on every scaffold.[/red]\n"
            "[dim]Install git and run [bold]forge --setup[/bold] again.[/dim]\n"
        )
    elif not git_name or not git_email:
        console.print(
            "[yellow]Git user.name or user.email is not configured.[/yellow]\n"
            "[dim]Forge runs git init + commit on scaffolded projects. "
            "Set them with:[/dim]\n"
            "[dim]  git config --global user.name \"Your Name\"[/dim]\n"
            "[dim]  git config --global user.email \"you@example.com\"[/dim]\n"
        )

    # --- Step 5: Docker check ---
    console.print("[bold]Step 5:[/bold] Checking Docker...\n")

    docker_installed = shutil.which("docker") is not None
    if docker_installed:
        console.print("[green]Docker is installed.[/green]\n")
    else:
        console.print(
            "[dim]Docker not found. Forge will still offer the Docker option,\n"
            "but scaffolded Dockerfiles won't be testable until Docker is installed.[/dim]\n"
        )

    # --- Step 6: Default project directory ---
    console.print("[bold]Step 6:[/bold] Default project directory.\n")

    existing_dir = load_forge_config().get("projects_dir", "")
    default_dir = existing_dir or ""

    console.print(
        "[dim]Where should Forge create new projects?\n"
        "Leave empty to use the current directory each time.[/dim]\n"
    )
    projects_dir = questionary.text(
        "Default project directory:",
        default=default_dir,
    ).ask()
    if projects_dir is None:
        raise SystemExit(0)
    projects_dir = projects_dir.strip()

    if projects_dir:
        expanded = Path(projects_dir).expanduser().resolve()
        if not expanded.exists():
            create = questionary.confirm(
                f"{expanded} doesn't exist. Create it?",
                default=True,
            ).ask()
            if create is None:
                raise SystemExit(0)
            if create:
                expanded.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]Created {expanded}[/green]\n")
        else:
            console.print(f"[dim]Using {expanded}[/dim]\n")
        projects_dir = str(expanded)
    else:
        console.print("[dim]Will use current directory.[/dim]\n")

    # --- Step 7: Conventions file ---
    console.print("[bold]Step 7:[/bold] Conventions file.\n")

    if CONVENTIONS_PATH.exists():
        console.print(f"[dim]Found existing conventions at {CONVENTIONS_PATH}[/dim]\n")
    else:
        console.print(
            "[dim]Forge uses a conventions file to inject your team's coding standards\n"
            "into every scaffold. A default one will be created for you.[/dim]\n"
        )
        FORGE_DIR.mkdir(parents=True, exist_ok=True)
        CONVENTIONS_PATH.write_text(DEFAULT_CONVENTIONS)
        console.print(f"[green]Created default conventions at {CONVENTIONS_PATH}[/green]")
        console.print("[dim]Edit this file anytime to customize your project standards.[/dim]\n")

    # --- Save config ---
    config = {
        "default_backend": default_backend,
        "preferred_editor": preferred_editor,
        "available_backends": available,
        "docker_available": docker_installed,
        "projects_dir": projects_dir,
    }
    save_forge_config(config)

    console.print("[green bold]Setup complete.[/green bold]")
    console.print(f"[dim]Config saved to {CONFIG_PATH}[/dim]")
    console.print("[dim]Run [bold]forge --setup[/bold] anytime to reconfigure.[/dim]\n")

    return config
