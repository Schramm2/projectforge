"""First-run setup wizard for UbundiForge."""

import json
import shutil

import questionary
from rich.console import Console
from rich.table import Table

from ubundiforge.config import SUPPORTED_BACKENDS, check_backend_installed
from ubundiforge.conventions import CONVENTIONS_PATH, DEFAULT_CONVENTIONS, FORGE_DIR

CONFIG_PATH = FORGE_DIR / "config.json"

SUPPORTED_EDITORS = [
    ("cursor", "Cursor"),
    ("code", "VS Code"),
    ("antigravity", "Antigravity"),
    ("windsurf", "Windsurf"),
    ("zed", "Zed"),
]


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
        choices = [questionary.Choice(b, value=b) for b in available]
        default_backend = questionary.select(
            "Which AI tool should Forge use by default?",
            choices=choices,
            default=available[0],
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
    for cmd, label in SUPPORTED_EDITORS:
        if shutil.which(cmd):
            available_editors.append((cmd, label))
            editor_table.add_row(label, "[green]Installed[/green]")
        else:
            editor_table.add_row(label, "[dim]Not found[/dim]")

    console.print(editor_table)
    console.print()

    if not available_editors:
        preferred_editor = ""
        console.print(
            "[dim]No supported editors found. "
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

    # --- Step 4: Conventions file ---
    console.print("[bold]Step 4:[/bold] Conventions file.\n")

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
    }
    save_forge_config(config)

    console.print("[green bold]Setup complete.[/green bold]")
    console.print(f"[dim]Config saved to {CONFIG_PATH}[/dim]")
    console.print("[dim]Run [bold]forge --setup[/bold] anytime to reconfigure.[/dim]\n")

    return config
