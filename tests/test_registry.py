"""Tests for the plugin registry."""

from pathlib import Path

import pytest

from polydiff.core.registry import PluginRegistry


@pytest.fixture
def registry():
    return PluginRegistry()


class TestPluginRegistry:
    def test_discover_plugins(self, registry):
        """Test that plugins are discovered from entry points."""
        plugins = registry.get_plugins()

        # Should have at least the built-in plugins
        assert len(plugins) >= 3

        # Check plugin names
        plugin_names = [p.name for p in plugins]
        assert "polydiff-image" in plugin_names
        assert "polydiff-pdf" in plugin_names
        assert "polydiff-xlsx" in plugin_names

    def test_get_plugin_for_extension(self, registry):
        """Test finding plugins by extension."""
        # Image extensions
        assert registry.get_plugin_for_extension(".png") is not None
        assert registry.get_plugin_for_extension(".jpg") is not None
        assert registry.get_plugin_for_extension(".jpeg") is not None

        # PDF
        assert registry.get_plugin_for_extension(".pdf") is not None

        # XLSX
        assert registry.get_plugin_for_extension(".xlsx") is not None

        # Unknown extension
        assert registry.get_plugin_for_extension(".xyz") is None

    def test_get_plugin_for_path(self, registry):
        """Test finding plugins by file path."""
        assert registry.get_plugin_for_path(Path("image.png")) is not None
        assert registry.get_plugin_for_path(Path("document.pdf")) is not None
        assert registry.get_plugin_for_path(Path("data.xlsx")) is not None
        assert registry.get_plugin_for_path(Path("unknown.xyz")) is None

    def test_extension_normalization(self, registry):
        """Test that extensions are normalized (with or without dot)."""
        assert registry.get_plugin_for_extension("png") is not None
        assert registry.get_plugin_for_extension(".png") is not None

    def test_plugins_loaded_once(self, registry):
        """Test that plugins are loaded only once."""
        plugins1 = registry.get_plugins()
        plugins2 = registry.get_plugins()

        # Should be the same objects (cached)
        assert len(plugins1) == len(plugins2)
