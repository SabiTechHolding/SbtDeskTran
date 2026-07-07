"""
Generate app icon (icon.ico) for SbtDeskTran.
Run once: python create_icon.py
Requires no extra dependencies — uses only tkinter + PIL if available,
otherwise falls back to a pure-Python ICO writer.
"""
import struct, zlib, os

# ── Pure-Python ICO generator (no Pillow needed) ──────────────────────────────
# We'll draw a simple "⇄" translation arrow logo using raw RGBA pixels,
# then pack it into a valid .ico file with 256x256, 64x64, 48x48, 32x32, 16x16.

def _make_rgba(size: int) -> bytes:
    """Return RGBA bytes for a single icon frame at `size`×`size`."""
    import math

    w = h = size
    img = bytearray(w * h * 4)  # RGBA flat

    # Background: deep blue-purple (#1e1e2e Catppuccin base)
    BG   = (30, 30, 46, 255)
    # Accent: lavender (#cba6f7)
    ACC  = (203, 166, 247, 255)
    # Arrow colour: teal (#89dceb)
    ARW  = (137, 220, 235, 255)

    def px(x, y, colour):
        if 0 <= x < w and 0 <= y < h:
            off = (y * w + x) * 4
            img[off:off+4] = colour

    def fill_rect(x0, y0, x1, y1, colour):
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                px(xx, yy, colour)

    def circle(cx, cy, r, colour, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx)**2 + (yy - cy)**2 <= r*r:
                    px(xx, yy, colour)

    def draw_arrow_right(cx, cy, length, thick, colour):
        """→ arrow centred at (cx, cy)."""
        half = thick // 2
        # shaft
        fill_rect(cx - length//2, cy - half, cx + length//4, cy + half + 1, colour)
        # arrowhead (triangle)
        tip = cx + length//2
        for i in range(thick + thick//2):
            fill_rect(tip - i, cy - i, tip - i + 1, cy + i + 1, colour)

    def draw_arrow_left(cx, cy, length, thick, colour):
        """← arrow (mirror of →)."""
        half = thick // 2
        fill_rect(cx - length//4, cy - half, cx + length//2, cy + half + 1, colour)
        tip = cx - length//2
        for i in range(thick + thick//2):
            fill_rect(tip + i, cy - i, tip + i + 1, cy + i + 1, colour)

    # Rounded-rect background (approximate with circle corners)
    r_bg   = max(4, size // 8)
    margin = max(1, size // 16)
    # Fill body
    fill_rect(margin + r_bg, margin, w - margin - r_bg, h - margin, BG)
    fill_rect(margin, margin + r_bg, w - margin, h - margin - r_bg, BG)
    # Corners
    for cx, cy in [(margin+r_bg, margin+r_bg),
                   (w-margin-r_bg-1, margin+r_bg),
                   (margin+r_bg, h-margin-r_bg-1),
                   (w-margin-r_bg-1, h-margin-r_bg-1)]:
        circle(cx, cy, r_bg, BG)

    # Two exchange arrows  ⇄
    s = size
    length = max(6, s // 3)
    thick  = max(2, s // 14)
    gap    = max(2, s // 10)
    mid    = s // 2

    draw_arrow_right(mid, mid - gap - thick, length, thick, ACC)
    draw_arrow_left( mid, mid + gap + thick, length, thick, ARW)

    return bytes(img)


def _png_from_rgba(rgba: bytes, size: int) -> bytes:
    """Encode raw RGBA bytes as a minimal PNG."""
    w = h = size

    def _chunk(tag: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc    = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    # IHDR
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    # Replace color type 2 (RGB) → 6 (RGBA)
    ihdr = struct.pack(">II", w, h) + bytes([8, 6, 0, 0, 0])

    # IDAT: filter byte 0 before each row
    raw_rows = b""
    for y in range(h):
        raw_rows += b"\x00" + rgba[y * w * 4: (y+1) * w * 4]
    compressed = zlib.compress(raw_rows, 9)

    PNG_SIG = b"\x89PNG\r\n\x1a\n"
    return (PNG_SIG
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", compressed)
            + _chunk(b"IEND", b""))


def build_ico(path: str):
    """Build a multi-resolution .ico file and save to `path`."""
    SIZES = [256, 64, 48, 32, 16]
    images = []
    for sz in SIZES:
        rgba = _make_rgba(sz)
        png  = _png_from_rgba(rgba, sz)
        images.append((sz, png))

    # ICO header
    n = len(images)
    header = struct.pack("<HHH", 0, 1, n)  # reserved, type=1 (ico), count

    # Directory entries come right after header (each 16 bytes)
    dir_size  = n * 16
    data_offset = 6 + dir_size  # 6 = header size

    directory = b""
    data      = b""
    offset    = data_offset
    for sz, png in images:
        w = h = sz if sz < 256 else 0  # 256 stored as 0 in ICO spec
        entry = struct.pack("<BBBBHHII",
            w, h,       # width, height (0 = 256)
            0,          # colour count (0 = > 256)
            0,          # reserved
            1,          # colour planes
            32,         # bits per pixel
            len(png),   # size of image data
            offset,     # offset of image data
        )
        directory += entry
        data      += png
        offset    += len(png)

    with open(path, "wb") as f:
        f.write(header + directory + data)
    print(f"Icon saved → {path}  ({n} sizes: {', '.join(str(s) for s,_ in images)}px)")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    build_ico(out)
