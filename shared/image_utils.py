"""Shared image utility functions for BaseCamp Linux."""
import struct
from PIL import Image

try:
    import numpy as np
except ImportError:  # optional: only speeds the conversion up, see below
    np = None


def image_to_rgb565(image_path, size=(72, 72), frame=0):
    """Convert image file to RGB565 little-endian bytes at the given size.

    size=(72, 72)    → numpad button displays (D1-D4)
    size=(240, 204)  → main OLED display

    For animated GIFs, ``frame`` selects which frame to use (0-based).

    Vectorized with NumPy when it is available: identical output to the
    pixel-by-pixel fallback below, but without the per-pixel Python call
    overhead (getpixel/struct.pack) that dominates larger sizes and animated
    GIFs. NumPy ships inside the AppImage; a source install without it simply
    takes the slower path instead of failing to import.
    """
    img = Image.open(image_path)
    if frame > 0 and getattr(img, 'n_frames', 1) > 1:
        img.seek(min(frame, img.n_frames - 1))
    img = img.resize(size, Image.LANCZOS).convert('RGB')

    if np is None:
        data = bytearray()
        for y in range(size[1]):
            for x in range(size[0]):
                r, g, b = img.getpixel((x, y))
                value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                data += struct.pack('<H', value)  # little-endian
        return bytes(data)

    arr = np.asarray(img, dtype=np.uint16)  # shape (H, W, 3), H=size[1], W=size[0]
    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]
    value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    # value has shape (H, W) in row-major order == same y-then-x iteration
    # order as the original nested loop, so tobytes() matches exactly.
    return value.astype('<u2').tobytes()
