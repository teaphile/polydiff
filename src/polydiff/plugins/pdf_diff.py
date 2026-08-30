"""PDF diff plugin for polydiff."""

import difflib
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image

from ..core.plugin_base import DiffOptions, DiffPlugin, DiffResult
from ..utils.image_ops import compute_ssim, downsample_image


class PdfDiffPlugin(DiffPlugin):
    """Plugin for diffing PDF files."""

    name = "polydiff-pdf"
    supported_extensions = [".pdf"]

    def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
        """Compare two PDFs and return a DiffResult."""
        try:
            doc_a = fitz.open(str(path_a))
            doc_b = fitz.open(str(path_b))
        except Exception as e:
            return DiffResult(
                similarity=0.0,
                changed=True,
                summary=f"Error opening PDFs: {e}",
                terminal_output=f"[red]Error:[/red] {e}",
            )

        pages_a = len(doc_a)
        pages_b = len(doc_b)

        # Compare pages
        page_results = []
        min_pages = min(pages_a, pages_b)

        for page_num in range(min_pages):
            page_a = doc_a[page_num]
            page_b = doc_b[page_num]

            # Render pages to images for visual comparison
            pix_a = page_a.get_pixmap(dpi=150)
            pix_b = page_b.get_pixmap(dpi=150)

            img_a = Image.frombytes("RGB", [pix_a.width, pix_a.height], pix_a.samples)
            img_b = Image.frombytes("RGB", [pix_b.width, pix_b.height], pix_b.samples)

            # Compute visual similarity
            visual_similarity = compute_ssim(img_a, img_b)

            # Extract and compare text
            text_a = page_a.get_text()
            text_b = page_b.get_text()

            text_diff = None
            text_changed = False
            if text_a != text_b:
                text_changed = True
                # Generate unified diff
                diff_lines = difflib.unified_diff(
                    text_a.splitlines(keepends=True),
                    text_b.splitlines(keepends=True),
                    fromfile=f"page {page_num + 1} (old)",
                    tofile=f"page {page_num + 1} (new)",
                    n=options.context_lines,
                )
                text_diff = "".join(diff_lines)

            page_results.append({
                "number": page_num + 1,
                "visual_similarity": visual_similarity,
                "text_changed": text_changed,
                "text_diff": text_diff,
            })

        # Handle page count differences
        pages_added = list(range(min_pages + 1, pages_b + 1))
        pages_removed = list(range(min_pages + 1, pages_a + 1))

        # Compute overall similarity
        if page_results:
            avg_similarity = sum(p["visual_similarity"] for p in page_results) / len(page_results)
            # Penalize for page count differences
            if pages_added or pages_removed:
                total_pages = max(pages_a, pages_b)
                avg_similarity *= (min_pages / total_pages)
        else:
            avg_similarity = 0.0

        changed = avg_similarity < 0.99 or pages_added or pages_removed or any(
            p["text_changed"] for p in page_results
        )

        # Build summary
        summary_parts = []
        if not changed:
            summary_parts.append("PDFs are identical")
        else:
            summary_parts.append(f"{avg_similarity:.1%} similar overall")
            if pages_added:
                summary_parts.append(f"{len(pages_added)} page(s) added")
            if pages_removed:
                summary_parts.append(f"{len(pages_removed)} page(s) removed")
            text_changes = sum(1 for p in page_results if p["text_changed"])
            if text_changes:
                summary_parts.append(f"{text_changes} page(s) with text changes")

        summary = ", ".join(summary_parts)

        # Build terminal output
        terminal_output = self._build_terminal_output(
            page_results, pages_added, pages_removed, pages_a, pages_b, options.color
        )

        # Build HTML output
        html_output = None
        if options.output_format == "html":
            html_output = self._build_html_output(
                page_results, pages_added, pages_removed, avg_similarity, summary
            )

        # Build JSON output
        json_output = {
            "similarity": avg_similarity,
            "changed": changed,
            "pages_a": pages_a,
            "pages_b": pages_b,
            "pages_added": pages_added,
            "pages_removed": pages_removed,
            "pages": [
                {
                    "number": p["number"],
                    "visual_similarity": p["visual_similarity"],
                    "text_changed": p["text_changed"],
                }
                for p in page_results
            ],
        }

        doc_a.close()
        doc_b.close()

        return DiffResult(
            similarity=avg_similarity,
            changed=changed,
            summary=summary,
            terminal_output=terminal_output,
            html_output=html_output,
            json_output=json_output,
        )

    def _build_terminal_output(
        self,
        page_results: list,
        pages_added: list,
        pages_removed: list,
        pages_a: int,
        pages_b: int,
        color: bool,
    ) -> str:
        """Build Rich-formatted terminal output."""
        lines = []

        # Overall status
        if not page_results and not pages_added and not pages_removed:
            lines.append("[green]✓ PDFs are identical[/green]")
            return "\n".join(lines)

        # Page count info
        if pages_a != pages_b:
            lines.append(f"[dim]Pages:[/dim] {pages_a} → {pages_b}")

        if pages_added:
            lines.append(f"[green]Pages added:[/green] {', '.join(map(str, pages_added))}")
        if pages_removed:
            lines.append(f"[red]Pages removed:[/red] {', '.join(map(str, pages_removed))}")

        # Per-page table
        if page_results:
            lines.append("")
            lines.append("[bold]Page-by-Page Comparison:[/bold]")
            lines.append(f"{'Page':<8} {'Visual':<12} {'Text':<10}")
            lines.append("-" * 30)

            for page in page_results:
                visual_pct = f"{page['visual_similarity']:.1%}"
                text_status = "Changed" if page["text_changed"] else "Same"

                if page["visual_similarity"] >= 0.99:
                    visual_style = "green"
                elif page["visual_similarity"] >= 0.8:
                    visual_style = "yellow"
                else:
                    visual_style = "red"

                text_style = "yellow" if page["text_changed"] else "green"

                lines.append(
                    f"{page['number']:<8} "
                    f"[{visual_style}]{visual_pct:<12}[/{visual_style}] "
                    f"[{text_style}]{text_status:<10}[/{text_style}]"
                )

        # Show text diffs for changed pages
        text_changed_pages = [p for p in page_results if p["text_changed"]]
        if text_changed_pages:
            lines.append("")
            lines.append("[bold]Text Changes:[/bold]")
            for page in text_changed_pages[:3]:  # Show first 3
                lines.append(f"\n[dim]Page {page['number']}:[/dim]")
                lines.append(page["text_diff"])
            if len(text_changed_pages) > 3:
                lines.append(f"\n[dim]... and {len(text_changed_pages) - 3} more pages with text changes[/dim]")

        return "\n".join(lines)

    def _build_html_output(
        self,
        page_results: list,
        pages_added: list,
        pages_removed: list,
        similarity: float,
        summary: str,
    ) -> str:
        """Build HTML output."""
        html_parts = [
            '<h2>PDF Diff Report</h2>',
            f'<div class="summary {"identical" if similarity >= 0.99 else "minor-changes" if similarity > 0.8 else "major-changes"}">',
            f'    <strong>Overall Similarity:</strong> {similarity:.1%} — {summary}',
            '</div>',
        ]

        if pages_added:
            html_parts.append(f'<div class="summary added"><strong>Pages added:</strong> {", ".join(map(str, pages_added))}</div>')
        if pages_removed:
            html_parts.append(f'<div class="summary removed"><strong>Pages removed:</strong> {", ".join(map(str, pages_removed))}</div>')

        # Page table
        html_parts.extend([
            '<h3>Page-by-Page Comparison</h3>',
            '<table>',
            '    <thead>',
            '        <tr>',
            '            <th>Page</th>',
            '            <th>Visual Similarity</th>',
            '            <th>Text Changed</th>',
            '            <th>Details</th>',
            '        </tr>',
            '    </thead>',
            '    <tbody>',
        ])

        for page in page_results:
            row_class = ' class="changed"' if page["text_changed"] else ""
            html_parts.extend([
                f'        <tr{row_class}>',
                f'            <td>{page["number"]}</td>',
                f'            <td>{page["visual_similarity"]:.1%}</td>',
                f'            <td>{"Yes" if page["text_changed"] else "No"}</td>',
                '            <td>',
            ])
            if page["text_diff"]:
                html_parts.extend([
                    '                <details>',
                    '                    <summary>View text diff</summary>',
                    f'                    <pre>{page["text_diff"]}</pre>',
                    '                </details>',
                ])
            html_parts.extend([
                '            </td>',
                '        </tr>',
            ])

        html_parts.extend([
            '    </tbody>',
            '</table>',
        ])

        return "\n".join(html_parts)

    def extract_text(self, path: Path) -> str:
        """Extract text from a PDF for textconv usage."""
        try:
            doc = fitz.open(str(path))
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            doc.close()
            return "\n\n".join(text_parts)
        except Exception as e:
            return f"Error extracting text: {e}"
