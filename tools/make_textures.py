"""
Procedural texture generator ("sprites" of the game).

The game may only display numeric matrices as images, so every texture is a
numpy array (width, height, 3). Running this file saves the textures as PNG in
assets/textures/ so they can also be loaded from disk (load image -> matrix).

    python -m tools.make_textures
"""
import os
import numpy as np

SIZE = 64
NAMES = ['wood', 'brick', 'metal', 'rubber', 'belt', 'cardboard', 'grass', 'sky']


def _grid(size=SIZE):
    x, y = np.meshgrid(np.arange(size), np.arange(size), indexing='ij')
    return x.astype(float), y.astype(float)


def _noise(rng, size, amount):
    return rng.uniform(-amount, amount, size=(size, size, 1))


def _clip(arr):
    return np.clip(arr, 0, 255).astype(np.uint8)


def wood(size=SIZE):
    rng = np.random.default_rng(1)
    x, y = _grid(size)
    base = np.array([172, 118, 62], dtype=float)
    grain = 0.82 + 0.18 * np.sin((y + 4.0 * np.sin(x * 0.25)) * 0.9)
    ring = 1.0 - 0.10 * ((np.floor(y / 11.0) % 2))
    arr = base * (grain * ring)[..., None] + _noise(rng, size, 9)
    return _clip(arr)


def brick(size=SIZE):
    rng = np.random.default_rng(2)
    x, y = _grid(size)
    row_h, mortar = 16, 3
    row = np.floor(y / row_h)
    offset = (row % 2) * (size // 4)
    bx = (x + offset) % (size // 2)
    is_mortar = (y % row_h < mortar) | (bx < mortar)
    brick_col = np.array([176, 74, 52], dtype=float)
    mortar_col = np.array([205, 196, 184], dtype=float)
    shade = 0.9 + 0.1 * ((row + np.floor((x + offset) / (size // 2))) % 3) / 2.0
    arr = np.where(is_mortar[..., None], mortar_col, brick_col * shade[..., None])
    arr = arr + _noise(rng, size, 10)
    return _clip(arr)


def metal(size=SIZE):
    rng = np.random.default_rng(3)
    x, y = _grid(size)
    base = 150 + 40 * np.sin((x + y) * 0.12) + 15 * np.sin(x * 0.7)
    arr = np.stack([base * 0.95, base, base * 1.08], axis=-1)
    # rivets in the corners
    for cx, cy in [(8, 8), (size - 9, 8), (8, size - 9), (size - 9, size - 9)]:
        d = np.hypot(x - cx, y - cy)
        arr[d < 4] = (90, 92, 100)
        arr[d < 2] = (210, 214, 224)
    arr = arr + _noise(rng, size, 6)
    return _clip(arr)


def rubber(size=SIZE):
    rng = np.random.default_rng(4)
    x, y = _grid(size)
    base = np.array([58, 60, 72], dtype=float)
    dots = ((x % 8 < 3) & (y % 8 < 3)).astype(float) * 22
    arr = base + dots[..., None] + _noise(rng, size, 5)
    return _clip(arr)


def belt(size=SIZE):
    """Dark belt with yellow chevrons along x so scrolling `u` shows motion."""
    rng = np.random.default_rng(5)
    x, y = _grid(size)
    base = np.array([48, 48, 52], dtype=float)
    chevron = ((x + np.abs(y - size / 2) * 0.6) % 16) < 5
    stripe = np.array([236, 190, 40], dtype=float)
    arr = np.where(chevron[..., None], stripe, base)
    edge = (y < 4) | (y > size - 5)
    arr[edge] = (120, 120, 126)
    arr = arr + _noise(rng, size, 6)
    return _clip(arr)


def cardboard(size=SIZE):
    rng = np.random.default_rng(6)
    x, y = _grid(size)
    base = np.array([206, 166, 104], dtype=float)
    lines = (y % 6 == 0).astype(float) * -18
    arr = base + lines[..., None] + _noise(rng, size, 8)
    return _clip(arr)


def grass(size=SIZE):
    rng = np.random.default_rng(7)
    x, y = _grid(size)
    base = np.array([70, 150, 60], dtype=float)
    blades = (np.sin(x * 1.7 + y * 0.3) > 0.7).astype(float) * 30
    arr = base + blades[..., None] + _noise(rng, size, 12)
    return _clip(arr)


def sky(size=SIZE):
    x, y = _grid(size)
    t = (y / (size - 1))[..., None]
    top = np.array([90, 150, 235], dtype=float)
    bottom = np.array([190, 220, 250], dtype=float)
    return _clip(top + (bottom - top) * t)


_GENERATORS = {
    'wood': wood, 'brick': brick, 'metal': metal, 'rubber': rubber,
    'belt': belt, 'cardboard': cardboard, 'grass': grass, 'sky': sky,
}


def generate(name):
    return _GENERATORS[name]()


def main():
    import pygame
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'assets', 'textures')
    os.makedirs(out_dir, exist_ok=True)
    for name in NAMES:
        arr = generate(name)
        surface = pygame.surfarray.make_surface(arr)
        path = os.path.join(out_dir, f"{name}.png")
        pygame.image.save(surface, path)
        print("saved", path)


if __name__ == '__main__':
    main()
