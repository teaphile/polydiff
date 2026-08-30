"""Base classes for polydiff plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DiffOptions:
    """Options for controlling diff behavior."""

    output_format: str = "terminal"  # "terminal" | "html" | "json" | "image"
    output_path: Optional[Path] = None
    context_lines: int = 3  # for text-layer diffs inside plugins (PDF text, etc.)
    color: bool = True


@dataclass
class DiffResult:
    """Result of comparing two files."""

    similarity: float  # 0.0 (completely different) to 1.0 (identical)
    changed: bool  # convenience flag, similarity < 1.0
    summary: str  # one-line human-readable summary
    terminal_output: str  # Rich-markup-formatted string, ready to print
    html_output: Optional[str] = None  # full HTML fragment for embedding in reports
    json_output: dict = field(default_factory=dict)  # structured, stable schema
    artifact_path: Optional[Path] = None  # e.g. path to a generated diff image


class DiffPlugin(ABC):
    """Base class every format plugin must implement."""

    name: str  # e.g. "polydiff-image"
    supported_extensions: list[str]  # e.g. [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

    @abstractmethod
    def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
        """Compare two files of the same format and return a DiffResult."""
        ...

    def supports(self, path: Path) -> bool:
        """Check if this plugin supports the given file extension."""
        return path.suffix.lower() in self.supported_extensions
