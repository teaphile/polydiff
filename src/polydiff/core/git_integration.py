"""Git integration for polydiff — .gitattributes and git config management."""

import subprocess
from pathlib import Path
from typing import Optional

# Mapping of file extensions to polydiff driver names
DRIVER_MAPPING = {
    # Images
    ".png": "polydiff-image",
    ".jpg": "polydiff-image",
    ".jpeg": "polydiff-image",
    ".webp": "polydiff-image",
    ".bmp": "polydiff-image",
    ".gif": "polydiff-image",
    # PDFs
    ".pdf": "polydiff-pdf",
    # Excel
    ".xlsx": "polydiff-xlsx",
    ".xlsm": "polydiff-xlsx",
}

GITATTRIBUTES_HEADER = "# added by polydiff — do not edit this block manually"


def get_git_root(path: Optional[Path] = None) -> Optional[Path]:
    """Find the root of the git repository containing the given path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path or Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def write_gitattributes(
    repo_root: Path,
    extensions: Optional[list[str]] = None,
    dry_run: bool = False,
) -> list[str]:
    """Write .gitattributes entries for polydiff drivers.

    Args:
        repo_root: Path to the git repository root
        extensions: List of extensions to configure (None = all)
        dry_run: If True, return what would be written without writing

    Returns:
        List of lines that were (or would be) added
    """
    gitattributes_path = repo_root / ".gitattributes"

    # Read existing content
    existing_content = ""
    if gitattributes_path.exists():
        existing_content = gitattributes_path.read_text()

    # Determine which extensions to configure
    if extensions is None:
        extensions = list(DRIVER_MAPPING.keys())

    # Build new entries
    new_lines = []
    for ext in sorted(set(extensions)):
        ext_lower = ext.lower()
        if ext_lower in DRIVER_MAPPING:
            driver = DRIVER_MAPPING[ext_lower]
            pattern = f"*{ext_lower}"
            line = f"{pattern}\tdiff={driver}"
            # Check if this pattern is already configured
            if pattern not in existing_content:
                new_lines.append(line)

    if not new_lines:
        return []

    if dry_run:
        return new_lines

    # Write the block
    block_lines = [GITATTRIBUTES_HEADER] + new_lines + [""]

    with open(gitattributes_path, "a") as f:
        if existing_content and not existing_content.endswith("\n"):
            f.write("\n")
        f.write("\n".join(block_lines))
        f.write("\n")

    return new_lines


def setup_git_config(
    scope: str = "local",
    repo_root: Optional[Path] = None,
    dry_run: bool = False,
) -> list[str]:
    """Configure git to use polydiff drivers.

    Args:
        scope: "local" (repo .git/config) or "global" (~/.gitconfig)
        repo_root: Required for local scope
        dry_run: If True, return commands that would be run

    Returns:
        List of commands that were (or would be) executed
    """
    config_scope = "--local" if scope == "local" else "--global"

    commands = []
    for driver_name in set(DRIVER_MAPPING.values()):
        cmd = [
            "git", "config", config_scope,
            f"diff.{driver_name}.command", "polydiff diff-driver",
        ]
        commands.append(cmd)

    if dry_run:
        return [" ".join(cmd) for cmd in commands]

    cwd = repo_root if scope == "local" else None
    executed = []
    for cmd in commands:
        subprocess.run(cmd, cwd=cwd, check=True)
        executed.append(" ".join(cmd))

    return executed


def parse_diff_driver_args(args: list[str]) -> tuple[Path, Path]:
    """Parse git's external diff driver arguments.

    Git passes: path old-file old-hex old-mode new-file new-hex new-mode [rename-info]

    Returns:
        Tuple of (old_file_path, new_file_path)
    """
    if len(args) < 7:
        raise ValueError(
            f"Expected at least 7 arguments from git diff driver, got {len(args)}"
        )

    # args[0] = path (relative to repo root)
    old_file = Path(args[1])
    new_file = Path(args[4])

    return old_file, new_file


def install_polydiff(
    scope: str = "local",
    repo_root: Optional[Path] = None,
    extensions: Optional[list[str]] = None,
) -> dict:
    """One-command installation: configure .gitattributes + git config.

    Args:
        scope: "local" or "global"
        repo_root: Repository root (auto-detected if None)
        extensions: Extensions to configure (None = all)

    Returns:
        Summary dict with what was configured
    """
    if repo_root is None:
        repo_root = get_git_root()
        if repo_root is None:
            raise RuntimeError("Not inside a git repository. Run 'git init' first.")

    # Write .gitattributes
    added_lines = write_gitattributes(repo_root, extensions)

    # Setup git config
    config_commands = setup_git_config(scope, repo_root if scope == "local" else None)

    return {
        "repo_root": str(repo_root),
        "scope": scope,
        "gitattributes_added": added_lines,
        "config_commands": config_commands,
    }
