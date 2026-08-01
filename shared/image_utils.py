"""Shared image utility functions for BaseCamp Linux."""
import numpy as np
from PIL import Image


def image_to_rgb565(image_path, size=(72, 72), frame=0):
    """Convert image file to RGB565 little-endian bytes at the given size.

    size=(72, 72)    → numpad button displays (D1-D4)
    size=(240, 204)  → main OLED display

    For animated GIFs, ``frame`` selects which frame to use (0-based).

    Vectorized with NumPy: identical output to the original pixel-by-pixel
    implementation, but avoids per-pixel Python function call overhead
    (getpixel/struct.pack), which is the actual bottleneck for larger
    sizes and animated GIFs — not something extra CPU cores fix, since a
    tight per-pixel Python loop doesn't parallelize well and the work
    itself was just needlessly slow per element.
    """
    img = Image.open(image_path)
    if frame > 0 and getattr(img, 'n_frames', 1) > 1:
        img.seek(min(frame, img.n_frames - 1))
    img = img.resize(size, Image.LANCZOS).convert('RGB')

    arr = np.asarray(img, dtype=np.uint16)  # shape (H, W, 3), H=size[1], W=size[0]
    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]
    value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    # value has shape (H, W) in row-major order == same y-then-x iteration
    # order as the original nested loop, so tobytes() matches exactly.
    return value.astype('<u2').tobytes()
