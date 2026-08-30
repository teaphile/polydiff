"""Delegation layer for tools that already handle certain formats well."""

import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class DelegatedTool:
    """Configuration for a tool that polydiff delegates to."""

    name: str
    check_cmd: list[str]
    install_hint: str
    git_setup_cmd: Optional[list[str]] = None
    extensions: list[str] = None

    def __post_init__(self):
        if self.extensions is None:
            self.extensions = []


# Tools that polydiff delegates to rather than reimplementing
DELEGATIONS: dict[str, DelegatedTool] = {
    ".ipynb": DelegatedTool(
        name="nbdime",
        check_cmd=["nbdiff", "--version"],
        install_hint="pip install nbdime",
        git_setup_cmd=["git-nbdiffdriver", "config", "--enable", "--global"],
        extensions=[".ipynb"],
    ),
    ".csv": DelegatedTool(
        name="daff",
        check_cmd=["daff", "version"],
        install_hint="pip install daff",
        extensions=[".csv", ".tsv"],
    ),
    ".tsv": DelegatedTool(
        name="daff",
        check_cmd=["daff", "version"],
        install_hint="pip install daff",
        extensions=[".csv", ".tsv"],
    ),
}


def is_tool_available(tool: DelegatedTool) -> bool:
    """Check if a delegated tool is installed and available."""
    return shutil.which(tool.check_cmd[0]) is not None


def get_available_delegations() -> dict[str, DelegatedTool]:
    """Get all delegated tools that are currently available."""
    available = {}
    for ext, tool in DELEGATIONS.items():
        if is_tool_available(tool) and tool.name not in [t.name for t in available.values()]:
            available[ext] = tool
    return available


def get_missing_delegations() -> dict[str, DelegatedTool]:
    """Get all delegated tools that are NOT currently available."""
    missing = {}
    seen_names = set()
    for ext, tool in DELEGATIONS.items():
        if not is_tool_available(tool) and tool.name not in seen_names:
            missing[ext] = tool
            seen_names.add(tool.name)
    return missing


def get_delegated_tool(extension: str) -> Optional[DelegatedTool]:
    """Get the delegated tool for a given extension, if any."""
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return DELEGATIONS.get(ext)
