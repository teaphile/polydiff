"""Tests for the PDF diff plugin."""

from pathlib import Path

import pytest

from polydiff.core.plugin_base import DiffOptions
from polydiff.plugins.pdf_diff import PdfDiffPlugin

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pdfs"


@pytest.fixture
def plugin():
    return PdfDiffPlugin()


@pytest.fixture
def options():
    return DiffOptions(output_format="terminal", color=False)


class TestPdfDiffPlugin:
    def test_identical_pdfs(self, plugin, options):
        """Test that identical PDFs produce similarity of 1.0."""
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.pdf",
            FIXTURES_DIR / "identical_b.pdf",
            options,
        )

        assert result.similarity == pytest.approx(1.0, abs=0.01)
        assert result.changed is False

    def test_text_change(self, plugin, options):
        """Test that text changes are detected."""
        result = plugin.diff(
            FIXTURES_DIR / "text_change_a.pdf",
            FIXTURES_DIR / "text_change_b.pdf",
            options,
        )

        assert result.changed is True
        assert result.similarity < 1.0
        # Check that text changes are mentioned
        assert "text" in result.summary.lower() or "changed" in result.summary.lower()

    def test_page_count_change(self, plugin, options):
        """Test that page count changes are detected."""
        result = plugin.diff(
            FIXTURES_DIR / "page_count_a.pdf",
            FIXTURES_DIR / "page_count_b.pdf",
            options,
        )

        assert result.changed is True
        assert "added" in result.summary.lower() or "page" in result.summary.lower()

    def test_supports_extension(self, plugin):
        """Test that plugin supports correct extensions."""
        assert plugin.supports(Path("test.pdf"))
        assert not plugin.supports(Path("test.png"))
        assert not plugin.supports(Path("test.txt"))

    def test_json_output(self, plugin):
        """Test JSON output format."""
        options = DiffOptions(output_format="json")
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.pdf",
            FIXTURES_DIR / "identical_b.pdf",
            options,
        )

        assert "similarity" in result.json_output
        assert "changed" in result.json_output
        assert "pages_a" in result.json_output
        assert "pages_b" in result.json_output
        assert "pages" in result.json_output

    def test_terminal_output_contains_page_info(self, plugin, options):
        """Test that terminal output contains page information."""
        result = plugin.diff(
            FIXTURES_DIR / "text_change_a.pdf",
            FIXTURES_DIR / "text_change_b.pdf",
            options,
        )

        assert "page" in result.terminal_output.lower()

    def test_extract_text(self, plugin):
        """Test text extraction for textconv."""
        text = plugin.extract_text(FIXTURES_DIR / "text_change_a.pdf")

        assert "Hello World" in text
        assert "test document" in text

    def test_html_output_escapes_text_diff(self, plugin):
        """Test that HTML output escapes embedded text diff content."""
        html = plugin._build_html_output(
            page_results=[
                {
                    "number": 1,
                    "visual_similarity": 0.95,
                    "text_changed": True,
                    "text_diff": "<script>alert('xss')</script>",
                }
            ],
            pages_added=[],
            pages_removed=[],
            similarity=0.95,
            summary="changed",
        )

        assert "<script>alert('xss')</script>" not in html
        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
