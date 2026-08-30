"""Shared image operations for diff computation."""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def downsample_image(
    image: Image.Image,
    max_dimension: int = 2000,
) -> Image.Image:
    """Downsample an image if it's larger than max_dimension on any side.

    Args:
        image: PIL Image to potentially downsample
        max_dimension: Maximum allowed dimension (width or height)

    Returns:
        Downsampled image (or original if already small enough)
    """
    width, height = image.size
    if width <= max_dimension and height <= max_dimension:
        return image

    # Calculate new dimensions maintaining aspect ratio
    ratio = min(max_dimension / width, max_dimension / height)
    new_size = (int(width * ratio), int(height * ratio))

    return image.resize(new_size, Image.Resampling.LANCZOS)


def compute_ssim(
    image_a: Image.Image,
    image_b: Image.Image,
    downsample: bool = True,
    max_dimension: int = 2000,
) -> float:
    """Compute Structural Similarity Index (SSIM) between two images.

    SSIM is robust to minor recompression artifacts, unlike raw pixel-diff.

    Args:
        image_a: First image (PIL Image)
        image_b: Second image (PIL Image)
        downsample: Whether to downsample large images before comparison
        max_dimension: Maximum dimension for downsampling

    Returns:
        SSIM score between 0.0 (completely different) and 1.0 (identical)
    """
    if downsample:
        image_a = downsample_image(image_a, max_dimension)
        image_b = downsample_image(image_b, max_dimension)

    # Convert to grayscale for SSIM (standard approach)
    gray_a = np.array(image_a.convert("L"))
    gray_b = np.array(image_b.convert("L"))

    # If dimensions differ after downsampling, resize to match
    if gray_a.shape != gray_b.shape:
        # Resize to the smaller dimensions
        min_h = min(gray_a.shape[0], gray_b.shape[0])
        min_w = min(gray_a.shape[1], gray_b.shape[1])
        gray_a = gray_a[:min_h, :min_w]
        gray_b = gray_b[:min_h, :min_w]

    # Compute SSIM
    score, _ = structural_similarity(gray_a, gray_b, full=True)
    return float(score)


def compute_pixel_diff(
    image_a: Image.Image,
    image_b: Image.Image,
    threshold: int = 30,
) -> Tuple[np.ndarray, list[Tuple[int, int, int, int]]]:
    """Compute pixel-level difference between two images.

    Args:
        image_a: First image (PIL Image)
        image_b: Second image (PIL Image)
        threshold: Pixel difference threshold (0-255) to consider as "changed"

    Returns:
        Tuple of:
            - diff_mask: Binary mask where 1 = changed pixel
            - bounding_boxes: List of (x, y, width, height) for changed regions
    """
    # Ensure same size
    if image_a.size != image_b.size:
        # Resize to the smaller dimensions
        min_w = min(image_a.width, image_b.width)
        min_h = min(image_a.height, image_b.height)
        image_a = image_a.resize((min_w, min_h), Image.Resampling.LANCZOS)
        image_b = image_b.resize((min_w, min_h), Image.Resampling.LANCZOS)

    # Convert to numpy arrays
    arr_a = np.array(image_a.convert("RGB")).astype(np.int16)
    arr_b = np.array(image_b.convert("RGB")).astype(np.int16)

    # Compute absolute difference
    diff = np.abs(arr_a - arr_b)

    # Create binary mask (any channel exceeds threshold)
    diff_mask = np.any(diff > threshold, axis=2).astype(np.uint8)

    # Find bounding boxes of changed regions using connected components
    bounding_boxes = _find_bounding_boxes(diff_mask)

    return diff_mask, bounding_boxes


