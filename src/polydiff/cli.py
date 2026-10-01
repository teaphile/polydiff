"""polydiff CLI — One git config. Every file type gets a real diff."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .core.delegation import get_available_delegations, get_missing_delegations
from .core.git_integration import (
    install_polydiff,
    parse_diff_driver_args,
)
from .core.plugin_base import DiffOptions
from .core.registry import registry
from .render.terminal import render_terminal_summary

app = typer.Typer(
    name="polydiff",
    help="One git config. Every file type gets a real diff.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"polydiff {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """polydiff — real diffs for images, PDFs, and Excel files."""


@app.command()
def diff(
    file_a: Path = typer.Argument(..., help="First file to compare"),
    file_b: Path = typer.Argument(..., help="Second file to compare"),
    format: str = typer.Option(
        "terminal", "--format", "-f",
        help="Output format: terminal, html, json, or image"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output path (for html/image formats)"
    ),
    color: bool = typer.Option(
        True, "--color/--no-color",
        help="Enable/disable colored output"
    ),
    context_lines: int = typer.Option(
        3, "--context-lines", "-c",
        min=0,
        help="Context lines for text diffs (e.g., PDF text changes)"
    ),
    similarity_threshold: float = typer.Option(
        0.99, "--similarity-threshold",
        min=0.0,
        max=1.0,
        help="Threshold below which files are considered changed"
    ),
):
    """Compare two files directly (works with or without git)."""
    # Validate files exist
    if not file_a.exists():
        console.print(f"[red]Error:[/red] File not found: {file_a}")
        raise typer.Exit(1)
    if not file_b.exists():
        console.print(f"[red]Error:[/red] File not found: {file_b}")
        raise typer.Exit(1)

    # Find appropriate plugin
    plugin = registry.get_plugin_for_path(file_a)
    if plugin is None:
        console.print(f"[red]Error:[/red] No plugin found for extension: {file_a.suffix}")
        console.print("Run [bold]polydiff plugins list[/bold] to see available plugins.")
        raise typer.Exit(1)

    # Verify both files have same extension
    if file_a.suffix.lower() != file_b.suffix.lower():
        console.print("[yellow]Warning:[/yellow] Files have different extensions. Comparing anyway.")

    # Run diff
    options = DiffOptions(
        output_format=format,
        output_path=output,
        context_lines=context_lines,
        similarity_threshold=similarity_threshold,
        color=color,
    )

    result = plugin.diff(file_a, file_b, options)

    # Output based on format
    if format == "terminal":
        render_terminal_summary(result, color=color)
    elif format == "html":
        if result.html_output:
            if output:
                from .render.html import save_html_report
                save_html_report(result.html_output, output, title=f"polydiff: {file_a.name} vs {file_b.name}")
                console.print(f"[green]HTML report saved to:[/green] {output}")
            else:
                console.print(result.html_output)
        else:
            console.print("[yellow]Warning:[/yellow] Plugin did not generate HTML output.")
    elif format == "json":
        import json
        console.print_json(json.dumps(result.json_output, indent=2, default=str))
    elif format == "image":
        if result.artifact_path:
            console.print(f"[green]Diff image saved to:[/green] {result.artifact_path}")
        else:
            console.print("[yellow]Warning:[/yellow] Plugin did not generate an image artifact.")
    else:
        console.print(f"[red]Error:[/red] Unknown format: {format}")
        raise typer.Exit(1)


@app.command()
def install(
    scope: str = typer.Option(
        "local", "--scope", "-s",
        help="Configuration scope: local (repo) or global"
    ),
    global_flag: bool = typer.Option(
        False, "--global", "-g",
        help="Configure globally (overrides --scope)"
    ),
    local_flag: bool = typer.Option(
        False, "--local", "-l",
        help="Configure locally in current repo (overrides --scope)"
    ),
    extensions: Optional[str] = typer.Option(
        None, "--extensions", "-e",
        help="Comma-separated list of extensions to configure (default: all)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Show what would be configured without making changes"
    ),
):
    """Auto-configure git to use polydiff for binary file diffs."""
    # Determine scope
    if global_flag:
        scope = "global"
    elif local_flag:
        scope = "local"

    # Parse extensions
    ext_list = None
    if extensions:
        ext_list = [e.strip() for e in extensions.split(",")]
        # Ensure extensions start with .
        ext_list = [e if e.startswith(".") else f".{e}" for e in ext_list]

    try:
        if dry_run:
            # Show what would be done
            from .core.git_integration import DRIVER_MAPPING, get_git_root

            repo_root = get_git_root()
            if repo_root is None and scope == "local":
                console.print("[red]Error:[/red] Not inside a git repository.")
                raise typer.Exit(1)

            console.print(f"[bold]Scope:[/bold] {scope}")
            console.print(f"[bold]Repository:[/bold] {repo_root or '(global)'}")
            console.print()

            # Show .gitattributes entries
            console.print("[bold].gitattributes entries:[/bold]")
            if ext_list:
                for ext in ext_list:
                    if ext in DRIVER_MAPPING:
                        console.print(f"  *{ext}\tdiff={DRIVER_MAPPING[ext]}")
            else:
                for ext, driver in sorted(DRIVER_MAPPING.items()):
                    console.print(f"  *{ext}\tdiff={driver}")

            console.print()

            # Show git config commands
            console.print("[bold]Git config commands:[/bold]")
            config_scope = "--local" if scope == "local" else "--global"
            for driver in set(DRIVER_MAPPING.values()):
                console.print(f"  git config {config_scope} diff.{driver}.command 'polydiff diff-driver'")

            console.print()

            # Show delegation detection
            available = get_available_delegations()
            missing = get_missing_delegations()

            if available:
                console.print("[bold]Available delegated tools:[/bold]")
                for tool in set(t.name for t in available.values()):
                    console.print(f"  ✓ {tool}")

            if missing:
                console.print("[bold]Missing delegated tools (suggestions):[/bold]")
                for tool in set(t.name for t in missing.values()):
                    console.print(f"  ○ {tool} — {next(t.install_hint for t in missing.values() if t.name == tool)}")

        else:
            # Actually install
            result = install_polydiff(
                scope=scope,
                extensions=ext_list,
            )

            console.print("[green]✓ polydiff configured successfully![/green]")
            console.print()
            console.print(f"[bold]Scope:[/bold] {result['scope']}")
            console.print(f"[bold]Repository:[/bold] {result['repo_root']}")
            console.print()

            if result["gitattributes_added"]:
                console.print("[bold].gitattributes entries added:[/bold]")
                for line in result["gitattributes_added"]:
                    console.print(f"  {line}")

            if result["config_commands"]:
                console.print("[bold]Git config commands executed:[/bold]")
                for cmd in result["config_commands"]:
                    console.print(f"  {cmd}")

            # Check for delegated tools
            available = get_available_delegations()
            missing = get_missing_delegations()

            if available:
                console.print()
                console.print("[bold]Delegated tools detected and configured:[/bold]")
                for tool in set(t.name for t in available.values()):
                    console.print(f"  ✓ {tool}")

            if missing:
                console.print()
                console.print("[yellow]Suggested additional tools:[/yellow]")
                for tool in set(t.name for t in missing.values()):
                    hint = next(t.install_hint for t in missing.values() if t.name == tool)
                    console.print(f"  ○ {tool}: {hint}")

            console.print()
            console.print("[dim]Run 'git diff' on binary files to see real diffs![/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("plugins")
def plugins_list():
    """List installed polydiff plugins."""
    plugins = registry.get_plugins()

    if not plugins:
        console.print("[yellow]No plugins found.[/yellow]")
        console.print("This shouldn't happen — the built-in plugins should always be available.")
        raise typer.Exit(1)

    table = Table(title="Installed Plugins", show_header=True, header_style="bold cyan")
    table.add_column("Plugin", style="bold")
    table.add_column("Extensions")
    table.add_column("Source")

    for plugin in plugins:
        extensions = ", ".join(plugin.supported_extensions)
        table.add_row(plugin.name, extensions, "built-in")

    # Check for delegated tools
    available = get_available_delegations()
    if available:
        for ext, tool in available.items():
            table.add_row(f"{tool.name} (delegated)", ext, "external")

    console.print(table)


@app.command()
def doctor():
    """Check environment health and dependencies."""
    console.print("[bold]polydiff environment check[/bold]")
    console.print()

    # Python version
    python_version = sys.version.split()[0]
    console.print(f"[bold]Python:[/bold] {python_version}")

    # Check dependencies
    console.print()
    console.print("[bold]Dependencies:[/bold]")

    deps = {
        "typer": "typer",
        "rich": "rich",
        "pillow": "PIL",
        "scikit-image": "skimage",
        "pymupdf": "fitz",
        "openpyxl": "openpyxl",
        "jinja2": "jinja2",
    }

    for name, module in deps.items():
        try:
            __import__(module)
            console.print(f"  ✓ {name}")
        except ImportError:
            console.print(f"  ✗ {name} [red](missing)[/red]")

    # Check optional tools
    console.print()
    console.print("[bold]Optional tools:[/bold]")

    import shutil
    optional_tools = {
        "nbdime": "nbdiff",
        "daff": "daff",
        "git": "git",
    }

    for name, cmd in optional_tools.items():
        if shutil.which(cmd):
            console.print(f"  ✓ {name}")
        else:
            console.print(f"  ○ {name} [dim](not installed)[/dim]")

    # Check git version
    console.print()
    try:
        import subprocess
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
        )
        console.print(f"[bold]Git:[/bold] {result.stdout.strip()}")
    except Exception:
        console.print("[bold]Git:[/bold] [red]Not found[/red]")

    # Check plugins
    console.print()
    console.print("[bold]Plugins:[/bold]")
    plugins = registry.get_plugins()
    for plugin in plugins:
        console.print(f"  ✓ {plugin.name} ({', '.join(plugin.supported_extensions)})")


@app.command("diff-driver", hidden=True)
def diff_driver(
    args: list[str] = typer.Argument(..., help="Git diff driver arguments"),
):
    """Internal: Git external diff driver interface.

    Git passes: path old-file old-hex old-mode new-file new-hex new-mode [rename-info]
    """
    try:
        old_file, new_file = parse_diff_driver_args(args)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Find plugin for this file
    plugin = registry.get_plugin_for_path(old_file)
    if plugin is None:
        console.print(f"[red]Error:[/red] No plugin found for: {old_file.suffix}")
        raise typer.Exit(1)

    # Run diff
    options = DiffOptions(output_format="terminal", color=True)
    result = plugin.diff(old_file, new_file, options)

    # Print terminal output
    console.print(result.terminal_output)


@app.command("extract-text", hidden=True)
def extract_text(
    file: Path = typer.Argument(..., help="File to extract text from"),
):
    """Internal: Extract text from a file (used as git textconv)."""
    plugin = registry.get_plugin_for_path(file)

    if plugin is None:
        console.print(f"[red]Error:[/red] No plugin found for: {file.suffix}")
        raise typer.Exit(1)

    # Check if plugin has extract_text method
    if hasattr(plugin, "extract_text"):
        text = plugin.extract_text(file)
        console.print(text)
    else:
        console.print(f"[yellow]Warning:[/yellow] {plugin.name} does not support text extraction.")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
