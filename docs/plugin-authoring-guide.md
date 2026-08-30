# Plugin Authoring Guide

**Add support for a new file format in 30 minutes.**

This guide walks you through creating a polydiff plugin for any file format. By the end, you'll have a working plugin that integrates seamlessly with polydiff and git.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Plugin Interface](#plugin-interface)
- [Implementation Steps](#implementation-steps)
- [Registration](#registration)
- [Testing](#testing)
- [Publishing](#publishing)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

polydiff uses a plugin architecture based on Python entry points. Plugins are:

- **Self-contained**: Each plugin is a Python class that implements the `DiffPlugin` interface
- **Discoverable**: Plugins are found automatically via entry points in `pyproject.toml`
- **Independent**: Plugins can be distributed as separate packages

## Quick Start

### 1. Create the Plugin Class

Create a new file in `src/polydiff/plugins/` (or in your own package):

```python
# src/polydiff/plugins/cad_diff.py

from pathlib import Path
from polydiff.core.plugin_base import DiffPlugin, DiffResult, DiffOptions

class CadDiffPlugin(DiffPlugin):
    """Plugin for diffing CAD files."""

    name = "polydiff-cad"
    supported_extensions = [".dwg", ".dxf"]

    def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
        """Compare two CAD files."""
        # Your implementation here
        similarity = 0.95  # Compute this
        changed = similarity < 1.0

        return DiffResult(
            similarity=similarity,
            changed=changed,
            summary=f"{similarity:.1%} similar",
            terminal_output=self._build_terminal_output(similarity, changed),
            json_output={
                "similarity": similarity,
                "changed": changed,
            },
        )

    def _build_terminal_output(self, similarity: float, changed: bool) -> str:
        """Build Rich-formatted terminal output."""
        if not changed:
            return "[green]✓ Files are identical[/green]"
        return f"[yellow]~ {similarity:.1%} similar[/yellow]"
```

### 2. Register the Plugin

Add to your `pyproject.toml`:

```toml
[project.entry-points."polydiff/plugins"]
cad = "polydiff.plugins.cad_diff:CadDiffPlugin"
```

### 3. Test It

```bash
# Install your plugin
pip install -e .

# Verify it's discovered
polydiff plugins list

# Test it
polydiff diff old.dxf new.dxf
```

## Plugin Interface

### DiffPlugin Base Class

All plugins must inherit from `DiffPlugin` and implement:

```python
class DiffPlugin(ABC):
    """Base class every format plugin must implement."""

    name: str                            # e.g. "polydiff-cad"
    supported_extensions: list[str]      # e.g. [".dwg", ".dxf"]

    @abstractmethod
    def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
        """Compare two files of the same format and return a DiffResult."""
        ...

    def supports(self, path: Path) -> bool:
        """Check if this plugin supports the given file."""
        return path.suffix.lower() in self.supported_extensions
```

### DiffOptions

Controls diff behavior:

```python
@dataclass
class DiffOptions:
    output_format: str = "terminal"      # "terminal" | "html" | "json" | "image"
    output_path: Optional[Path] = None   # Where to save output (for html/image)
    context_lines: int = 3               # For text diffs
    color: bool = True                   # Enable colored output
```

### DiffResult

The result of a diff operation:

```python
@dataclass
class DiffResult:
    similarity: float                    # 0.0 (different) to 1.0 (identical)
    changed: bool                        # True if similarity < 1.0
    summary: str                         # One-line human-readable summary
    terminal_output: str                 # Rich-markup-formatted string
    html_output: Optional[str] = None    # HTML fragment for reports
    json_output: dict = field(default_factory=dict)  # Structured data
    artifact_path: Optional[Path] = None # Path to generated artifact
```

## Implementation Steps

### Step 1: Analyze the Format

Before coding, understand:

1. **What can change?** (visual, structural, metadata, content)
2. **What libraries exist?** (check PyPI, GitHub)
3. **What's a useful diff?** (summary, detailed, visual)

### Step 2: Implement the diff() Method

```python
def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
    # 1. Load both files
    try:
        data_a = self._load(path_a)
        data_b = self._load(path_b)
    except Exception as e:
        return DiffResult(
            similarity=0.0,
            changed=True,
            summary=f"Error: {e}",
            terminal_output=f"[red]Error:[/red] {e}",
        )

    # 2. Compare them
    similarity = self._compute_similarity(data_a, data_b)
    changes = self._find_changes(data_a, data_b)

    # 3. Build output
    changed = similarity < 1.0

    return DiffResult(
        similarity=similarity,
        changed=changed,
        summary=self._build_summary(changes),
        terminal_output=self._build_terminal(changes),
        html_output=self._build_html(changes) if options.output_format == "html" else None,
        json_output=self._build_json(changes),
    )
```

### Step 3: Build Output Formats

#### Terminal Output (Required)

Use Rich markup for colored output:

```python
def _build_terminal(self, changes: list) -> str:
    lines = []
    if not changes:
        lines.append("[green]✓ Files are identical[/green]")
    else:
        lines.append(f"[yellow]{len(changes)} change(s) found[/yellow]")
        for change in changes[:10]:  # Limit output
            lines.append(f"  • {change}")
    return "\n".join(lines)
```

#### HTML Output (Optional)

Return an HTML fragment (not a full page):

```python
def _build_html(self, changes: list) -> str:
    html = ["<h2>Diff Report</h2>"]
    if changes:
        html.append("<ul>")
        for change in changes:
            html.append(f"<li>{change}</li>")
        html.append("</ul>")
    else:
        html.append("<p>No changes found.</p>")
    return "\n".join(html)
```

#### JSON Output (Recommended)

Provide structured data for programmatic use:

```python
def _build_json(self, changes: list) -> dict:
    return {
        "changes_count": len(changes),
        "changes": changes,
    }
```

## Registration

### Option 1: Built-in Plugin

Add to polydiff's `pyproject.toml`:

```toml
[project.entry-points."polydiff/plugins"]
your_format = "polydiff.plugins.your_diff:YourDiffPlugin"
```

### Option 2: Separate Package

Create a new package:

```
polydiff-plugin-cad/
├── pyproject.toml
├── src/
│   └── polydiff_plugin_cad/
│       ├── __init__.py
│       └── cad_diff.py
└── tests/
```

In `pyproject.toml`:

```toml
[project]
name = "polydiff-plugin-cad"
version = "0.1.0"
dependencies = [
    "polydiff>=0.1.0",
    "ezdxf>=0.18",  # Example CAD library
]

[project.entry-points."polydiff/plugins"]
cad = "polydiff_plugin_cad.cad_diff:CadDiffPlugin"
```

## Testing

### Test Structure

```python
# tests/test_cad_diff.py

from pathlib import Path
import pytest
from polydiff.core.plugin_base import DiffOptions
from polydiff.plugins.cad_diff import CadDiffPlugin

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "cad"

@pytest.fixture
def plugin():
    return CadDiffPlugin()

@pytest.fixture
def options():
    return DiffOptions(output_format="terminal", color=False)

class TestCadDiffPlugin:
    def test_identical_files(self, plugin, options):
        result = plugin.diff(
            FIXTURES_DIR / "identical_a.dxf",
            FIXTURES_DIR / "identical_b.dxf",
            options,
        )
        assert result.similarity == pytest.approx(1.0, abs=0.01)
        assert result.changed is False

    def test_changed_files(self, plugin, options):
        result = plugin.diff(
            FIXTURES_DIR / "original.dxf",
            FIXTURES_DIR / "modified.dxf",
            options,
        )
        assert result.changed is True
        assert result.similarity < 1.0

    def test_supports_extension(self, plugin):
        assert plugin.supports(Path("test.dxf"))
        assert plugin.supports(Path("test.dwg"))
        assert not plugin.supports(Path("test.txt"))
```

### Test Fixtures

Create test files in `tests/fixtures/`:

```
tests/fixtures/
└── cad/
    ├── identical_a.dxf
    ├── identical_b.dxf
    ├── original.dxf
    └── modified.dxf
```

## Publishing

### 1. Prepare Your Package

```bash
# Update version
# pyproject.toml: version = "0.1.0"

# Add README
# README.md

# Add LICENSE
# LICENSE (MIT recommended)
```

### 2. Build and Upload

```bash
# Install build tools
pip install build twine

# Build
python -m build

# Check
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

### 3. Announce

- Open a PR to add your plugin to polydiff's README
- Share on relevant communities

## Examples

### Image Plugin (Built-in)

See `src/polydiff/plugins/image_diff.py` for a complete example including:
- SSIM computation
- Pixel diff visualization
- HTML output with embedded images

### PDF Plugin (Built-in)

See `src/polydiff/plugins/pdf_diff.py` for:
- Page-by-page comparison
- Text extraction
- Visual and text diff combination

### XLSX Plugin (Built-in)

See `src/polydiff/plugins/xlsx_diff.py` for:
- Cell-level diffing
- Formula comparison
- Sheet-level changes

## Best Practices

### 1. Handle Errors Gracefully

```python
def diff(self, path_a, path_b, options):
    try:
        data_a = self._load(path_a)
    except Exception as e:
        return DiffResult(
            similarity=0.0,
            changed=True,
            summary=f"Error loading {path_a.name}: {e}",
            terminal_output=f"[red]Error:[/red] {e}",
        )
```

### 2. Provide Useful Summaries

```python
# Bad
summary = "Files differ"

# Good
summary = "3 layers changed, 2 objects added, 1 object removed"
```

### 3. Limit Output Size

```python
# Don't dump 10,000 changes to terminal
for change in changes[:50]:
    lines.append(f"  • {change}")
if len(changes) > 50:
    lines.append(f"  [dim]... and {len(changes) - 50} more[/dim]")
```

### 4. Use Similarity Score Meaningfully

```python
# 1.0 = identical
# 0.99+ = trivial differences (whitespace, timestamps)
# 0.9-0.99 = minor changes
# 0.5-0.9 = significant changes
# 0.0-0.5 = major changes or completely different
```

### 5. Support Multiple Output Formats

Always implement `terminal_output`. Consider implementing:
- `html_output` for rich reports
- `json_output` for programmatic use
- `artifact_path` for visual diffs

## Getting Help

- Open an issue on GitHub
- Check existing plugins for examples
- Read the source code (it's well-documented!)

## License

Plugins should use the MIT license to match polydiff's license.

---

**Happy plugin writing!** 🎉

Your plugin helps make polydiff more useful for everyone. Thank you for contributing!
