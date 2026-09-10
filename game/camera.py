"""
Window -> Viewport mapping (world coordinates to device coordinates),
with pan (translation) and zoom (scale), plus all the drawing helpers that
apply the mapping and clip against the viewport.
"""
import math
from gfx.fill import fill_polygon
from gfx.clipping import draw_line_clipped
from gfx.raster import draw_circle, draw_ellipse


class Camera:
    MIN_WINDOW_W = 200.0

    def __init__(self, viewport, window, world=None, textures=None):
        self.vp = tuple(viewport)          # device rect (x, y, w, h)
        self.win = list(window)            # world rect [x, y, w, h]
        self.world = world                 # (w, h) used to clamp panning
        self.textures = textures or {}
        self._fix_aspect()

    # ------------------------------------------------------------ mapping
    def _fix_aspect(self):
        self.win[3] = self.win[2] * self.vp[3] / self.vp[2]

    @property
    def scale(self):
        return self.vp[2] / self.win[2]

    @property
    def clip(self):
        x, y, w, h = self.vp
        return (x, y, x + w, y + h)

    def world_to_device(self, x, y):
        s = self.scale
        return (self.vp[0] + (x - self.win[0]) * s,
                self.vp[1] + (y - self.win[1]) * s)

    def device_to_world(self, dx, dy):
        s = self.scale
        return (self.win[0] + (dx - self.vp[0]) / s,
                self.win[1] + (dy - self.vp[1]) / s)

    def contains_device(self, dx, dy):
        x, y, w, h = self.vp
        return x <= dx < x + w and y <= dy < y + h

    # ------------------------------------------------------------ transforms
    def pan(self, dx, dy):
        """Window translation (world units)."""
        self.win[0] += dx
        self.win[1] += dy
        self._clamp()

    def zoom(self, factor, anchor=None):
        """Window scaling about an anchor point (world coords) or the center."""
        if anchor is None:
            anchor = (self.win[0] + self.win[2] / 2, self.win[1] + self.win[3] / 2)
        ax, ay = anchor
        max_w = self.world[0] * 1.2 if self.world else 1e9
        new_w = min(max(self.win[2] * factor, self.MIN_WINDOW_W), max_w)
        ratio = new_w / self.win[2]
        self.win[0] = ax - (ax - self.win[0]) * ratio
        self.win[1] = ay - (ay - self.win[1]) * ratio
        self.win[2] = new_w
        self._fix_aspect()
        self._clamp()

    def _clamp(self):
        if not self.world:
            return
        margin = 0.1
        min_x = -self.world[0] * margin
        min_y = -self.world[1] * margin
        max_x = self.world[0] * (1 + margin) - self.win[2]
        max_y = self.world[1] * (1 + margin) - self.win[3]
        self.win[0] = min(max(self.win[0], min_x), max(max_x, min_x))
        self.win[1] = min(max(self.win[1], min_y), max(max_y, min_y))

    def fit_world(self):
        self.win = [0.0, 0.0, float(self.world[0]), 0.0]
        self._fix_aspect()

    # ------------------------------------------------------------ drawing
    def _visible(self, dverts):
        x0, y0, x1, y1 = self.clip
        xs = [v[0] for v in dverts]
        ys = [v[1] for v in dverts]
        return not (max(xs) < x0 or min(xs) >= x1 or max(ys) < y0 or min(ys) >= y1)

    def draw_shape(self, fb, shape):
        dverts = [self.world_to_device(x, y) for x, y in shape.verts]
        if not self._visible(dverts):
            return
        fill_polygon(fb, dverts, shape.style, self.clip, self.textures)
        if shape.outline is not None:
            n = len(dverts)
            for i in range(n):
                x0, y0 = dverts[i]
                x1, y1 = dverts[(i + 1) % n]
                draw_line_clipped(fb, x0, y0, x1, y1, shape.outline, self.clip)

    def draw_part(self, fb, part):
        for shape in part.world_shapes():
            self.draw_shape(fb, shape)
        part.extra_draw(fb, self)

    def draw_line_world(self, fb, x0, y0, x1, y1, color):
        dx0, dy0 = self.world_to_device(x0, y0)
        dx1, dy1 = self.world_to_device(x1, y1)
        draw_line_clipped(fb, dx0, dy0, dx1, dy1, color, self.clip)

    def draw_circle_world(self, fb, cx, cy, r, color):
        dx, dy = self.world_to_device(cx, cy)
        draw_circle(fb, dx, dy, r * self.scale, color, self.clip)

    def draw_ellipse_world(self, fb, cx, cy, rx, ry, color):
        dx, dy = self.world_to_device(cx, cy)
        draw_ellipse(fb, dx, dy, rx * self.scale, ry * self.scale, color, self.clip)

    def draw_window_of(self, fb, other, color):
        """Draws another camera's window as a rectangle (used by the minimap)."""
        x, y, w, h = other.win
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        for i in range(4):
            a, b = pts[i], pts[(i + 1) % 4]
            self.draw_line_world(fb, a[0], a[1], b[0], b[1], color)
