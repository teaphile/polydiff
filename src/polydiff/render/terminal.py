"""Terminal rendering utilities using Rich."""

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..core.plugin_base import DiffResult


def render_terminal_summary(result: DiffResult, color: bool = True) -> None:
    """Render a diff result summary to the terminal."""
    console = Console(no_color=not color)

    # Similarity indicator
    if result.similarity >= 0.99:
        status = Text("✓ Identical", style="green")
    elif result.similarity >= 0.8:
        status = Text(f"~ {result.similarity:.1%} similar", style="yellow")
    else:
        status = Text(f"✗ {result.similarity:.1%} similar", style="red bold")

    console.print(f"[bold]Diff Result:[/bold] {status}")
    console.print(f"[dim]{result.summary}[/dim]")

    if result.terminal_output:
        console.print()
        console.print(result.terminal_output)


def render_diff_table(
    title: str,
    rows: list[dict],
    columns: list[str],
    color: bool = True,
) -> str:
    """Render a table of diff results.

    Args:
        title: Table title
        rows: List of row dicts with column values
        columns: Column names to display
        color: Whether to use color

    Returns:
        Rendered table as string
    """
    console = Console(no_color=not color, record=True, width=120)

    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in columns:
        table.add_column(col)

    for row in rows:
        values = [str(row.get(col, "")) for col in columns]
        table.add_row(*values)

    console.print(table)
    return console.export_text()
