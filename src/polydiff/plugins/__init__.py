"""Built-in polydiff plugins."""

from .image_diff import ImageDiffPlugin
from .pdf_diff import PdfDiffPlugin
from .xlsx_diff import XlsxDiffPlugin

__all__ = ["ImageDiffPlugin", "PdfDiffPlugin", "XlsxDiffPlugin"]