def _find_bounding_boxes(
    mask: np.ndarray,
    min_area: int = 100,
) -> list[Tuple[int, int, int, int]]:
    """Find bounding boxes of connected regions in a binary mask.

    Args:
        mask: Binary mask (0s and 1s)
        min_area: Minimum area to consider as a region

    Returns:
        List of (x, y, width, height) bounding boxes
    """
    try:
        from scipy import ndimage
        labeled, num_features = ndimage.label(mask)
    except ImportError:
        # Fallback: simple grid-based detection
        return _simple_bounding_boxes(mask, min_area)

    boxes = []
    for i in range(1, num_features + 1):
        region = np.where(labeled == i)
        if len(region[0]) < min_area:
            continue

        y_min, y_max = region[0].min(), region[0].max()
        x_min, x_max = region[1].min(), region[1].max()

        boxes.append((
            int(x_min),
            int(y_min),
            int(x_max - x_min + 1),
            int(y_max - y_min + 1),
        ))

    return boxes


def _simple_bounding_boxes(
    mask: np.ndarray,
    min_area: int = 100,
) -> list[Tuple[int, int, int, int]]:
    """Simple fallback bounding box detection without scipy."""
    h, w = mask.shape
    boxes = []

    # Divide into grid cells and find changed regions
    cell_size = 50
    for y in range(0, h, cell_size):
        for x in range(0, w, cell_size):
            cell = mask[y:y + cell_size, x:x + cell_size]
            if np.sum(cell) >= min_area:
                boxes.append((x, y, cell_size, cell_size))

    return boxes


def create_diff_overlay(
    image_a: Image.Image,
    image_b: Image.Image,
    bounding_boxes: list[Tuple[int, int, int, int]],
    color: Tuple[int, int, int] = (255, 0, 0),
    alpha: int = 128,
) -> Image.Image:
    """Create a diff overlay image with bounding boxes around changed regions.

    Args:
        image_a: Original image
        image_b: Modified image
        bounding_boxes: List of (x, y, width, height) boxes to highlight
        color: RGB color for highlighting
        alpha: Alpha transparency for highlight (0-255)

    Returns:
        New image with diff overlay
    """
    # Create a copy of image_b as the base
    overlay = image_b.copy().convert("RGBA")

    # Create highlight layer
    highlight = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    highlight_arr = np.array(highlight)

    # Draw bounding boxes
    for x, y, w, h in bounding_boxes:
        # Clamp to image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, overlay.width - x)
        h = min(h, overlay.height - y)

        # Draw filled rectangle with transparency
        highlight_arr[y:y + h, x:x + w] = (*color, alpha)

    highlight = Image.fromarray(highlight_arr)

    # Composite
    result = Image.alpha_composite(overlay, highlight)

    return result.convert("RGB")


def create_side_by_side(
    image_a: Image.Image,
    image_b: Image.Image,
    diff_overlay: Optional[Image.Image] = None,
    padding: int = 10,
) -> Image.Image:
    """Create a side-by-side comparison image.

    Args:
        image_a: Original image
        image_b: Modified image
        diff_overlay: Optional diff overlay image (shown as third panel)
        padding: Padding between images in pixels

    Returns:
        Combined side-by-side image
    """
    # Ensure same height
    max_height = max(image_a.height, image_b.height)

    def pad_to_height(img: Image.Image, height: int) -> Image.Image:
        if img.height == height:
            return img
        padded = Image.new("RGB", (img.width, height), (240, 240, 240))
        padded.paste(img, (0, 0))
        return padded

    image_a = pad_to_height(image_a, max_height)
    image_b = pad_to_height(image_b, max_height)

    panels = [image_a, image_b]
    if diff_overlay:
        diff_overlay = pad_to_height(diff_overlay, max_height)
        panels.append(diff_overlay)

    # Calculate total width
    total_width = sum(p.width for p in panels) + padding * (len(panels) - 1)

    # Create combined image
    combined = Image.new("RGB", (total_width, max_height), (255, 255, 255))

    x_offset = 0
    for panel in panels:
        combined.paste(panel, (x_offset, 0))
        x_offset += panel.width + padding

    return combined
