"""Cohen-Sutherland line clipping against an axis-aligned rectangle."""
from gfx.raster import draw_line

INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8


def _outcode(x, y, xmin, ymin, xmax, ymax):
    code = INSIDE
    if x < xmin:
        code |= LEFT
    elif x > xmax:
        code |= RIGHT
    if y < ymin:
        code |= TOP
    elif y > ymax:
        code |= BOTTOM
    return code


def cohen_sutherland(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """Returns the clipped segment (x0, y0, x1, y1) or None if fully outside.
    Bounds are inclusive."""
    c0 = _outcode(x0, y0, xmin, ymin, xmax, ymax)
    c1 = _outcode(x1, y1, xmin, ymin, xmax, ymax)
    while True:
        if not (c0 | c1):      # trivially accept
            return x0, y0, x1, y1
        if c0 & c1:            # trivially reject
            return None
        # Pick an endpoint outside the window and move it to the border
        c_out = c0 if c0 else c1
        if c_out & TOP:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
            y = ymin
        elif c_out & BOTTOM:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
            y = ymax
        elif c_out & RIGHT:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
            x = xmax
        else:  # LEFT
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
            x = xmin
        if c_out == c0:
            x0, y0 = x, y
            c0 = _outcode(x0, y0, xmin, ymin, xmax, ymax)
        else:
            x1, y1 = x, y
            c1 = _outcode(x1, y1, xmin, ymin, xmax, ymax)


def draw_line_clipped(fb, x0, y0, x1, y1, color, clip):
    """clip = (x0, y0, x1, y1) with exclusive x1/y1 (same convention as raster.set_pixel)."""
    seg = cohen_sutherland(x0, y0, x1, y1, clip[0], clip[1], clip[2] - 1, clip[3] - 1)
    if seg is None:
        return False
    draw_line(fb, seg[0], seg[1], seg[2], seg[3], color, clip)
    return True
