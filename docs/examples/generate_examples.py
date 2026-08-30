#!/usr/bin/env python3
"""Generate example images for the demo."""

from PIL import Image, ImageDraw, ImageFont
import os


def create_example_images():
    """Create example images showing polydiff in action."""
    os.makedirs("output", exist_ok=True)

    # Create a simple "before" image
    img_before = Image.new("RGB", (400, 300), "white")
    draw_before = ImageDraw.Draw(img_before)

    # Draw a blue rectangle
    draw_before.rectangle([50, 50, 200, 150], fill="blue", outline="black", width=2)
    draw_before.text((60, 170), "Original", fill="black")

    # Create an "after" image with a change
    img_after = Image.new("RGB", (400, 300), "white")
    draw_after = ImageDraw.Draw(img_after)

    # Draw a blue rectangle with a red inner rectangle (change)
    draw_after.rectangle([50, 50, 200, 150], fill="blue", outline="black", width=2)
    draw_after.rectangle([80, 80, 170, 120], fill="red")
    draw_after.text((60, 170), "Modified", fill="black")

    # Save images
    img_before.save("output/before.png")
    img_after.save("output/after.png")

    print("Example images created in output/ directory")


if __name__ == "__main__":
    create_example_images()
