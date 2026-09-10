"""Level definitions, custom level persistence and dict (de)serialization."""
import glob
import json
import math
import os
import time

from game.parts import (Ball, Bucket, Plank, Trampoline, Fan, Conveyor, Box, Wall,
                        Portal, Magnet, TNT, PART_TYPES, part_from_dict)

CUSTOM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'levels', 'custom')


class Level:
    def __init__(self, name, fixed, inventory, hint, sandbox=False, path=None):
        self.name = name
        self.fixed = fixed            # list of callables returning Part instances
        self.inventory = inventory    # list of (PartClass, count)
        self.hint = hint
        self.sandbox = sandbox
        self.path = path

    def build_parts(self):
        return [factory() for factory in self.fixed]

    # ------------------------------------------------------------ dict format
    @classmethod
    def from_dict(cls, data, path=None):
        part_dicts = [dict(p, fixed=True) for p in data.get('parts', [])]
        fixed = [lambda p=p: part_from_dict(p) for p in part_dicts]
        inventory = [(PART_TYPES[name], int(count)) for name, count in data.get('inventory', {}).items()
                     if name in PART_TYPES and int(count) > 0]
        return cls(data.get('name', 'FASE'), fixed, inventory, data.get('hint', ''), path=path)

    @staticmethod
    def to_dict(name, parts, hint):
        """Locked parts become the scenery; loose parts become the inventory."""
        fixed_parts = [p.to_dict() for p in parts if p.fixed or isinstance(p, Ball)]
        inventory = {}
        seen_portal_channels = set()
        for p in parts:
            if p.fixed or isinstance(p, Ball):
                continue
            if isinstance(p, Portal):
                if p.channel in seen_portal_channels:
                    continue
                seen_portal_channels.add(p.channel)
            key = type(p).__name__
            inventory[key] = inventory.get(key, 0) + 1
        return {'name': name, 'hint': hint, 'parts': fixed_parts, 'inventory': inventory}


# ---------------------------------------------------------------- custom levels on disk
def save_custom_level(parts, hint=""):
    os.makedirs(CUSTOM_DIR, exist_ok=True)
    existing = load_custom_levels()
    name = f"PERSONALIZADA {len(existing) + 1}"
    data = Level.to_dict(name, parts, hint or "FASE CRIADA NO EDITOR.")
    path = os.path.join(CUSTOM_DIR, f"fase_{int(time.time())}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return name, path


def delete_custom_level(level):
    if level.path and os.path.exists(level.path):
        os.remove(level.path)
        return True
    return False


def load_custom_levels():
    levels = []
    for path in sorted(glob.glob(os.path.join(CUSTOM_DIR, '*.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                levels.append(Level.from_dict(json.load(f), path=path))
        except (OSError, ValueError, KeyError):
            continue
    return levels


# ---------------------------------------------------------------- built-in levels
LEVELS = [
    Level(
        "1 - PRIMEIROS PASSOS",
        [lambda: Ball(160, 90, fixed=True),
         lambda: Bucket(1000, 735, fixed=True)],
        [(Plank, 3)],
        "USE AS TABUAS COMO RAMPAS PARA LEVAR A BOLA ATE O BALDE."),
    Level(
        "2 - CONTRA O MURO",
        [lambda: Ball(120, 80, fixed=True),
         lambda: Wall(620, 560, fixed=True),
         lambda: Box(620, 695, fixed=True),
         lambda: Bucket(1060, 735, fixed=True)],
        [(Plank, 2), (Trampoline, 1), (Fan, 1)],
        "O MURO ESTA NO CAMINHO. UM TRAMPOLIM OU UM VENTILADOR PODEM AJUDAR."),
    Level(
        "3 - VOLTA POR CIMA",
        [lambda: Ball(1080, 90, fixed=True),
         lambda: Plank(1010, 200, angle=math.radians(-10), fixed=True),
         lambda: Wall(560, 540, fixed=True),
         lambda: Bucket(140, 735, fixed=True)],
        [(Conveyor, 2), (Plank, 2), (Fan, 1), (Trampoline, 1), (Box, 1)],
        "A BOLA PRECISA ATRAVESSAR A TELA INTEIRA. ESTEIRAS E VENTILADORES SAO SEUS AMIGOS."),
    Level(
        "4 - PORTAIS E IMAS",
        [lambda: Ball(150, 90, fixed=True),
         lambda: Plank(230, 220, angle=math.radians(18), fixed=True),
         lambda: Wall(520, 420, fixed=True),
         lambda: Wall(520, 640, fixed=True),
         lambda: TNT(950, 560, fixed=True),
         lambda: Bucket(1060, 735, fixed=True)],
        [(Portal, 1), (Magnet, 1), (Plank, 2)],
        "O MURO VAI DO CHAO AO TETO. QUE TAL ATRAVESSAR POR UM PORTAL?"),
    Level(
        "5 - DESAFIO FINAL",
        [lambda: Ball(90, 700, fixed=True),
         lambda: Plank(170, 735, angle=math.radians(8), fixed=True),
         lambda: Wall(540, 620, fixed=True),
         lambda: Bucket(1000, 620, fixed=True),
         lambda: Box(1000, 710, fixed=True)],
        [(Fan, 2), (Conveyor, 1), (Plank, 2), (Trampoline, 2), (TNT, 1)],
        "O BALDE ESTA LA NO ALTO. SOPRE A BOLA PARA CIMA!"),
    Level(
        "LIVRE - MODO CRIATIVO",
        [lambda: Ball(200, 100, fixed=True),
         lambda: Bucket(900, 735, fixed=True)],
        [(cls, 9) for cls in (Plank, Trampoline, Fan, Conveyor, Box, Wall, Portal, Magnet, TNT)],
        "SEM LIMITES. MONTE A MAQUINA MAIS ABSURDA QUE CONSEGUIR.",
        sandbox=True),
]

EDITOR_LEVEL = Level(
    "EDITOR DE FASES",
    [lambda: Ball(200, 100, fixed=True),
     lambda: Bucket(900, 735, fixed=True)],
    [],
    "COLOQUE PECAS E APERTE F PARA TRAVAR AS QUE SERAO CENARIO. AS SOLTAS VIRAM O INVENTARIO. S SALVA.")
