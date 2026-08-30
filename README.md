# polydiff

**One `git config`. Every file type gets a real diff.**

Git is excellent at diffing text/code, and useless at diffing anything else. Run `git diff` on a changed PNG, PDF, or XLSX file and you get:

```
Binary files a/logo.png and b/logo.png differ
```

That's it. No visual, no summary, nothing actionable.

`polydiff` fixes that in one command.

## Quick Start

```bash
pip install polydiff

# In your git repo:
polydiff install

# Now git diff works on binary files:
git diff  # Shows real visual/cell/text diffs for images, PDFs, Excel files

# Or use standalone (no git required):
polydiff diff old.png new.png
polydiff diff old.pdf new.pdf
polydiff diff old.xlsx new.xlsx
```

## What It Does

| Format | What you get |
|--------|--------------|
| **Images** (PNG, JPG, WebP, BMP) | Visual side-by-side diff with changed regions highlighted, similarity score |
| **PDFs** | Per-page visual diff + text-layer diff, page additions/removals detected |
| **XLSX** | Cell-level changes, rows/columns added/removed, formula changes, sheet changes |

## Delegation to Existing Tools

`polydiff` doesn't reinvent wheels that already roll well:

- **Jupyter notebooks** (`.ipynb`) → delegates to [nbdime](https://github.com/jupyter/nbdime)
- **CSV/TSV** → delegates to [daff](https://github.com/paulfitz/daff)

When you run `polydiff install`, it detects these tools and wires them in automatically.

## Plugin System

Support new formats by installing plugins:

```bash
pip install polydiff-plugin-cad  # hypothetical community plugin
```

Or [write your own plugin](docs/plugin-authoring-guide.md) in 30 minutes.

## Commands

| Command | Purpose |
|---------|---------|
| `polydiff diff <a> <b>` | Compare two files directly |
| `polydiff install` | Auto-configure git integration |
| `polydiff plugins list` | Show installed plugins |
| `polydiff doctor` | Check environment health |

## License

MIT — free for personal and commercial use.
