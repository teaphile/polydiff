"""XLSX diff plugin for polydiff."""

from pathlib import Path
from typing import Any, Optional

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from ..core.plugin_base import DiffOptions, DiffPlugin, DiffResult


class XlsxDiffPlugin(DiffPlugin):
    """Plugin for diffing Excel XLSX files."""

    name = "polydiff-xlsx"
    supported_extensions = [".xlsx", ".xlsm"]

    def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
        """Compare two XLSX files and return a DiffResult."""
        try:
            # Load workbooks - both with formulas and with computed values
            wb_a_formulas = load_workbook(str(path_a), data_only=False)
            wb_a_values = load_workbook(str(path_a), data_only=True)
            wb_b_formulas = load_workbook(str(path_b), data_only=False)
            wb_b_values = load_workbook(str(path_b), data_only=True)
        except Exception as e:
            return DiffResult(
                similarity=0.0,
                changed=True,
                summary=f"Error opening workbooks: {e}",
                terminal_output=f"[red]Error:[/red] {e}",
            )

        # Get sheet names
        sheets_a = set(wb_a_formulas.sheetnames)
        sheets_b = set(wb_b_formulas.sheetnames)

        sheets_added = sorted(sheets_b - sheets_a)
        sheets_removed = sorted(sheets_a - sheets_b)
        common_sheets = sorted(sheets_a & sheets_b)

        # Diff each common sheet
        sheet_diffs = {}
        total_changes = 0
        total_cells = 0

        for sheet_name in common_sheets:
            sheet_diff = self._diff_sheet(
                wb_a_formulas[sheet_name],
                wb_a_values[sheet_name],
                wb_b_formulas[sheet_name],
                wb_b_values[sheet_name],
            )
            sheet_diffs[sheet_name] = sheet_diff
            total_changes += len(sheet_diff["changes"])
            total_cells += sheet_diff["total_cells"]

        # Compute similarity
        if total_cells > 0:
            similarity = 1.0 - (total_changes / total_cells)
        else:
            similarity = 1.0 if not (sheets_added or sheets_removed) else 0.0

        # Penalize for sheet differences
        total_sheets = max(len(sheets_a), len(sheets_b))
        if total_sheets > 0:
            sheet_similarity = len(common_sheets) / total_sheets
            similarity = (similarity + sheet_similarity) / 2

        # Check for any changes
        has_structural_changes = any(
            diff["rows_added"] or diff["rows_removed"] or diff["columns_added"] or diff["columns_removed"]
            for diff in sheet_diffs.values()
        )
        changed = similarity < 0.99 or bool(sheets_added) or bool(sheets_removed) or has_structural_changes

        # Build summary
        summary_parts = []
        if not changed:
            summary_parts.append("Workbooks are identical")
        else:
            summary_parts.append(f"{similarity:.1%} similar")
            if sheets_added:
                summary_parts.append(f"{len(sheets_added)} sheet(s) added")
            if sheets_removed:
                summary_parts.append(f"{len(sheets_removed)} sheet(s) removed")
            if total_changes:
                summary_parts.append(f"{total_changes} cell(s) changed")

        summary = ", ".join(summary_parts)

        # Build terminal output
        terminal_output = self._build_terminal_output(
            sheet_diffs, sheets_added, sheets_removed, common_sheets, options.color
        )

        # Build HTML output
        html_output = None
        if options.output_format == "html":
            html_output = self._build_html_output(
                sheet_diffs, sheets_added, sheets_removed, similarity, summary
            )

        # Build JSON output
        json_output = {
            "similarity": similarity,
            "changed": changed,
            "sheets_a": sorted(sheets_a),
            "sheets_b": sorted(sheets_b),
            "sheets_added": sheets_added,
            "sheets_removed": sheets_removed,
            "sheets": {
                name: {
                    "changes_count": len(diff["changes"]),
                    "rows_added": diff["rows_added"],
                    "rows_removed": diff["rows_removed"],
                    "columns_added": diff["columns_added"],
                    "columns_removed": diff["columns_removed"],
                }
                for name, diff in sheet_diffs.items()
            },
        }

        # Close workbooks
        wb_a_formulas.close()
        wb_a_values.close()
        wb_b_formulas.close()
        wb_b_values.close()

        return DiffResult(
            similarity=similarity,
            changed=changed,
            summary=summary,
            terminal_output=terminal_output,
            html_output=html_output,
            json_output=json_output,
        )

    def _diff_sheet(
        self,
        sheet_a_formulas,
        sheet_a_values,
        sheet_b_formulas,
        sheet_b_values,
    ) -> dict:
        """Diff a single sheet between two workbooks."""
        # Get dimensions
        max_row_a = sheet_a_formulas.max_row or 0
        max_col_a = sheet_a_formulas.max_column or 0
        max_row_b = sheet_b_formulas.max_row or 0
        max_col_b = sheet_b_formulas.max_column or 0

        max_row = max(max_row_a, max_row_b)
        max_col = max(max_col_a, max_col_b)

        total_cells = max_row * max_col

        changes = []
        rows_added = []
        rows_removed = []
        columns_added = []
        columns_removed = []

        # Detect row additions/removals
        if max_row_b > max_row_a:
            rows_added = list(range(max_row_a + 1, max_row_b + 1))
        elif max_row_a > max_row_b:
            rows_removed = list(range(max_row_b + 1, max_row_a + 1))

        # Detect column additions/removals
        if max_col_b > max_col_a:
            columns_added = [
                get_column_letter(c) for c in range(max_col_a + 1, max_col_b + 1)
            ]
        elif max_col_a > max_col_b:
            columns_removed = [
                get_column_letter(c) for c in range(max_col_b + 1, max_col_a + 1)
            ]

        # Compare cells
        for row in range(1, min(max_row_a, max_row_b) + 1):
            for col in range(1, min(max_col_a, max_col_b) + 1):
                cell_a_formula = sheet_a_formulas.cell(row=row, column=col)
                cell_b_formula = sheet_b_formulas.cell(row=row, column=col)
                cell_a_value = sheet_a_values.cell(row=row, column=col)
                cell_b_value = sheet_b_values.cell(row=row, column=col)

                formula_a = cell_a_formula.value
                formula_b = cell_b_formula.value
                value_a = cell_a_value.value
                value_b = cell_b_value.value

                # Check for changes
                if formula_a != formula_b or value_a != value_b:
                    cell_ref = f"{get_column_letter(col)}{row}"

                    change_type = []
                    if formula_a != formula_b:
                        change_type.append("formula")
                    if value_a != value_b:
                        change_type.append("value")

                    changes.append({
                        "cell": cell_ref,
                        "old_formula": formula_a,
                        "new_formula": formula_b,
                        "old_value": value_a,
                        "new_value": value_b,
                        "type": ", ".join(change_type),
                    })

        return {
            "changes": changes,
            "rows_added": rows_added,
            "rows_removed": rows_removed,
            "columns_added": columns_added,
            "columns_removed": columns_removed,
            "total_cells": total_cells,
            "max_row_a": max_row_a,
            "max_col_a": max_col_a,
            "max_row_b": max_row_b,
            "max_col_b": max_col_b,
        }

    def _build_terminal_output(
        self,
        sheet_diffs: dict,
        sheets_added: list,
        sheets_removed: list,
        common_sheets: list,
        color: bool,
    ) -> str:
        """Build Rich-formatted terminal output."""
        lines = []

        # Sheet-level changes
        if sheets_added:
            lines.append(f"[green]Sheets added:[/green] {', '.join(sheets_added)}")
        if sheets_removed:
            lines.append(f"[red]Sheets removed:[/red] {', '.join(sheets_removed)}")

        # Per-sheet details
        for sheet_name in common_sheets:
            diff = sheet_diffs[sheet_name]
            changes = diff["changes"]

            if not changes and not diff["rows_added"] and not diff["rows_removed"]:
                continue

            lines.append(f"\n[bold]Sheet: {sheet_name}[/bold]")

            if diff["rows_added"]:
                lines.append(f"  [green]Rows added:[/green] {len(diff['rows_added'])}")
            if diff["rows_removed"]:
                lines.append(f"  [red]Rows removed:[/red] {len(diff['rows_removed'])}")
            if diff["columns_added"]:
                lines.append(f"  [green]Columns added:[/green] {', '.join(diff['columns_added'])}")
            if diff["columns_removed"]:
                lines.append(f"  [red]Columns removed:[/red] {', '.join(diff['columns_removed'])}")

            if changes:
                lines.append(f"  [yellow]Cells changed:[/yellow] {len(changes)}")

                # Show changes in a table (limit to 200 rows for readability)
                if len(changes) <= 200:
                    lines.append("")
                    lines.append(f"  {'Cell':<10} {'Old Value':<20} {'New Value':<20} {'Type':<10}")
                    lines.append("  " + "-" * 60)

                    for change in changes[:50]:  # Show first 50
                        old_val = str(change["old_value"])[:18] if change["old_value"] is not None else ""
                        new_val = str(change["new_value"])[:18] if change["new_value"] is not None else ""
                        lines.append(
                            f"  {change['cell']:<10} {old_val:<20} {new_val:<20} {change['type']:<10}"
                        )

                    if len(changes) > 50:
                        lines.append(f"  [dim]... and {len(changes) - 50} more changes[/dim]")
                else:
                    lines.append(f"  [dim]({len(changes)} changes - too many to display inline)[/dim]")

        if not any(sheet_diffs[s]["changes"] for s in common_sheets) and not sheets_added and not sheets_removed:
            lines.append("[green]✓ Workbooks are identical[/green]")

        return "\n".join(lines)

    def _build_html_output(
        self,
        sheet_diffs: dict,
        sheets_added: list,
        sheets_removed: list,
        similarity: float,
        summary: str,
    ) -> str:
        """Build HTML output."""
        html_parts = [
            '<h2>Excel Diff Report</h2>',
            f'<div class="summary {"identical" if similarity >= 0.99 else "minor-changes" if similarity > 0.8 else "major-changes"}">',
            f'    <strong>Overall Similarity:</strong> {similarity:.1%} — {summary}',
            '</div>',
        ]

        if sheets_added:
            html_parts.append(f'<div class="summary added"><strong>Sheets added:</strong> {", ".join(sheets_added)}</div>')
        if sheets_removed:
            html_parts.append(f'<div class="summary removed"><strong>Sheets removed:</strong> {", ".join(sheets_removed)}</div>')

        # Per-sheet tables
        for sheet_name, diff in sheet_diffs.items():
            changes = diff["changes"]
            if not changes and not diff["rows_added"] and not diff["rows_removed"]:
                continue

            html_parts.extend([
                f'<h3>Sheet: {sheet_name}</h3>',
            ])

            if diff["rows_added"]:
                html_parts.append(f'<div class="summary added"><strong>Rows added:</strong> {len(diff["rows_added"])}</div>')
            if diff["rows_removed"]:
                html_parts.append(f'<div class="summary removed"><strong>Rows removed:</strong> {len(diff["rows_removed"])}</div>')
            if diff["columns_added"]:
                html_parts.append(f'<div class="summary added"><strong>Columns added:</strong> {", ".join(diff["columns_added"])}</div>')
            if diff["columns_removed"]:
                html_parts.append(f'<div class="summary removed"><strong>Columns removed:</strong> {", ".join(diff["columns_removed"])}</div>')

            if changes:
                html_parts.extend([
                    '<table>',
                    '    <thead>',
                    '        <tr>',
                    '            <th>Cell</th>',
                    '            <th>Old Value</th>',
                    '            <th>New Value</th>',
                    '            <th>Type</th>',
                    '        </tr>',
                    '    </thead>',
                    '    <tbody>',
                ])

                for change in changes[:100]:  # Limit to 100 in HTML
                    old_val = str(change["old_value"]) if change["old_value"] is not None else ""
                    new_val = str(change["new_value"]) if change["new_value"] is not None else ""
                    html_parts.extend([
                        '        <tr class="changed">',
                        f'            <td>{change["cell"]}</td>',
                        f'            <td>{old_val}</td>',
                        f'            <td>{new_val}</td>',
                        f'            <td>{change["type"]}</td>',
                        '        </tr>',
                    ])

                html_parts.extend([
                    '    </tbody>',
                    '</table>',
                ])

                if len(changes) > 100:
                    html_parts.append(f'<p><em>... and {len(changes) - 100} more changes</em></p>')
            else:
                html_parts.append('<p><em>No cell changes in this sheet.</em></p>')

        return "\n".join(html_parts)
