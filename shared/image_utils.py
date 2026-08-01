"""Shared image utility functions for BaseCamp Linux."""
from PIL import Image

# Per-channel lookup tables for the RGB565 packing, applied with bytes.translate
# so the work happens in C instead of per pixel in Python. Splitting the 16-bit
# value into its two output bytes up front is what makes that possible:
#   high byte = (r & 0xF8) | (g >> 5)
#   low  byte = ((g << 3) & 0xE0) | (b >> 3)
_HI_R = bytes((v & 0xF8) for v in range(256))
_HI_G = bytes((v >> 5) for v in range(256))
_LO_G = bytes(((v << 3) & 0xE0) for v in range(256))
_LO_B = bytes((v >> 3) for v in range(256))


def image_to_rgb565(image_path, size=(72, 72), frame=0):
    """Convert image file to RGB565 little-endian bytes at the given size.

    size=(72, 72)    → numpad button displays (D1-D4)
    size=(240, 204)  → main OLED display

    For animated GIFs, ``frame`` selects which frame to use (0-based).

    The conversion runs on whole byte strings rather than pixel by pixel: the
    channels are sliced out of the raw RGB buffer, mapped through the tables
    above, combined with one big-integer OR and interleaved with a bytearray
    slice assignment. Every step is a C-level operation, which is what the
    per-pixel getpixel/struct.pack loop cost us on larger sizes and animated
    GIFs. NumPy would do the same job, but importing it inside the AppImage
    aborts the process: the bundled libflexiblas cannot find a BLAS backend
    there and calls abort(), which no try/except can catch.
    """
    img = Image.open(image_path)
    if frame > 0 and getattr(img, 'n_frames', 1) > 1:
        img.seek(min(frame, img.n_frames - 1))
    img = img.resize(size, Image.LANCZOS).convert('RGB')

    raw = img.tobytes()
    n = len(raw) // 3
    if n == 0:
        return b""
    r, g, b = raw[0::3], raw[1::3], raw[2::3]
    hi = (int.from_bytes(r.translate(_HI_R), 'big')
          | int.from_bytes(g.translate(_HI_G), 'big')).to_bytes(n, 'big')
    lo = (int.from_bytes(g.translate(_LO_G), 'big')
          | int.from_bytes(b.translate(_LO_B), 'big')).to_bytes(n, 'big')
    out = bytearray(2 * n)
    out[0::2] = lo   # little-endian: low byte first
    out[1::2] = hi
    return bytes(out)
