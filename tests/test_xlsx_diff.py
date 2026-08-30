"""Tests for the XLSX diff plugin."""

from pathlib import Path

import pytest

from polydiff.core.plugin_base import DiffOptions
from polydiff.plugins.xlsx_diff import XlsxDiffPlugin

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "xlsx"


@pytest.fixture
def plugin():
    return XlsxDiffPlugin()


@pytest.fixture
def options():
    return DiffOptions(output_format="terminal", color=False)


class TestXlsxDiffPlugin:
    def test_identical_workbooks(self, plugin, options):
        """Test that identical workbooks produce similarity of 1.0."""
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.xlsx",
            FIXTURES_DIR / "identical_b.xlsx",
            options,
        )

        assert result.similarity == pytest.approx(1.0, abs=0.01)
        assert result.changed is False

    def test_cell_change(self, plugin, options):
        """Test that cell value changes are detected."""
        result = plugin.diff(
            FIXTURES_DIR / "cell_change_a.xlsx",
            FIXTURES_DIR / "cell_change_b.xlsx",
            options,
        )

        assert result.changed is True
        assert result.similarity < 1.0
        assert "cell" in result.summary.lower() or "changed" in result.summary.lower()

    def test_row_added(self, plugin, options):
        """Test that added rows are detected."""
        result = plugin.diff(
            FIXTURES_DIR / "row_added_a.xlsx",
            FIXTURES_DIR / "row_added_b.xlsx",
            options,
        )

        assert result.changed is True

    def test_sheet_added(self, plugin, options):
        """Test that added sheets are detected."""
        result = plugin.diff(
            FIXTURES_DIR / "sheet_added_a.xlsx",
            FIXTURES_DIR / "sheet_added_b.xlsx",
            options,
        )

        assert result.changed is True
        assert "sheet" in result.summary.lower()

    def test_formula_change(self, plugin, options):
        """Test that formula changes are detected."""
        result = plugin.diff(
            FIXTURES_DIR / "formula_change_a.xlsx",
            FIXTURES_DIR / "formula_change_b.xlsx",
            options,
        )

        assert result.changed is True

    def test_supports_extension(self, plugin):
        """Test that plugin supports correct extensions."""
        assert plugin.supports(Path("test.xlsx"))
        assert plugin.supports(Path("test.xlsm"))
        assert not plugin.supports(Path("test.xls"))
        assert not plugin.supports(Path("test.csv"))

    def test_json_output(self, plugin):
        """Test JSON output format."""
        options = DiffOptions(output_format="json")
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.xlsx",
            FIXTURES_DIR / "identical_b.xlsx",
            options,
        )

        assert "similarity" in result.json_output
        assert "changed" in result.json_output
        assert "sheets_a" in result.json_output
        assert "sheets_b" in result.json_output
        assert "sheets" in result.json_output

    def test_terminal_output_contains_sheet_info(self, plugin, options):
        """Test that terminal output contains sheet information."""
        result = plugin.diff(
            FIXTURES_DIR / "cell_change_a.xlsx",
            FIXTURES_DIR / "cell_change_b.xlsx",
            options,
        )

        assert "sheet" in result.terminal_output.lower() or "cell" in result.terminal_output.lower()
