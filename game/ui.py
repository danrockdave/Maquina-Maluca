"""Interactive menu widgets drawn with the rasterizer."""
from gfx.fill import fill_rect
from gfx.raster import draw_rect_outline
from gfx.font import draw_text_centered, text_width, text_height, draw_text
from game import config as C


class Button:
    def __init__(self, rect, label, scale=2, on_click=None, color=None):
        self.rect = tuple(rect)
        self.label = label
        self.scale = scale
        self.on_click = on_click
        self.color = color or C.ACCENT

    def hit(self, pos):
        x, y, w, h = self.rect
        return x <= pos[0] < x + w and y <= pos[1] < y + h

    def draw(self, fb, hover=False, active=False):
        x, y, w, h = self.rect
        base = self.color
        if active:
            top, bottom = base, tuple(int(c * 0.6) for c in base)
            text = (20, 20, 25)
        elif hover:
            top, bottom = tuple(min(255, int(c * 1.15)) for c in base), tuple(int(c * 0.8) for c in base)
            text = (20, 20, 25)
        else:
            top, bottom = (80, 86, 104), (52, 56, 70)
            text = C.TEXT
        fill_rect(fb, x, y, x + w - 1, y + h - 1,
                  {'kind': 'gradient', 'colors': [top, top, bottom, bottom]})
        draw_rect_outline(fb, x, y, x + w - 1, y + h - 1, (15, 15, 20))
        draw_rect_outline(fb, x + 1, y + 1, x + w - 2, y + h - 2, tuple(min(255, c + 40) for c in top))
        scale = self.scale
        while scale > 1 and text_width(self.label, scale) > w - 12:
            scale -= 1
        ty = y + (h - text_height(scale)) // 2
        draw_text_centered(fb, x + w // 2, ty, self.label, text, scale)


def wrap_text(text, max_width, scale):
    words = text.split(' ')
    lines, current = [], ''
    for word in words:
        candidate = word if not current else current + ' ' + word
        if text_width(candidate, scale) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_panel(fb, rect, title=None):
    x, y, w, h = rect
    fill_rect(fb, x, y, x + w - 1, y + h - 1, {'kind': 'flat', 'color': C.PANEL_BG})
    draw_rect_outline(fb, x, y, x + w - 1, y + h - 1, C.PANEL_BORDER)
    if title:
        draw_text(fb, x + 8, y + 6, title, C.ACCENT, 2)
