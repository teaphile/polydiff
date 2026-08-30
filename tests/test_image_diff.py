"""Tests for the image diff plugin."""

from pathlib import Path

import pytest

from polydiff.core.plugin_base import DiffOptions
from polydiff.plugins.image_diff import ImageDiffPlugin

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "images"


@pytest.fixture
def plugin():
    return ImageDiffPlugin()


@pytest.fixture
def options():
    return DiffOptions(output_format="terminal", color=False)


class TestImageDiffPlugin:
    def test_identical_images(self, plugin, options):
        """Test that identical images produce similarity of 1.0."""
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.png",
            FIXTURES_DIR / "identical_b.png",
            options,
        )

        assert result.similarity == pytest.approx(1.0, abs=0.01)
        assert result.changed is False
        assert "identical" in result.summary.lower()

    def test_minor_change(self, plugin, options):
        """Test that minor changes produce high similarity."""
        result = plugin.diff(
            FIXTURES_DIR / "minor_change_a.png",
            FIXTURES_DIR / "minor_change_b.png",
            options,
        )

        assert result.similarity > 0.5
        assert result.similarity < 1.0
        assert result.changed is True
        assert "similar" in result.summary.lower()

    def test_major_change(self, plugin, options):
        """Test that major changes produce low similarity."""
        result = plugin.diff(
            FIXTURES_DIR / "major_change_a.png",
            FIXTURES_DIR / "major_change_b.png",
            options,
        )

        assert result.similarity < 0.8
        assert result.changed is True

    def test_supports_extension(self, plugin):
        """Test that plugin supports correct extensions."""
        assert plugin.supports(Path("test.png"))
        assert plugin.supports(Path("test.jpg"))
        assert plugin.supports(Path("test.jpeg"))
        assert plugin.supports(Path("test.webp"))
        assert plugin.supports(Path("test.bmp"))
        assert plugin.supports(Path("test.gif"))
        assert not plugin.supports(Path("test.pdf"))
        assert not plugin.supports(Path("test.txt"))

    def test_json_output(self, plugin):
        """Test JSON output format."""
        options = DiffOptions(output_format="json")
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.png",
            FIXTURES_DIR / "identical_b.png",
            options,
        )

        assert "similarity" in result.json_output
        assert "changed" in result.json_output
        assert "dimensions_a" in result.json_output
        assert "dimensions_b" in result.json_output

    def test_terminal_output_contains_info(self, plugin, options):
        """Test that terminal output contains useful information."""
        result = plugin.diff(
            FIXTURES_DIR / "minor_change_a.png",
            FIXTURES_DIR / "minor_change_b.png",
            options,
        )

        assert "similar" in result.terminal_output.lower()
        assert "dimensions" in result.terminal_output.lower() or "200" in result.terminal_output
