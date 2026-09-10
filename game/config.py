"""Screen layout and palette."""
SCREEN_W, SCREEN_H = 1024, 640
FPS = 60

# World (in world units, y grows downwards)
WORLD_W, WORLD_H = 1200, 800

# Device-space rectangles: (x, y, w, h). The main viewport keeps the world's
# 3:2 aspect ratio; the right column holds the inventory and the minimap.
MARGIN = 10
BOTTOM_H = 90
PANEL_W = 214
MAIN_VP = (MARGIN, MARGIN, SCREEN_W - PANEL_W - 3 * MARGIN,
           SCREEN_H - BOTTOM_H - 3 * MARGIN)                      # 780 x 520
PANEL = (MAIN_VP[0] + MAIN_VP[2] + MARGIN, MARGIN, PANEL_W, 380)  # parts inventory
MINIMAP_VP = (PANEL[0] + (PANEL_W - 195) // 2, PANEL[1] + PANEL[3] + MARGIN, 195, 130)
BOTTOM = (MARGIN, MAIN_VP[1] + MAIN_VP[3] + MARGIN, SCREEN_W - 2 * MARGIN, BOTTOM_H)

TEXTURE_NAMES = ['wood', 'brick', 'metal', 'rubber', 'belt', 'cardboard', 'grass', 'sky']

# Palette
BG = (24, 26, 36)
PANEL_BG = (44, 48, 62)
PANEL_BORDER = (110, 118, 140)
TEXT = (235, 235, 240)
TEXT_DIM = (150, 156, 172)
ACCENT = (255, 196, 60)
ACCENT_DARK = (190, 130, 20)
GOOD = (90, 220, 110)
BAD = (240, 90, 80)
SKY_TOP = (78, 140, 230)
SKY_BOTTOM = (185, 218, 250)
