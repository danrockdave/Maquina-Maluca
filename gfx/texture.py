"""Texture loading: image file -> numpy matrix (width, height, 3)."""
import os
import numpy as np
import pygame

_CACHE = {}
ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'assets', 'textures')


def load_texture(name):
    """Loads assets/textures/<name>.png into a numpy array. If the file is
    missing, the texture is generated procedurally (tools/make_textures.py)."""
    if name in _CACHE:
        return _CACHE[name]
    path = os.path.join(ASSET_DIR, f"{name}.png")
    if os.path.exists(path):
        surface = pygame.image.load(path)
        arr = pygame.surfarray.array3d(surface).astype(np.uint8)
    else:
        from tools.make_textures import generate
        arr = generate(name)
    _CACHE[name] = arr
    return arr


def load_all(names):
    return {n: load_texture(n) for n in names}
