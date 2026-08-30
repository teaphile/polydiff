# Contributing to polydiff

Thank you for your interest in contributing to polydiff! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Adding a New Format Plugin](#adding-a-new-format-plugin)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your changes
4. Make your changes
5. Push to your fork and submit a pull request

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/polydiff.git
cd polydiff

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests to verify setup
pytest tests/ -v
```

### Code Quality

We use `ruff` for linting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

## Making Changes

### Branch Naming

- `feature/description` for new features
- `fix/description` for bug fixes
- `docs/description` for documentation changes

### Commit Messages

Write clear, descriptive commit messages:

```
Add support for WebP image format

- Implement WebP loading in ImageDiffPlugin
- Add WebP to supported_extensions list
- Add test fixtures for WebP files
- Update documentation
```

### Testing

Always add tests for new functionality:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_image_diff.py -v

# Run with coverage
pytest tests/ --cov=polydiff --cov-report=html
```

## Adding a New Format Plugin

See the [Plugin Authoring Guide](docs/plugin-authoring-guide.md) for detailed instructions.

### Quick Summary

1. Create a new file in `src/polydiff/plugins/` (e.g., `cad_diff.py`)
2. Implement the `DiffPlugin` interface:

```python
from polydiff.core.plugin_base import DiffPlugin, DiffResult, DiffOptions

class CadDiffPlugin(DiffPlugin):
    name = "polydiff-cad"
    supported_extensions = [".dwg", ".dxf"]

    def diff(self, path_a, path_b, options: DiffOptions) -> DiffResult:
        # Your implementation here
        pass
```

3. Register the plugin in `pyproject.toml`:

```toml
[project.entry-points."polydiff/plugins"]
cad = "polydiff.plugins.cad_diff:CadDiffPlugin"
```

4. Add tests in `tests/test_cad_diff.py`
5. Update documentation

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add yourself to CONTRIBUTORS.md (if it exists)
4. Submit the pull request with a clear description

### PR Description Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing

- [ ] Tests added/updated
- [ ] All tests pass

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

## Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template.

## Requesting Features

Use the [New Format Plugin Request](.github/ISSUE_TEMPLATE/new_format_plugin.md) template for new format support.

## Questions?

Feel free to open an issue for any questions about contributing.

Thank you for helping make polydiff better! 🎉
