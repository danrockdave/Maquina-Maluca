"""
Region filling algorithms:
  - flood_fill      (seed fill: replaces the connected region of the seed color)
  - boundary_fill   (seed fill: fills until a boundary color is reached)
  - fill_polygon    (scanline fill with flat color, per-vertex gradient or texture)

Both seed fills are 4-connected and work span by span (each horizontal run is
written with one slice assignment, which is equivalent to consecutive set_pixel calls).
"""
import math
import numpy as np


# ---------------------------------------------------------------- seed fills

def _run_bounds(match, x):
    """Left/right limits of the True run in `match` that contains index x."""
    left = np.flatnonzero(~match[:x])
    xl = int(left[-1]) + 1 if left.size else 0
    right = np.flatnonzero(~match[x + 1:])
    xr = x + int(right[0]) if right.size else len(match) - 1
    return xl, xr


def _run_starts(match, xl, xr):
    """Start index of every True run inside match[xl:xr+1]."""
    seg = match[xl:xr + 1]
    padded = np.concatenate(([False], seg))
    starts = np.flatnonzero(padded[1:] & ~padded[:-1])
    return (starts + xl).tolist()


def _span_seed_fill(fb, x, y, new_color, predicate):
    """Generic span-based seed fill. `predicate(column)` returns a bool array
    telling which pixels of a framebuffer column (fb[:, y]) are fillable."""
    w, h = fb.shape[0], fb.shape[1]
    if not (0 <= x < w and 0 <= y < h):
        return
    new_color = np.array(new_color, dtype=np.uint8)
    stack = [(x, y)]
    while stack:
        x, y = stack.pop()
        match = predicate(fb[:, y])
        if not match[x]:
            continue
        xl, xr = _run_bounds(match, x)
        fb[xl:xr + 1, y] = new_color
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                nmatch = predicate(fb[:, ny])
                for sx in _run_starts(nmatch, xl, xr):
                    stack.append((sx, ny))


def flood_fill(fb, x, y, new_color):
    """Replaces the 4-connected region that has the seed's color."""
    target = fb[x, y].copy()
    if np.array_equal(target, np.array(new_color, dtype=np.uint8)):
        return

    def predicate(column):
        return np.all(column == target, axis=1)

    _span_seed_fill(fb, x, y, new_color, predicate)


def boundary_fill(fb, x, y, fill_color, boundary_color):
    """Fills the 4-connected region delimited by pixels of boundary_color."""
    boundary = np.array(boundary_color, dtype=np.uint8)
    fill = np.array(fill_color, dtype=np.uint8)

    def predicate(column):
        is_boundary = np.all(column == boundary, axis=1)
        is_filled = np.all(column == fill, axis=1)
        return ~(is_boundary | is_filled)

    _span_seed_fill(fb, x, y, fill_color, predicate)


# ---------------------------------------------------------------- scanline

def _scanline(fb, verts, attrs, clip, span_fn):
    """Core scanline algorithm.

    verts : list of (x, y) in device coordinates
    attrs : list of numpy arrays (one per vertex) interpolated linearly along edges
            and along each span (colors for gradients, (u, v) for textures)
    clip  : (x0, y0, x1, y1) exclusive
    span_fn(xs, xe, y, xa, xb, aa, ab): writes pixels xs..xe (inclusive) of row y,
            where xa/xb are the exact intersections and aa/ab their attributes.
    """
    n = len(verts)
    if n < 3:
        return
    ys = [v[1] for v in verts]
    y_min = max(int(math.ceil(min(ys))), clip[1])
    y_max = min(int(math.floor(max(ys))), clip[3] - 1)
    if y_min > y_max:
        return

    # Edge table: (y_top, y_bottom, x_at_top, dx/dy, attr_at_top, dattr/dy)
    edges = []
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        a0, a1 = attrs[i], attrs[(i + 1) % n]
        if y0 == y1:          # horizontal edges do not contribute
            continue
        if y0 > y1:
            x0, y0, x1, y1, a0, a1 = x1, y1, x0, y0, a1, a0
        inv = 1.0 / (y1 - y0)
        edges.append((y0, y1, x0, (x1 - x0) * inv, a0, (a1 - a0) * inv))

    for y in range(y_min, y_max + 1):
        crossings = []
        for (y0, y1, x0, dxdy, a0, dady) in edges:
            if y0 <= y < y1:  # half-open interval avoids double counting vertices
                t = y - y0
                crossings.append((x0 + dxdy * t, a0 + dady * t))
        if len(crossings) < 2:
            continue
        crossings.sort(key=lambda c: c[0])
        for i in range(0, len(crossings) - 1, 2):
            xa, aa = crossings[i]
            xb, ab = crossings[i + 1]
            xs = max(int(math.ceil(xa)), clip[0])
            xe = min(int(math.floor(xb)), clip[2] - 1)
            if xs > xe:
                continue
            span_fn(xs, xe, y, xa, xb, aa, ab)


def _span_params(xs, xe, xa, xb):
    width = xb - xa
    if width < 1e-9:
        return np.zeros(xe - xs + 1)
    return (np.arange(xs, xe + 1) - xa) / width


def fill_polygon(fb, verts, style, clip=None, textures=None):
    """Scanline polygon fill.

    style is a dict:
      {'kind': 'flat',     'color': (r, g, b)}
      {'kind': 'gradient', 'colors': [(r,g,b) per vertex]}
      {'kind': 'texture',  'name': str, 'uvs': [(u,v) per vertex], 'offset': (du, dv)}
    """
    if clip is None:
        clip = (0, 0, fb.shape[0], fb.shape[1])
    kind = style['kind']
    n = len(verts)

    if kind == 'flat':
        color = np.array(style['color'], dtype=np.uint8)
        zero = np.zeros(1)
        attrs = [zero] * n

        def span_fn(xs, xe, y, xa, xb, aa, ab):
            fb[xs:xe + 1, y] = color

    elif kind == 'gradient':
        attrs = [np.array(c, dtype=float) for c in style['colors']]

        def span_fn(xs, xe, y, xa, xb, aa, ab):
            t = _span_params(xs, xe, xa, xb)[:, None]
            cols = aa + (ab - aa) * t
            fb[xs:xe + 1, y] = cols.astype(np.uint8)

    elif kind == 'texture':
        tex = textures[style['name']]
        tw, th = tex.shape[0], tex.shape[1]
        du, dv = style.get('offset', (0.0, 0.0))
        attrs = [np.array(uv, dtype=float) for uv in style['uvs']]

        def span_fn(xs, xe, y, xa, xb, aa, ab):
            t = _span_params(xs, xe, xa, xb)
            # (u, v) interpolated along the span; the modulo makes textures repeat
            u = (aa[0] + (ab[0] - aa[0]) * t + du) % 1.0
            v = (aa[1] + (ab[1] - aa[1]) * t + dv) % 1.0
            fb[xs:xe + 1, y] = tex[(u * tw).astype(np.intp), (v * th).astype(np.intp)]
    else:
        raise ValueError(f"unknown style kind: {kind}")

    _scanline(fb, verts, attrs, clip, span_fn)


def fill_rect(fb, x0, y0, x1, y1, style, clip=None, textures=None):
    """Convenience wrapper: axis-aligned rectangle through the scanline filler."""
    verts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if style['kind'] == 'texture' and 'uvs' not in style:
        style = dict(style, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    fill_polygon(fb, verts, style, clip, textures)
