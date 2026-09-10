"""
Rasterization primitives built exclusively on top of set_pixel().

Framebuffer convention: numpy uint8 array with shape (width, height, 3),
so fb[x, y] = (r, g, b). This matches pygame.surfarray.blit_array().

A "clip" is a device-space rectangle (x0, y0, x1, y1) with exclusive x1/y1.
"""
import numpy as np


def make_framebuffer(width, height, color=(0, 0, 0)):
    fb = np.zeros((width, height, 3), dtype=np.uint8)
    fb[:, :] = color
    return fb


def set_pixel(fb, x, y, color, clip=None):
    """The single primitive everything else is built on."""
    if clip is None:
        if 0 <= x < fb.shape[0] and 0 <= y < fb.shape[1]:
            fb[x, y] = color
    else:
        if clip[0] <= x < clip[2] and clip[1] <= y < clip[3]:
            fb[x, y] = color


def draw_line(fb, x0, y0, x1, y1, color, clip=None):
    """Bresenham line algorithm (integer arithmetic only)."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        set_pixel(fb, x0, y0, color, clip)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_circle(fb, cx, cy, r, color, clip=None):
    """Midpoint circle algorithm with 8-way symmetry."""
    cx, cy, r = int(round(cx)), int(round(cy)), int(round(r))
    if r <= 0:
        set_pixel(fb, cx, cy, color, clip)
        return
    x, y = 0, r
    d = 1 - r
    while x <= y:
        set_pixel(fb, cx + x, cy + y, color, clip)
        set_pixel(fb, cx - x, cy + y, color, clip)
        set_pixel(fb, cx + x, cy - y, color, clip)
        set_pixel(fb, cx - x, cy - y, color, clip)
        set_pixel(fb, cx + y, cy + x, color, clip)
        set_pixel(fb, cx - y, cy + x, color, clip)
        set_pixel(fb, cx + y, cy - x, color, clip)
        set_pixel(fb, cx - y, cy - x, color, clip)
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1


def draw_ellipse(fb, cx, cy, rx, ry, color, clip=None):
    """Midpoint ellipse algorithm (two regions) with 4-way symmetry."""
    cx, cy, rx, ry = int(round(cx)), int(round(cy)), int(round(rx)), int(round(ry))
    if rx <= 0 or ry <= 0:
        draw_line(fb, cx - rx, cy - ry, cx + rx, cy + ry, color, clip)
        return

    def plot(x, y):
        set_pixel(fb, cx + x, cy + y, color, clip)
        set_pixel(fb, cx - x, cy + y, color, clip)
        set_pixel(fb, cx + x, cy - y, color, clip)
        set_pixel(fb, cx - x, cy - y, color, clip)

    rx2, ry2 = rx * rx, ry * ry
    two_rx2, two_ry2 = 2 * rx2, 2 * ry2
    x, y = 0, ry
    px, py = 0, two_rx2 * y

    # Region 1: slope magnitude < 1
    p = round(ry2 - rx2 * ry + 0.25 * rx2)
    while px < py:
        plot(x, y)
        x += 1
        px += two_ry2
        if p < 0:
            p += ry2 + px
        else:
            y -= 1
            py -= two_rx2
            p += ry2 + px - py
    plot(x, y)

    # Region 2: slope magnitude >= 1
    p = round(ry2 * (x + 0.5) ** 2 + rx2 * (y - 1) ** 2 - rx2 * ry2)
    while y > 0:
        y -= 1
        py -= two_rx2
        if p > 0:
            p += rx2 - py
        else:
            x += 1
            px += two_ry2
            p += rx2 - py + px
        plot(x, y)


def draw_hline(fb, x0, x1, y, color, clip=None):
    """Horizontal run of set_pixel calls written as one slice assignment."""
    cx0, cy0, cx1, cy1 = clip if clip is not None else (0, 0, fb.shape[0], fb.shape[1])
    if not (cy0 <= y < cy1):
        return
    xa, xb = max(min(x0, x1), cx0), min(max(x0, x1) + 1, cx1)
    if xa < xb:
        fb[xa:xb, y] = color


def draw_vline(fb, x, y0, y1, color, clip=None):
    cx0, cy0, cx1, cy1 = clip if clip is not None else (0, 0, fb.shape[0], fb.shape[1])
    if not (cx0 <= x < cx1):
        return
    ya, yb = max(min(y0, y1), cy0), min(max(y0, y1) + 1, cy1)
    if ya < yb:
        fb[x, ya:yb] = color


def draw_rect_outline(fb, x0, y0, x1, y1, color, clip=None):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    draw_hline(fb, x0, x1, y0, color, clip)
    draw_hline(fb, x0, x1, y1, color, clip)
    draw_vline(fb, x0, y0, y1, color, clip)
    draw_vline(fb, x1, y0, y1, color, clip)


def draw_polyline(fb, points, color, closed=True, clip=None):
    n = len(points)
    for i in range(n if closed else n - 1):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        draw_line(fb, x0, y0, x1, y1, color, clip)
