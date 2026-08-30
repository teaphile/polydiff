"""Plugin registry using entry points for discovery."""

from importlib.metadata import entry_points
from pathlib import Path
from typing import Optional

from .plugin_base import DiffPlugin


class PluginRegistry:
    """Discovers and manages polydiff plugins."""

    def __init__(self):
        self._plugins: list[DiffPlugin] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load plugins from entry points if not already loaded."""
        if self._loaded:
            return

        eps = entry_points(group="polydiff/plugins")
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugin = plugin_class()
                self._plugins.append(plugin)
            except Exception as e:
                # Log but don't fail - a broken plugin shouldn't break the tool
                print(f"Warning: Failed to load plugin '{ep.name}': {e}")

        self._loaded = True

    def get_plugins(self) -> list[DiffPlugin]:
        """Get all registered plugins."""
        self._ensure_loaded()
        return self._plugins.copy()

    def get_plugin_for_extension(self, extension: str) -> Optional[DiffPlugin]:
        """Find a plugin that supports the given file extension."""
        self._ensure_loaded()
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        for plugin in self._plugins:
            if ext in plugin.supported_extensions:
                return plugin
        return None

    def get_plugin_for_path(self, path: Path) -> Optional[DiffPlugin]:
        """Find a plugin that supports the given file path."""
        return self.get_plugin_for_extension(path.suffix)


# Global registry instance
registry = PluginRegistry()
