"""Game scenes: splash, menu, level select, help and gameplay."""
import math
import pygame

from gfx.raster import draw_line, draw_circle, draw_ellipse, draw_rect_outline, draw_polyline
from gfx.fill import flood_fill, boundary_fill, fill_polygon, fill_rect
from gfx.font import draw_text, draw_text_centered, text_width, text_height
from gfx.transform import rotation_about, apply_to_points, apply_to_point
from gfx.clipping import draw_line_clipped
from game import config as C
from game.camera import Camera
from game.ui import Button, wrap_text, draw_panel
from game.parts import Ball, Bucket, Trampoline, Fan, Conveyor, Portal, TNT, PLACEABLE
from game.levels import LEVELS, EDITOR_LEVEL, load_custom_levels, save_custom_level, delete_custom_level
from game.generator import generate_random_level
from game import physics


class Scene:
    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, fb):
        pass


# ====================================================================== splash
class SplashScene(Scene):
    """Opening screen drawn ONLY with line / circle / ellipse rasterization and
    seed fills (flood fill and boundary fill). Rendered once and cached."""
    OUTLINE = (0, 0, 0)

    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.cached = None
        app.audio.music('menu')

    def _build(self, fb):
        """The scene is designed on an 800x520 canvas and scaled uniformly."""
        W, H = C.SCREEN_W, C.SCREEN_H
        s = min(W / 800.0, H / 520.0)
        ox = (W - 800 * s) / 2

        def X(v):
            return int(round(ox + v * s))

        def Y(v):
            return int(round(v * s))

        def R(v):
            return int(round(v * s))

        def line(x0, y0, x1, y1, color):
            draw_line(fb, X(x0), Y(y0), X(x1), Y(y1), color)

        def circle(cx, cy, r, color):
            draw_circle(fb, X(cx), Y(cy), R(r), color)

        def ellipse(cx, cy, rx, ry, color):
            draw_ellipse(fb, X(cx), Y(cy), R(rx), R(ry), color)

        def bfill(x, y, color, boundary):
            boundary_fill(fb, X(x), Y(y), color, boundary)

        OUT = self.OUTLINE
        fb[:, :] = (0, 0, 0)
        horizon = Y(400)
        # Sky: a gradient polygon (scanline) covering the top region
        fill_rect(fb, 0, 0, W - 1, horizon - 1, {'kind': 'gradient',
                                                 'colors': [C.SKY_TOP, C.SKY_TOP, C.SKY_BOTTOM, C.SKY_BOTTOM]})
        # Ground: horizon line + flood fill of the black area below it
        draw_line(fb, 0, horizon, W - 1, horizon, (40, 110, 40))
        flood_fill(fb, 10, min(H - 5, horizon + 40), (86, 170, 72))
        gx = 0
        while gx < W:                                  # blades of grass
            draw_line(fb, gx, horizon, gx + R(6), horizon - R(8), (40, 110, 40))
            draw_line(fb, gx + R(6), horizon - R(8), gx + R(12), horizon, (40, 110, 40))
            gx += R(40)

        # Ramp (triangle of lines) filled with boundary fill
        line(60, 300, 330, 398, OUT)
        line(330, 398, 60, 398, OUT)
        line(60, 398, 60, 300, OUT)
        bfill(80, 380, (180, 125, 65), OUT)
        for i in range(1, 6):                          # wood stripes
            yy = 300 + i * 18
            line(62, yy, 62 + (398 - yy) * 270 / 98, 396, (140, 95, 45))

        # Ball (midpoint circle) with boundary fill and a highlight
        circle(98, 262, 30, OUT)
        bfill(98, 262, (222, 52, 52), OUT)
        circle(88, 252, 7, (255, 200, 200))
        bfill(88, 252, (255, 200, 200), (255, 200, 200))
        line(140, 262, 175, 262, (255, 255, 255))      # motion lines
        line(140, 250, 168, 250, (255, 255, 255))

        # Gear (circle + teeth + hole) with boundary fill
        gcx, gcy, gr = 470, 330, 48
        circle(gcx, gcy, gr, OUT)
        for i in range(10):
            a = 2 * math.pi * i / 10
            ca, sa = math.cos(a), math.sin(a)
            px, py = -sa, ca                           # tangent direction
            r0, r1, hw = gr - 1, gr + 12, 7
            pts = [(gcx + r0 * ca - hw * px, gcy + r0 * sa - hw * py),
                   (gcx + r1 * ca - hw * px * 0.7, gcy + r1 * sa - hw * py * 0.7),
                   (gcx + r1 * ca + hw * px * 0.7, gcy + r1 * sa + hw * py * 0.7),
                   (gcx + r0 * ca + hw * px, gcy + r0 * sa + hw * py)]
            draw_polyline(fb, [(X(x), Y(y)) for x, y in pts], OUT, closed=True)
            bfill(gcx + (gr + 5) * ca, gcy + (gr + 5) * sa, (120, 128, 150), OUT)
        circle(gcx, gcy, 12, OUT)
        bfill(gcx, gcy - 30, (160, 168, 190), OUT)
        bfill(gcx, gcy, (60, 64, 80), OUT)

        # Balloon (midpoint ellipse) with boundary fill, highlight and string
        bx, by = 640, 150
        ellipse(bx, by, 46, 62, OUT)
        bfill(bx, by, (245, 190, 40), OUT)
        ellipse(bx - 16, by - 24, 10, 16, (255, 240, 180))
        bfill(bx - 16, by - 24, (255, 240, 180), (255, 240, 180))
        line(bx - 5, by + 62, bx + 5, by + 70, OUT)
        line(bx + 5, by + 70, bx - 5, by + 70, OUT)
        line(bx - 5, by + 70, bx - 5, by + 62, OUT)
        for sy in range(0, 120, 2):
            line(bx + 8 * math.sin(sy * 0.1), by + 72 + sy,
                 bx + 8 * math.sin((sy + 2) * 0.1), by + 74 + sy, (60, 60, 60))

        # Bucket (trapezoid of lines + rim ellipse) on the ground, boundary filled
        pts = [(690, 300), (770, 300), (760, 398), (700, 398)]
        draw_polyline(fb, [(X(x), Y(y)) for x, y in pts], OUT, closed=True)
        bfill(730, 350, (90, 150, 235), OUT)
        line(690, 320, 770, 320, (240, 200, 60))
        line(690, 321, 770, 321, (240, 200, 60))
        ellipse(730, 300, 40, 7, (200, 220, 250))
        bfill(730, 300, (140, 180, 245), (200, 220, 250))

        # Sun (circle) delimited by its own outline color (the sky is a gradient)
        circle(745, 62, 28, (255, 235, 120))
        bfill(745, 62, (255, 235, 120), (255, 235, 120))
        for i in range(12):
            a = 2 * math.pi * i / 12
            line(745 + 36 * math.cos(a), 62 + 36 * math.sin(a),
                 745 + 48 * math.cos(a), 62 + 48 * math.sin(a), (255, 235, 120))

        # Title (bitmap font, also set_pixel based) with a drop shadow
        ts = max(6, int(7 * s))
        draw_text_centered(fb, W // 2 + 4, Y(44), "MAQUINA MALUCA", (20, 30, 60), ts)
        draw_text_centered(fb, W // 2, Y(40), "MAQUINA MALUCA", C.ACCENT, ts)
        draw_text_centered(fb, W // 2, Y(112), "INSPIRADO EM THE INCREDIBLE MACHINE", (245, 250, 255), 2)
        draw_text_centered(fb, W // 2, Y(440), "TELA DESENHADA COM BRESENHAM, PONTO MEDIO,", (20, 50, 20), 1)
        draw_text_centered(fb, W // 2, Y(452), "FLOOD FILL E BOUNDARY FILL", (20, 50, 20), 1)
        self.cached = fb.copy()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.app.audio.play('start')
            self.app.set_scene(MenuScene(self.app))

    def update(self, dt):
        self.time += dt

    def draw(self, fb):
        if self.cached is None:
            self._build(fb)
        fb[:, :] = self.cached
        if int(self.time * 2) % 2 == 0:
            draw_text_centered(fb, C.SCREEN_W // 2, C.SCREEN_H - 40, "PRESSIONE QUALQUER TECLA", C.TEXT, 2)


# ====================================================================== menu
def _click(app, button):
    app.audio.play('click')
    button.on_click()


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        app.audio.music('menu')
        cx = C.SCREEN_W // 2
        top = C.SCREEN_H // 2 - 60
        self.buttons = [
            Button((cx - 120, top, 240, 42), "JOGAR", on_click=lambda: app.set_scene(PlayScene(app, LEVELS[0], 0))),
            Button((cx - 120, top + 52, 240, 42), "NIVEIS", on_click=lambda: app.set_scene(LevelSelectScene(app))),
            Button((cx - 120, top + 104, 240, 42), "COMO JOGAR", on_click=lambda: app.set_scene(HelpScene(app))),
            Button((cx - 120, top + 156, 240, 42), "SAIR", on_click=app.quit),
        ]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in self.buttons:
                if b.hit(event.pos):
                    _click(self.app, b)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                _click(self.app, self.buttons[0])
            elif event.key == pygame.K_ESCAPE:
                self.app.quit()
            elif event.key == pygame.K_m:
                self.app.audio.toggle_mute()

    def update(self, dt):
        self.time += dt

    def draw(self, fb):
        draw_background(fb)
        W, H = C.SCREEN_W, C.SCREEN_H
        draw_gear(fb, 130, H - 130, 80, self.time * 0.6)
        draw_gear(fb, W - 130, H - 130, 80, -self.time * 0.6 + 0.3)
        draw_gear(fb, 130, 120, 45, -self.time * 1.05)
        draw_gear(fb, W - 130, 120, 45, self.time * 1.05 + 0.2)
        draw_text_centered(fb, W // 2 + 3, 73, "MAQUINA MALUCA", (20, 30, 60), 7)
        draw_text_centered(fb, W // 2, 70, "MAQUINA MALUCA", C.ACCENT, 7)
        draw_text_centered(fb, W // 2, 140, "MONTE UMA MAQUINA ABSURDA PARA LEVAR A BOLA AO BALDE", C.TEXT, 2)
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(fb, hover=b.hit(mouse))
        draw_text_centered(fb, C.SCREEN_W // 2, C.SCREEN_H - 30, "TRABALHO DE COMPUTACAO GRAFICA - PYGAME + NUMPY", C.TEXT_DIM, 1)


_BACKGROUND_CACHE = {}


def draw_background(fb):
    """Static menu gradient, rasterized once and copied afterwards."""
    key = fb.shape
    if key not in _BACKGROUND_CACHE:
        fill_rect(fb, 0, 0, C.SCREEN_W - 1, C.SCREEN_H - 1,
                  {'kind': 'gradient', 'colors': [(30, 34, 52), (30, 34, 52), (14, 16, 24), (14, 16, 24)]})
        _BACKGROUND_CACHE[key] = fb.copy()
    else:
        fb[:, :] = _BACKGROUND_CACHE[key]


def draw_gear(fb, cx, cy, r, angle, teeth=10):
    """Animated gear polygon (rotation transform) filled by scanline."""
    pts = []
    for i in range(teeth * 2):
        a = math.pi * i / teeth
        rr = r if i % 2 == 0 else r * 0.8
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        a2 = a + math.pi / teeth * 0.5
        pts.append((cx + rr * math.cos(a2), cy + rr * math.sin(a2)))
    pts = apply_to_points(rotation_about(angle, cx, cy), pts)
    fill_polygon(fb, pts, {'kind': 'flat', 'color': (60, 66, 88)})
    draw_polyline(fb, pts, (100, 108, 136), closed=True)
    draw_circle(fb, cx, cy, int(r * 0.3), (100, 108, 136))


# ====================================================================== level select
class LevelSelectScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.pending_delete = None
        self.message = ""
        self._build()

    def _build(self):
        app = self.app
        W = C.SCREEN_W
        self.buttons = []
        self.delete_buttons = []
        self.custom = load_custom_levels()[-6:][::-1]     # newest first, max 6
        col_w = W // 2 - 90
        self.lx, self.rx, top, step = 60, W // 2 + 30, 110, 46
        for i, level in enumerate(LEVELS):
            self.buttons.append(Button((self.lx, top + i * step, col_w, 38), level.name, scale=1,
                                       on_click=lambda i=i: app.set_scene(PlayScene(app, LEVELS[i], i))))
        for i, level in enumerate(self.custom):
            self.buttons.append(Button((self.rx, top + i * step, col_w - 44, 38), level.name, scale=1,
                                       on_click=lambda lv=level: app.set_scene(PlayScene(app, lv))))
            self.delete_buttons.append((level, Button((self.rx + col_w - 38, top + i * step, 38, 38), "X",
                                                      color=C.BAD)))
        row = top + max(len(LEVELS), 6) * step + 10
        self.buttons.append(Button((self.lx, row, col_w, 40), "EDITOR DE FASES", color=(120, 200, 255),
                                   on_click=lambda: app.set_scene(PlayScene(app, EDITOR_LEVEL, editor=True))))
        self.buttons.append(Button((self.rx, row, col_w, 40), "FASE ALEATORIA", color=(200, 120, 255),
                                   on_click=lambda: app.set_scene(
                                       PlayScene(app, generate_random_level(), random_mode=True))))
        self.buttons.append(Button((W // 2 - 100, row + 52, 200, 38), "VOLTAR",
                                   on_click=lambda: app.set_scene(MenuScene(app))))

    def _delete(self, level):
        """Two clicks are required: the first one asks for confirmation."""
        if self.pending_delete is level:
            delete_custom_level(level)
            self.pending_delete = None
            self.message = f"'{level.name}' FOI EXCLUIDA."
            self.app.audio.play('remove')
            self._build()
        else:
            self.pending_delete = level
            self.message = f"CLIQUE NO X DE NOVO PARA EXCLUIR '{level.name}'."
            self.app.audio.play('click')

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for level, b in self.delete_buttons:
                if b.hit(event.pos):
                    self._delete(level)
                    return
            for b in self.buttons:
                if b.hit(event.pos):
                    _click(self.app, b)
                    return
            self.pending_delete = None
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_scene(MenuScene(self.app))

    def draw(self, fb):
        draw_background(fb)
        draw_text_centered(fb, C.SCREEN_W // 2, 30, "ESCOLHA UM NIVEL", C.ACCENT, 4)
        draw_text(fb, self.lx, 84, "FASES", C.TEXT, 2)
        draw_text(fb, self.rx, 84, "MINHAS FASES", C.TEXT, 2)
        if not self.custom:
            draw_text(fb, self.rx, 120, "NENHUMA FASE SALVA AINDA.", C.TEXT_DIM, 1)
            draw_text(fb, self.rx, 134, "CRIE UMA NO EDITOR DE FASES!", C.TEXT_DIM, 1)
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(fb, hover=b.hit(mouse))
        for level, b in self.delete_buttons:
            b.label = "?" if self.pending_delete is level else "X"
            b.draw(fb, hover=b.hit(mouse), active=self.pending_delete is level)
        if self.message:
            draw_text_centered(fb, C.SCREEN_W // 2, C.SCREEN_H - 24, self.message, C.ACCENT, 1)


# ====================================================================== help
class HelpScene(Scene):
    LINES = [
        ("OBJETIVO", C.ACCENT),
        ("LEVE A BOLA ATE O BALDE MONTANDO UMA MAQUINA COM AS PECAS DISPONIVEIS.", C.TEXT),
        ("", C.TEXT),
        ("MOUSE", C.ACCENT),
        ("CLIQUE NUMA PECA DO PAINEL E DEPOIS NA CENA PARA COLOCA-LA.", C.TEXT),
        ("ARRASTE PECAS PARA MOVE-LAS. BOTAO DIREITO GIRA A PECA.", C.TEXT),
        ("RODA DO MOUSE = ZOOM NA POSICAO DO CURSOR.", C.TEXT),
        ("", C.TEXT),
        ("TECLADO", C.ACCENT),
        ("Q / E ........ GIRA A PECA SELECIONADA", C.TEXT),
        ("DELETE ....... DEVOLVE A PECA AO PAINEL", C.TEXT),
        ("SETAS ........ MOVE A JANELA (PAN)", C.TEXT),
        ("+ / - ........ ZOOM        H = VER O MUNDO INTEIRO", C.TEXT),
        ("ESPACO ....... RODA / PARA A SIMULACAO", C.TEXT),
        ("ESC .......... MENU DE PAUSA", C.TEXT),
        ("M ............ LIGA / DESLIGA O SOM", C.TEXT),
        ("", C.TEXT),
        ("EDITOR DE FASES", C.ACCENT),
        ("F TRAVA/DESTRAVA A PECA SELECIONADA. TRAVADAS = CENARIO, SOLTAS = INVENTARIO. S SALVA.", C.TEXT),
    ]

    def __init__(self, app):
        super().__init__(app)
        self.back = Button((C.SCREEN_W // 2 - 100, C.SCREEN_H - 60, 200, 36), "VOLTAR",
                           on_click=lambda: app.set_scene(MenuScene(app)))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.back.hit(event.pos):
            _click(self.app, self.back)
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            _click(self.app, self.back)

    def draw(self, fb):
        draw_background(fb)
        draw_text_centered(fb, C.SCREEN_W // 2, 30, "COMO JOGAR", C.ACCENT, 4)
        y = 80
        for text, color in self.LINES:
            scale = 2 if color == C.ACCENT else 1
            draw_text(fb, 60, y, text, color, scale)
            y += 22 if color == C.ACCENT else 15
        self.back.draw(fb, hover=self.back.hit(pygame.mouse.get_pos()))


# ====================================================================== gameplay
class PlayScene(Scene):
    PAN_SPEED = 520.0

    EDITOR_TYPES = PLACEABLE + [Bucket]

    def __init__(self, app, level, level_index=None, editor=False, random_mode=False):
        super().__init__(app)
        self.level = level
        self.level_index = level_index
        self.editor = editor
        self.random_mode = random_mode
        self.parts = self.level.build_parts()
        self.ball = next(p for p in self.parts if isinstance(p, Ball))
        if editor:
            self.inventory = {cls: 99 for cls in self.EDITOR_TYPES}
            self.inventory_order = list(self.EDITOR_TYPES)
        else:
            self.inventory = {cls: n for cls, n in self.level.inventory}
            self.inventory_order = [cls for cls, _ in self.level.inventory]
        self.previews = {cls: cls(0, 0) for cls in self.inventory_order}

        world = (C.WORLD_W, C.WORLD_H)
        self.camera = Camera(C.MAIN_VP, [0, 0, C.WORLD_W, C.WORLD_H], world, app.textures)
        self.camera.fit_world()
        self.minimap = Camera(C.MINIMAP_VP, [0, 0, C.WORLD_W, C.WORLD_H], world, app.textures)
        self.minimap.fit_world()

        self.running = False
        self.won = False
        self.lost_timer = None
        self.paused = False
        self.selected = None
        self.placing = None
        self.dragging = False
        self.drag_offset = (0.0, 0.0)
        self.message = self.level.hint
        self.message_color = C.TEXT
        self.time = 0.0

        bx, by = C.BOTTOM[0] + C.BOTTOM[2] - 3 * 92, C.BOTTOM[1] + 8
        self.run_button = Button((bx, by, 86, 30), "RODAR", on_click=self.toggle_run, color=C.GOOD)
        self.reset_button = Button((bx + 92, by, 86, 30), "LIMPAR", on_click=self.clear_placed)
        self.menu_button = Button((bx + 184, by, 86, 30), "MENU", on_click=self.open_pause)
        self.save_button = Button((bx, by + 38, 178, 30), "SALVAR FASE (S)", on_click=self.save_level,
                                  color=(120, 200, 255))
        vx, vy, vw, vh = C.MAIN_VP
        cx, cy = vx + vw // 2, vy + vh // 2
        self.next_button = Button((cx - 130, cy + 20, 260, 38),
                                  "OUTRA FASE ALEATORIA" if random_mode else "PROXIMO NIVEL",
                                  on_click=self.next_level, color=C.GOOD)
        self.pause_top = cy - 130
        pause = [("CONTINUAR", self.close_pause, None),
                 ("REINICIAR NIVEL", self.restart, None)]
        if random_mode:
            pause.append(("SORTEAR OUTRA FASE", self.next_level, (200, 120, 255)))
        pause.append(("MENU PRINCIPAL", lambda: app.set_scene(MenuScene(app)), None))
        self.pause_buttons = [
            Button((cx - 130, self.pause_top + 50 + i * 48, 260, 38), label, on_click=fn, color=color)
            for i, (label, fn, color) in enumerate(pause)]
        self.inventory_buttons = []
        self._build_inventory_buttons()
        self.chrome = None            # static UI background (rasterized once)
        self.preview_cache = {}
        app.audio.music('game', 0.45)

    # ------------------------------------------------------------ actions
    @property
    def buckets(self):
        return [p for p in self.parts if isinstance(p, Bucket)]

    def _build_inventory_buttons(self):
        self.inventory_buttons = []
        x, y, w, h = C.PANEL
        n = max(1, len(self.inventory_order))
        step = min(40, (h - 34) // n)
        for i, cls in enumerate(self.inventory_order):
            rect = (x + 8, y + 30 + i * step, w - 16, step - 4)
            self.inventory_buttons.append((cls, rect))

    def toggle_run(self):
        if self.won:
            return
        if self.running:
            self.stop()
        else:
            self.running = True
            self.selected = None
            self.placing = None
            self.dragging = False
            self.app.audio.play('start')
            self.set_message("SIMULACAO RODANDO... (ESPACO PARA PARAR)", C.GOOD)

    def stop(self):
        if self.running:
            self.app.audio.play('stop')
        self.app.audio.stop_all_loops()
        self.running = False
        self.lost_timer = None
        for p in self.parts:
            p.reset()
        self.ball.reset()
        self.run_button.label = "RODAR"
        self.set_message(self.level.hint, C.TEXT)

    def clear_placed(self):
        self.stop()
        for p in [p for p in self.parts if not p.fixed]:
            self._return_to_inventory(p)
        self.selected = None

    def restart(self):
        self.app.set_scene(PlayScene(self.app, self.level, self.level_index, self.editor, self.random_mode))

    def next_level(self):
        if self.random_mode:
            self.app.set_scene(PlayScene(self.app, generate_random_level(), random_mode=True))
        elif self.level_index is not None and self.level_index + 1 < len(LEVELS):
            self.app.set_scene(PlayScene(self.app, LEVELS[self.level_index + 1], self.level_index + 1))
        else:
            self.app.set_scene(LevelSelectScene(self.app))

    def save_level(self):
        if not self.editor:
            return
        self.stop()
        name, _path = save_custom_level(self.parts)
        self.app.audio.play('win')
        self.set_message(f"FASE SALVA COMO '{name}'. ELA APARECE EM NIVEIS > MINHAS FASES.", C.GOOD)

    def toggle_fixed(self):
        if not self.editor or self.selected is None or isinstance(self.selected, Ball):
            return
        self.selected.fixed = not self.selected.fixed
        self.app.audio.play('rotate')
        state = "TRAVADA (CENARIO)" if self.selected.fixed else "SOLTA (INVENTARIO DO JOGADOR)"
        self.set_message(f"{self.selected.label}: {state}", C.TEXT)

    def open_pause(self):
        self.app.audio.play('click')
        self.app.audio.stop_all_loops()
        self.paused = True

    def close_pause(self):
        self.app.audio.play('click')
        self.paused = False

    def set_message(self, text, color=None):
        self.message = text
        self.message_color = color or C.TEXT

    def _return_to_inventory(self, part):
        if part in self.parts:
            self.parts.remove(part)
            self.app.audio.play('remove')
        if isinstance(part, Portal):
            for twin in [p for p in self.parts if isinstance(p, Portal) and p.channel == part.channel]:
                self.parts.remove(twin)
        cls = type(part)
        self.inventory[cls] = min(99, self.inventory.get(cls, 0) + 1)
        if self.selected is part:
            self.selected = None

    def _place(self, cls, wx, wy):
        if self.inventory.get(cls, 0) <= 0:
            self.set_message("NAO HA MAIS PECAS DESSE TIPO.", C.BAD)
            return
        if cls is Portal:
            used = {p.channel for p in self.parts if isinstance(p, Portal)}
            channel = next((c for c in range(len(Portal.COLORS)) if c not in used), None)
            if channel is None:
                self.set_message("JA HA PORTAIS DEMAIS NA CENA (3 PARES).", C.BAD)
                return
            part = Portal(wx, wy, channel=channel)
            twin = Portal(min(wx + 180, C.WORLD_W - 40), wy, channel=channel)
            self.parts.extend([part, twin])
        else:
            part = cls(wx, wy)
            self.parts.append(part)
        self.inventory[cls] -= 1
        self.selected = part
        self.app.audio.play('place')
        self.set_message(part.hint, C.TEXT)

    def _part_at(self, wx, wy):
        for part in reversed(self.parts):
            if part.contains(wx, wy):
                return part
        return None

    def _editable(self, part):
        """Loose parts are editable in play; everything is editable in the editor."""
        return part is not None and (self.editor or not part.fixed) and not self.running

    # ------------------------------------------------------------ events
    def handle_event(self, event):
        if self.paused:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for b in self.pause_buttons:
                    if b.hit(event.pos):
                        b.on_click()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.close_pause()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.app.audio.toggle_mute()
            return

        if event.type == pygame.KEYDOWN:
            self._key_down(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_motion(event)
        elif event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.camera.contains_device(*pos):
                self.camera.zoom(0.85 if event.y > 0 else 1 / 0.85, self.camera.device_to_world(*pos))

    def _key_down(self, key):
        if key == pygame.K_ESCAPE:
            self.open_pause()
        elif key == pygame.K_SPACE:
            self.toggle_run()
        elif key in (pygame.K_q, pygame.K_e) and self._editable(self.selected):
            self.selected.rotate(math.radians(-15 if key == pygame.K_q else 15))
            self.app.audio.play('rotate')
        elif key == pygame.K_f:
            self.toggle_fixed()
        elif key == pygame.K_s and self.editor:
            self.save_level()
        elif key == pygame.K_m:
            self.app.audio.toggle_mute()
        elif key in (pygame.K_DELETE, pygame.K_BACKSPACE) and self._editable(self.selected) \
                and not isinstance(self.selected, Ball):
            self._return_to_inventory(self.selected)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.camera.zoom(0.8)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.camera.zoom(1.25)
        elif key == pygame.K_h:
            self.camera.fit_world()
        elif key == pygame.K_n and self.won:
            self.next_level()

    def _mouse_down(self, event):
        pos = event.pos
        if event.button == 1:
            if self.won and self.next_button.hit(pos):
                _click(self.app, self.next_button)
                return
            buttons = [self.run_button, self.reset_button, self.menu_button]
            if self.editor:
                buttons.append(self.save_button)
            for b in buttons:
                if b.hit(pos):
                    b.on_click()
                    return
            for cls, rect in self.inventory_buttons:
                if _hit(rect, pos) and not self.running:
                    self.app.audio.play('click')
                    self.placing = None if self.placing is cls else cls
                    self.selected = None
                    self.set_message(self.previews[cls].hint if self.placing else self.level.hint)
                    return
            if self.camera.contains_device(*pos):
                wx, wy = self.camera.device_to_world(*pos)
                if self.running:
                    return
                if self.placing is not None:
                    self._place(self.placing, wx, wy)
                    if self.inventory.get(self.placing, 0) <= 0:
                        self.placing = None
                    return
                part = self._part_at(wx, wy)
                self.selected = part
                if part is not None:
                    suffix = " (TRAVADA)" if part.fixed and not isinstance(part, Ball) else ""
                    self.set_message(part.hint + suffix)
                    if self.editor or not part.fixed:
                        self.dragging = True
                        self.drag_offset = (part.x - wx, part.y - wy)
            elif self.minimap.contains_device(*pos):
                wx, wy = self.minimap.device_to_world(*pos)
                self.camera.pan(wx - (self.camera.win[0] + self.camera.win[2] / 2),
                                wy - (self.camera.win[1] + self.camera.win[3] / 2))
        elif event.button == 3:
            if self._editable(self.selected):
                self.selected.rotate(math.radians(15))
                self.app.audio.play('rotate')

    def _mouse_motion(self, event):
        if self.dragging and self.selected and not self.running:
            if self.camera.contains_device(*event.pos):
                wx, wy = self.camera.device_to_world(*event.pos)
                self.selected.x = min(max(wx + self.drag_offset[0], 0), C.WORLD_W)
                self.selected.y = min(max(wy + self.drag_offset[1], 0), C.WORLD_H)

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        if self.paused:
            return
        keys = pygame.key.get_pressed()
        pan = self.PAN_SPEED * dt * (self.camera.win[2] / 900.0)
        if keys[pygame.K_LEFT]:
            self.camera.pan(-pan, 0)
        if keys[pygame.K_RIGHT]:
            self.camera.pan(pan, 0)
        if keys[pygame.K_UP]:
            self.camera.pan(0, -pan)
        if keys[pygame.K_DOWN]:
            self.camera.pan(0, pan)

        for part in self.parts:
            part.update(dt)
        for preview in self.previews.values():
            preview.update(dt)

        if self.running and not self.won:
            physics.step(self.ball, self.parts, dt, on_impact=self._on_impact)
            self._update_loops()
            for p in self.parts:
                if isinstance(p, TNT) and p.just_exploded:
                    p.just_exploded = False
                    self.app.audio.play('boom')
            self.run_button.label = "PARAR"
            for bucket in self.buckets:
                if bucket.goal_reached(self.ball):
                    self.won = True
                    self.running = False
                    self.app.audio.stop_all_loops()
                    self.app.audio.play('win')
                    self.set_message("MISSAO CUMPRIDA! A BOLA CHEGOU AO BALDE.", C.GOOD)
            if self.lost_timer is None and (
                    self.ball.y > C.WORLD_H + 150 or self.ball.x < -300 or self.ball.x > C.WORLD_W + 300):
                self.lost_timer = 1.2
                self.app.audio.stop_all_loops()
                self.app.audio.play('lose')
                self.set_message("A BOLA CAIU NO VAZIO! TENTE OUTRA VEZ.", C.BAD)
        if self.lost_timer is not None:
            self.lost_timer -= dt
            if self.lost_timer <= 0:
                self.stop()

    # ------------------------------------------------------------ sound
    def _on_impact(self, part, shape, speed):
        if speed < 120.0:
            return
        volume = min(1.0, speed / 900.0)
        if isinstance(part, Trampoline):
            self.app.audio.play('boing', volume, min_interval=0.15)
        else:
            self.app.audio.play('bounce', volume, min_interval=0.08)

    def _update_loops(self):
        """Ambient loops: fan wind and conveyor motor while the machine runs."""
        audio = self.app.audio
        if any(isinstance(p, Fan) for p in self.parts):
            audio.loop('wind', 0.6)
        else:
            audio.stop_loop('wind')
        if any(isinstance(p, Conveyor) for p in self.parts):
            audio.loop('belt', 0.35)
        else:
            audio.stop_loop('belt')

    # ------------------------------------------------------------ drawing
    def _build_chrome(self, fb):
        """Everything that never changes: sky, panel backgrounds and borders."""
        fb[:, :] = C.BG
        x, y, w, h = C.MAIN_VP
        fill_rect(fb, x, y, x + w - 1, y + h - 1,
                  {'kind': 'gradient', 'colors': [C.SKY_TOP, C.SKY_TOP, C.SKY_BOTTOM, C.SKY_BOTTOM]})
        draw_rect_outline(fb, x - 1, y - 1, x + w, y + h, C.PANEL_BORDER)
        draw_panel(fb, C.PANEL, "PECAS")
        draw_panel(fb, C.BOTTOM)
        mx, my, mw, mh = C.MINIMAP_VP
        fill_rect(fb, mx, my, mx + mw - 1, my + mh - 1, {'kind': 'flat', 'color': (60, 90, 140)})
        draw_rect_outline(fb, mx - 1, my - 1, mx + mw, my + mh, C.PANEL_BORDER)
        self.chrome = fb.copy()

    def draw(self, fb):
        if self.chrome is None:
            self._build_chrome(fb)
        fb[:, :] = self.chrome
        self._draw_world(fb)
        self._draw_minimap(fb)
        self._draw_panel(fb)
        self._draw_bottom(fb)
        if self.won:
            self._draw_win(fb)
        if self.paused:
            self._draw_pause(fb)

    def _draw_world(self, fb):
        cam = self.camera
        x, y, w, h = C.MAIN_VP
        # world boundary drawn through Cohen-Sutherland clipping
        for (a, b) in (((0, 0), (C.WORLD_W, 0)), ((C.WORLD_W, 0), (C.WORLD_W, C.WORLD_H)),
                       ((C.WORLD_W, C.WORLD_H), (0, C.WORLD_H)), ((0, C.WORLD_H), (0, 0))):
            cam.draw_line_world(fb, a[0], a[1], b[0], b[1], (255, 255, 255))
        for part in self.parts:
            if part is not self.ball:
                cam.draw_part(fb, part)
        cam.draw_part(fb, self.ball)

        if self.selected is not None and not self.running:
            locked = self.editor and self.selected.fixed and not isinstance(self.selected, Ball)
            self._draw_selection(fb, self.selected, color=(120, 200, 255) if locked else None)
        if self.placing is not None and not self.running:
            mouse = pygame.mouse.get_pos()
            if cam.contains_device(*mouse):
                ghost = self.previews[self.placing]
                ghost.x, ghost.y = cam.device_to_world(*mouse)
                self._draw_selection(fb, ghost, color=(255, 255, 255))
                ghost.x, ghost.y = 0.0, 0.0
        draw_text(fb, x + 6, y + 6, f"ZOOM {cam.scale:.2f}X   JANELA ({cam.win[0]:.0f}, {cam.win[1]:.0f})",
                  (255, 255, 255), 1)

    def _draw_selection(self, fb, part, color=None):
        color = color or C.ACCENT
        x0, y0, x1, y1 = part.local_bounds()
        pad = 6
        corners = [(x0 - pad, y0 - pad), (x1 + pad, y0 - pad), (x1 + pad, y1 + pad), (x0 - pad, y1 + pad)]
        pts = apply_to_points(part.model_matrix(), corners)
        for i in range(4):
            a, b = pts[i], pts[(i + 1) % 4]
            self.camera.draw_line_world(fb, a[0], a[1], b[0], b[1], color)

    def _draw_minimap(self, fb):
        mm = self.minimap
        x, y, w, h = C.MINIMAP_VP
        for part in self.parts:
            mm.draw_part(fb, part)
        mm.draw_window_of(fb, self.camera, C.ACCENT)
        draw_text(fb, x + 4, y + 3, "MAPA", C.TEXT, 1)

    def _draw_panel(self, fb):
        mouse = pygame.mouse.get_pos()
        for cls, rect in self.inventory_buttons:
            rx, ry, rw, rh = rect
            count = self.inventory.get(cls, 0)
            active = self.placing is cls
            hover = _hit(rect, mouse)
            top = (95, 100, 120) if hover else (70, 74, 92)
            if active:
                top = C.ACCENT_DARK
            bottom = tuple(int(c * 0.65) for c in top)
            fill_rect(fb, rx, ry, rx + rw - 1, ry + rh - 1,
                      {'kind': 'gradient', 'colors': [top, top, bottom, bottom]})
            draw_rect_outline(fb, rx, ry, rx + rw - 1, ry + rh - 1, (15, 15, 20))
            preview_rect = (rx + 3, ry + 3, 46, rh - 6)
            self._draw_preview(fb, self.previews[cls], preview_rect)
            label_color = C.TEXT if count > 0 else C.TEXT_DIM
            if rh >= 34:
                draw_text(fb, rx + 54, ry + 6, cls.label, label_color, 1)
                draw_text(fb, rx + 54, ry + 19, "" if self.editor else f"X{count}",
                          C.ACCENT if count > 0 else C.TEXT_DIM, 2)
            else:
                draw_text(fb, rx + 54, ry + (rh - 7) // 2, cls.label if self.editor else f"{cls.label} X{count}",
                          label_color, 1)

    def _draw_preview(self, fb, part, rect):
        """Renders a part through its own tiny window/viewport (cached when static)."""
        key = type(part)
        rx, ry, rw, rh = rect
        cached = self.preview_cache.get(key)
        if not part.animated and cached is not None and cached.shape[:2] == (rw, rh):
            fb[rx:rx + rw, ry:ry + rh] = cached
            return
        x0, y0, x1, y1 = part.local_bounds()
        pad = 12
        bw, bh = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
        win_w = max(bw, bh * rect[2] / rect[3])
        win_h = win_w * rect[3] / rect[2]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cam = Camera(rect, [cx - win_w / 2, cy - win_h / 2, win_w, win_h], None, self.app.textures)
        fill_rect(fb, rect[0], rect[1], rect[0] + rect[2] - 1, rect[1] + rect[3] - 1,
                  {'kind': 'flat', 'color': (28, 30, 40)})
        cam.draw_part(fb, part)
        if not part.animated:
            self.preview_cache[key] = fb[rx:rx + rw, ry:ry + rh].copy()

    def _draw_bottom(self, fb):
        x, y, w, h = C.BOTTOM
        draw_text(fb, x + 10, y + 8, self.level.name, C.ACCENT, 2)
        lines = wrap_text(self.message, C.BOTTOM[2] - 3 * 92 - 30, 1)
        ty = y + 30
        for line in lines[:3]:
            draw_text(fb, x + 10, ty, line, self.message_color, 1)
            ty += 12
        if self.editor:
            hint = "F TRAVA/DESTRAVA  S SALVA  Q/E GIRA  DEL REMOVE  ESPACO RODA  ESC MENU"
        else:
            hint = "Q/E GIRA  DEL REMOVE  SETAS PAN  +/- ZOOM  ESPACO RODA  ESC MENU  M SOM"
        if self.app.audio.muted:
            hint += " (MUDO)"
        draw_text(fb, x + 10, y + 74, hint[:(C.BOTTOM[2] - 3 * 92 - 30) // 6], C.TEXT_DIM, 1)
        mouse = pygame.mouse.get_pos()
        self.run_button.label = "PARAR" if self.running else "RODAR"
        self.run_button.color = C.BAD if self.running else C.GOOD
        buttons = [self.run_button, self.reset_button, self.menu_button]
        if self.editor:
            buttons.append(self.save_button)
        for b in buttons:
            b.draw(fb, hover=b.hit(mouse))

    def _draw_win(self, fb):
        x, y, w, h = C.MAIN_VP
        bw, bh = 340, 140
        bx, by = x + w // 2 - bw // 2, y + h // 2 - 70
        fill_rect(fb, bx, by, bx + bw, by + bh, {'kind': 'gradient',
                                                  'colors': [(40, 90, 50), (40, 90, 50), (20, 40, 25), (20, 40, 25)]})
        draw_rect_outline(fb, bx, by, bx + bw, by + bh, C.GOOD)
        draw_text_centered(fb, x + w // 2, by + 18, "MISSAO CUMPRIDA!", C.GOOD, 3)
        draw_text_centered(fb, x + w // 2, by + 52, "A BOLA CHEGOU AO BALDE", C.TEXT, 1)
        self.next_button.draw(fb, hover=self.next_button.hit(pygame.mouse.get_pos()))

    def _draw_pause(self, fb):
        x, y, w, h = C.MAIN_VP
        fb[x:x + w, y:y + h] //= 2          # dim the play area
        bx, by = x + w // 2 - 160, self.pause_top
        bh = 60 + len(self.pause_buttons) * 48
        fill_rect(fb, bx, by, bx + 320, by + bh, {'kind': 'flat', 'color': C.PANEL_BG})
        draw_rect_outline(fb, bx, by, bx + 320, by + bh, C.PANEL_BORDER)
        draw_text_centered(fb, x + w // 2, by + 12, "PAUSA", C.ACCENT, 3)
        mouse = pygame.mouse.get_pos()
        for b in self.pause_buttons:
            b.draw(fb, hover=b.hit(mouse))


def _hit(rect, pos):
    x, y, w, h = rect
    return x <= pos[0] < x + w and y <= pos[1] < y + h
