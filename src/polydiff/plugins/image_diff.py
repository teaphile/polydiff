"""Image diff plugin for polydiff."""

import base64
import io
from pathlib import Path
from typing import Optional

from PIL import Image

from ..core.plugin_base import DiffOptions, DiffPlugin, DiffResult
from ..utils.image_ops import (
    compute_pixel_diff,
    compute_ssim,
    create_diff_overlay,
    create_side_by_side,
    downsample_image,
)


class ImageDiffPlugin(DiffPlugin):
    """Plugin for diffing image files."""

    name = "polydiff-image"
    supported_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]

    def diff(self, path_a: Path, path_b: Path, options: DiffOptions) -> DiffResult:
        """Compare two images and return a DiffResult."""
        # Load images
        try:
            image_a = Image.open(path_a)
            image_b = Image.open(path_b)
        except Exception as e:
            return DiffResult(
                similarity=0.0,
                changed=True,
                summary=f"Error loading images: {e}",
                terminal_output=f"[red]Error:[/red] {e}",
            )

        # Get file info
        size_a = path_a.stat().st_size
        size_b = path_b.stat().st_size
        dim_a = image_a.size
        dim_b = image_b.size

        # Check for dimension changes
        dimensions_changed = dim_a != dim_b
        size_changed = size_a != size_b

        # Compute SSIM (perceptual similarity)
        similarity = compute_ssim(image_a, image_b)

        # Compute pixel diff for visualization
        diff_mask, bounding_boxes = compute_pixel_diff(image_a, image_b)

        # Create diff artifacts
        diff_overlay = create_diff_overlay(image_a, image_b, bounding_boxes)
        side_by_side = create_side_by_side(image_a, image_b, diff_overlay)

        # Determine if changed
        changed = similarity < 0.99  # Allow tiny floating point differences

        # Build summary
        summary_parts = []
        if not changed:
            summary_parts.append("Images are identical")
        else:
            summary_parts.append(f"{similarity:.1%} similar")
            if dimensions_changed:
                summary_parts.append(
                    f"dimensions changed: {dim_a[0]}x{dim_a[1]} → {dim_b[0]}x{dim_b[1]}"
                )
            if size_changed:
                size_diff = size_b - size_a
                direction = "+" if size_diff > 0 else ""
                summary_parts.append(f"size {direction}{size_diff:,} bytes")
            if bounding_boxes:
                summary_parts.append(f"{len(bounding_boxes)} region(s) changed")

        summary = ", ".join(summary_parts)

        # Build terminal output
        terminal_output = self._build_terminal_output(
            similarity, dim_a, dim_b, size_a, size_b, bounding_boxes, options.color
        )

        # Build HTML output
        html_output = None
        if options.output_format == "html":
            html_output = self._build_html_output(
                image_a, image_b, diff_overlay, similarity, summary,
                dim_a, dim_b, size_a, size_b, dimensions_changed, size_changed
            )

        # Save artifact if requested
        artifact_path = None
        if options.output_format == "image" and options.output_path:
            artifact_path = options.output_path
            side_by_side.save(artifact_path)

        # Build JSON output
        json_output = {
            "similarity": similarity,
            "changed": changed,
            "dimensions_a": list(dim_a),
            "dimensions_b": list(dim_b),
            "size_a": size_a,
            "size_b": size_b,
            "dimensions_changed": dimensions_changed,
            "size_changed": size_changed,
            "regions_changed": len(bounding_boxes),
            "bounding_boxes": [
                {"x": x, "y": y, "width": w, "height": h}
                for x, y, w, h in bounding_boxes
            ],
        }

        return DiffResult(
            similarity=similarity,
            changed=changed,
            summary=summary,
            terminal_output=terminal_output,
            html_output=html_output,
            json_output=json_output,
            artifact_path=artifact_path,
        )

    def _build_terminal_output(
        self,
        similarity: float,
        dim_a: tuple,
        dim_b: tuple,
        size_a: int,
        size_b: int,
        bounding_boxes: list,
        color: bool,
    ) -> str:
        """Build Rich-formatted terminal output."""
        lines = []

        # Similarity
        if similarity >= 0.99:
            lines.append("[green]✓ Images are identical[/green]")
        elif similarity >= 0.8:
            lines.append(f"[yellow]~ {similarity:.1%} similar[/yellow]")
        else:
            lines.append(f"[red]✗ {similarity:.1%} similar[/red]")

        # Dimensions
        if dim_a != dim_b:
            lines.append(f"[dim]Dimensions:[/dim] {dim_a[0]}x{dim_a[1]} → {dim_b[0]}x{dim_b[1]}")
        else:
            lines.append(f"[dim]Dimensions:[/dim] {dim_a[0]}x{dim_a[1]} (unchanged)")

        # File size
        size_diff = size_b - size_a
        if size_diff != 0:
            direction = "+" if size_diff > 0 else ""
            lines.append(f"[dim]File size:[/dim] {size_a:,} → {size_b:,} bytes ({direction}{size_diff:,})")
        else:
            lines.append(f"[dim]File size:[/dim] {size_a:,} bytes (unchanged)")

        # Changed regions
        if bounding_boxes:
            lines.append(f"[dim]Changed regions:[/dim] {len(bounding_boxes)}")
            for i, (x, y, w, h) in enumerate(bounding_boxes[:5], 1):
                lines.append(f"  [dim]Region {i}:[/dim] ({x}, {y}) {w}x{h}")
            if len(bounding_boxes) > 5:
                lines.append(f"  [dim]... and {len(bounding_boxes) - 5} more[/dim]")

        return "\n".join(lines)

    def _build_html_output(
        self,
        image_a: Image.Image,
        image_b: Image.Image,
        diff_overlay: Image.Image,
        similarity: float,
        summary: str,
        dim_a: tuple,
        dim_b: tuple,
        size_a: int,
        size_b: int,
        dimensions_changed: bool,
        size_changed: bool,
    ) -> str:
        """Build HTML output with embedded images."""
        def image_to_base64(img: Image.Image) -> str:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()

        old_b64 = image_to_base64(image_a)
        new_b64 = image_to_base64(image_b)
        overlay_b64 = image_to_base64(diff_overlay)

        # Build HTML
        html = f"""
        <h2>Image Diff Report</h2>

        <div class="summary {'identical' if similarity >= 0.99 else 'minor-changes' if similarity > 0.8 else 'major-changes'}">
            <strong>Similarity:</strong> {similarity:.1%} — {summary}
        </div>

        {'<div class="summary minor-changes"><strong>Dimension change:</strong> ' + f'{dim_a[0]}x{dim_a[1]} → {dim_b[0]}x{dim_b[1]}' + '</div>' if dimensions_changed else ''}

        {'<div class="summary minor-changes"><strong>File size change:</strong> ' + f'{size_a:,} → {size_b:,} bytes' + '</div>' if size_changed else ''}

        <h3>Visual Comparison</h3>
        <div class="side-by-side">
            <div>
                <h4>Original</h4>
                <img src="data:image/png;base64,{old_b64}" alt="Original image">
            </div>
            <div>
                <h4>Modified</h4>
                <img src="data:image/png;base64,{new_b64}" alt="Modified image">
            </div>
        </div>

        <h3>Diff Overlay</h3>
        <img src="data:image/png;base64,{overlay_b64}" alt="Diff overlay showing changed regions">
        """

        return html
