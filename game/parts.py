"""
Game parts. Every part is a set of polygons defined in local coordinates and
placed in the world with a model matrix  T(x, y) . R(angle) . S(scale).
"""
import math
import numpy as np
from gfx.transform import translation, rotation, scaling, compose, apply_to_points, apply_to_point
from gfx.clipping import draw_line_clipped

RECT_UV = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


class Shape:
    """A polygon plus its fill style and physical properties."""
    __slots__ = ('verts', 'style', 'outline', 'solid', 'restitution', 'friction', 'belt')

    def __init__(self, verts, style, outline=None, solid=False,
                 restitution=0.35, friction=0.002, belt=0.0):
        self.verts = verts
        self.style = style
        self.outline = outline
        self.solid = solid
        self.restitution = restitution
        self.friction = friction
        self.belt = belt

    def transformed(self, m):
        return Shape(apply_to_points(m, self.verts), self.style, self.outline,
                     self.solid, self.restitution, self.friction, self.belt)


# ------------------------------------------------------------- helpers
def rect(w, h, cx=0.0, cy=0.0):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def circle_poly(r, n=20, cx=0.0, cy=0.0, phase=0.0):
    return [(cx + r * math.cos(phase + 2 * math.pi * i / n),
             cy + r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]


def flat(color):
    return {'kind': 'flat', 'color': color}


def gradient(colors):
    return {'kind': 'gradient', 'colors': colors}


def texture(name, uvs=None, offset=(0.0, 0.0)):
    return {'kind': 'texture', 'name': name, 'uvs': uvs or RECT_UV, 'offset': offset}


def shade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


def vertical_gradient(top, bottom):
    """Colors for a rect() polygon (top-left, top-right, bottom-right, bottom-left)."""
    return [top, top, bottom, bottom]


# ------------------------------------------------------------- base part
class Part:
    label = "PECA"
    hint = ""
    rotatable = True
    animated = False      # True when the part changes appearance every frame

    def __init__(self, x, y, angle=0.0, fixed=False):
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)
        self.scale = 1.0
        self.fixed = fixed
        self.time = 0.0

    # --- transforms
    def model_matrix(self):
        return compose(translation(self.x, self.y), rotation(self.angle),
                       scaling(self.scale, self.scale))

    def to_local(self, wx, wy):
        return apply_to_point(np.linalg.inv(self.model_matrix()), wx, wy)

    # --- geometry
    def local_shapes(self):
        raise NotImplementedError

    def world_shapes(self):
        m = self.model_matrix()
        return [s.transformed(m) for s in self.local_shapes()]

    def colliders(self):
        return [s for s in self.world_shapes() if s.solid]

    def local_bounds(self):
        xs, ys = [], []
        for s in self.local_shapes():
            xs.extend(v[0] for v in s.verts)
            ys.extend(v[1] for v in s.verts)
        return min(xs), min(ys), max(xs), max(ys)

    def contains(self, wx, wy):
        lx, ly = self.to_local(wx, wy)
        x0, y0, x1, y1 = self.local_bounds()
        pad = 4.0
        return x0 - pad <= lx <= x1 + pad and y0 - pad <= ly <= y1 + pad

    # --- behaviour
    def update(self, dt):
        self.time += dt

    def apply_field(self, ball, dt, parts):
        """Called every physics substep (forces that act at a distance)."""
        pass

    def on_contact(self, ball, impact):
        """Called when the ball touches one of this part's solid shapes."""
        pass

    def reset(self):
        """Restores the state the part had before the simulation started."""
        pass

    def extra_draw(self, fb, camera):
        pass

    def rotate(self, delta):
        if self.rotatable:
            self.angle += delta

    # --- serialization (level editor / random levels)
    def to_dict(self):
        data = {'type': type(self).__name__, 'x': round(self.x, 1), 'y': round(self.y, 1),
                'angle': round(self.angle, 4), 'fixed': self.fixed}
        if hasattr(self, 'channel'):
            data['channel'] = self.channel
        return data


# ------------------------------------------------------------- parts
class Ball(Part):
    label = "BOLA"
    hint = "A BOLA. ELA PRECISA CHEGAR AO BALDE."
    rotatable = False

    def __init__(self, x, y, angle=0.0, fixed=False):
        super().__init__(x, y, angle, fixed)
        self.radius = 16.0
        self.vx = 0.0
        self.vy = 0.0
        self.start = (self.x, self.y)
        self.base_color = (222, 52, 52)
        self._shapes = self._build()

    def _build(self):
        n = 24
        verts = circle_poly(self.radius, n)
        colors = []
        for i in range(n):
            a = 2 * math.pi * i / n
            k = 0.55 + 0.5 * math.cos(a + 3 * math.pi / 4)   # light from top-left
            colors.append(shade(self.base_color, 0.45 + 0.75 * k))
        spot = circle_poly(3.5, 8, cx=self.radius * 0.45, cy=0.0)
        return [Shape(verts, gradient(colors), outline=(70, 12, 12)),
                Shape(spot, flat((255, 245, 230)))]

    def local_shapes(self):
        return self._shapes

    def reset(self):
        self.x, self.y = self.start
        self.vx = self.vy = 0.0
        self.angle = 0.0

    def contains(self, wx, wy):
        return math.hypot(wx - self.x, wy - self.y) <= self.radius + 4


class Plank(Part):
    label = "TABUA"
    hint = "TABUA DE MADEIRA. GIRE COM Q/E PARA FAZER RAMPAS."

    W, H = 180.0, 16.0

    def local_shapes(self):
        return [Shape(rect(self.W, self.H), texture('wood'), outline=(80, 50, 22),
                      solid=True, restitution=0.3)]


class Wall(Part):
    label = "MURO"
    hint = "MURO DE TIJOLOS. OBSTACULO SOLIDO."

    W, H = 60.0, 200.0

    def local_shapes(self):
        return [Shape(rect(self.W, self.H), texture('brick', uvs=[(0, 0), (1, 0), (1, 3), (0, 3)]),
                      outline=(90, 40, 30), solid=True, restitution=0.3)]


class Box(Part):
    label = "CAIXA"
    hint = "CAIXA DE PAPELAO. DEGRAU OU OBSTACULO."

    W, H = 70.0, 70.0

    def local_shapes(self):
        body = Shape(rect(self.W, self.H), texture('cardboard'), outline=(120, 90, 50),
                     solid=True, restitution=0.25)
        tape = Shape(rect(self.W, 10, 0, 0), flat((150, 120, 80)))
        return [body, tape]


class Trampoline(Part):
    label = "TRAMPOLIM"
    hint = "TRAMPOLIM. A BOLA QUICA MAIS ALTO A CADA PULO."

    W, H = 120.0, 14.0

    def local_shapes(self):
        pad = Shape(rect(self.W, self.H), gradient(vertical_gradient((120, 125, 150), (40, 42, 55))),
                    outline=(20, 20, 30), solid=True, restitution=1.12, friction=0.0)
        leg_l = Shape(rect(8, 24, -self.W / 2 + 12, self.H / 2 + 12), flat((120, 120, 130)),
                      outline=(60, 60, 70))
        leg_r = Shape(rect(8, 24, self.W / 2 - 12, self.H / 2 + 12), flat((120, 120, 130)),
                      outline=(60, 60, 70))
        return [leg_l, leg_r, pad]


class Conveyor(Part):
    label = "ESTEIRA"
    hint = "ESTEIRA ROLANTE. EMPURRA A BOLA NA DIRECAO DA SETA."

    animated = True
    W, H = 200.0, 24.0
    SPEED = 240.0

    def __init__(self, x, y, angle=0.0, fixed=False):
        super().__init__(x, y, angle, fixed)
        self.offset = 0.0

    def update(self, dt):
        super().update(dt)
        # Texture scrolling animation: u offset in texture space
        self.offset = (self.offset - self.SPEED / self.W * dt) % 1.0

    def local_shapes(self):
        belt = Shape(rect(self.W, self.H), texture('belt', uvs=[(0, 0), (3, 0), (3, 1), (0, 1)],
                                                      offset=(self.offset, 0.0)),
                     outline=(30, 30, 34), solid=True, restitution=0.15, belt=self.SPEED)
        frame = Shape(rect(self.W + 10, 8, 0, self.H / 2 + 4), texture('metal'),
                      outline=(60, 60, 70))
        return [frame, belt]

    def extra_draw(self, fb, camera):
        m = self.model_matrix()
        for lx in (-self.W / 2, self.W / 2):
            wx, wy = apply_to_point(m, lx, 0.0)
            camera.draw_circle_world(fb, wx, wy, self.H / 2 + 2, (200, 200, 210))
            camera.draw_circle_world(fb, wx, wy, 4, (200, 200, 210))


class Fan(Part):
    label = "VENTILADOR"
    hint = "VENTILADOR. SOPRA A BOLA. GIRE PARA MUDAR A DIRECAO."

    animated = True
    FORCE = 1500.0
    REACH = 420.0
    HALF_WIDTH = 80.0

    def __init__(self, x, y, angle=0.0, fixed=False):
        super().__init__(x, y, angle, fixed)
        self.blade_angle = 0.0

    def update(self, dt):
        super().update(dt)
        self.blade_angle += 14.0 * dt     # rotation animation

    def local_shapes(self):
        base = Shape(rect(44, 74, -8, 0), texture('metal'), outline=(60, 62, 70),
                     solid=True, restitution=0.3)
        foot = Shape(rect(56, 8, -8, 41), flat((70, 72, 80)), outline=(40, 40, 46))
        shapes = [foot, base]
        hub = (34.0, 0.0)
        for i in range(3):
            m = compose(translation(*hub), rotation(self.blade_angle + i * 2 * math.pi / 3))
            blade = apply_to_points(m, rect(8, 62, 0, -16))
            colors = [(235, 235, 245), (200, 205, 220), (120, 125, 145), (150, 155, 175)]
            shapes.append(Shape(blade, gradient(colors), outline=(70, 72, 84)))
        shapes.append(Shape(circle_poly(6, 10, hub[0], hub[1]), flat((50, 50, 58))))
        return shapes

    def extra_draw(self, fb, camera):
        m = self.model_matrix()
        hx, hy = apply_to_point(m, 34.0, 0.0)
        camera.draw_circle_world(fb, hx, hy, 40, (90, 92, 104))
        # animated wind lines (translation animation)
        phase = (self.time * 260.0) % 60.0
        for ly in (-50.0, 0.0, 50.0):
            lx = 80.0 + phase
            while lx < self.REACH:
                x0, y0 = apply_to_point(m, lx, ly)
                x1, y1 = apply_to_point(m, min(lx + 24.0, self.REACH), ly)
                camera.draw_line_world(fb, x0, y0, x1, y1, (170, 205, 245))
                lx += 60.0

    def apply_field(self, ball, dt, parts):
        lx, ly = self.to_local(ball.x, ball.y)
        if 60.0 <= lx <= self.REACH and abs(ly) <= self.HALF_WIDTH:
            strength = 1.0 - 0.55 * (lx - 60.0) / (self.REACH - 60.0)
            ball.vx += math.cos(self.angle) * self.FORCE * strength * dt
            ball.vy += math.sin(self.angle) * self.FORCE * strength * dt


class Bucket(Part):
    label = "BALDE"
    hint = "O BALDE. OBJETIVO: COLOCAR A BOLA AQUI DENTRO."
    rotatable = False

    W, H, T = 110.0, 90.0, 10.0

    def local_shapes(self):
        w, h, t = self.W, self.H, self.T
        light, dark = (120, 170, 235), (35, 70, 130)
        left = Shape(rect(t, h, -w / 2 + t / 2, 0), gradient([light, light, dark, dark]),
                     outline=(20, 40, 80), solid=True, restitution=0.2)
        right = Shape(rect(t, h, w / 2 - t / 2, 0), gradient([dark, dark, light, light]),
                      outline=(20, 40, 80), solid=True, restitution=0.2)
        bottom = Shape(rect(w, t, 0, h / 2 - t / 2), gradient([dark, light, light, dark]),
                       outline=(20, 40, 80), solid=True, restitution=0.2)
        band = Shape(rect(w, 6, 0, -h / 2 + 12), flat((240, 200, 60)))
        return [left, right, bottom, band]

    def extra_draw(self, fb, camera):
        camera.draw_ellipse_world(fb, self.x, self.y - self.H / 2, self.W / 2 + 2, 7, (200, 220, 250))

    def goal_reached(self, ball):
        lx, ly = self.to_local(ball.x, ball.y)
        inner_w = self.W / 2 - self.T - ball.radius * 0.5
        return abs(lx) < inner_w and -self.H / 2 + 18 < ly < self.H / 2


class Portal(Part):
    label = "PORTAL"
    hint = "PORTAL. A BOLA ENTRA EM UM E SAI NO OUTRO DA MESMA COR."
    rotatable = False
    animated = True

    COLORS = [(255, 130, 40), (60, 200, 255), (200, 90, 255)]
    R = 30.0
    COOLDOWN = 0.6

    def __init__(self, x, y, angle=0.0, fixed=False, channel=0):
        super().__init__(x, y, angle, fixed)
        self.channel = channel
        self.cooldown = 0.0

    @property
    def color(self):
        return self.COLORS[self.channel % len(self.COLORS)]

    def update(self, dt):
        super().update(dt)
        self.cooldown = max(0.0, self.cooldown - dt)

    def reset(self):
        self.cooldown = 0.0

    def local_shapes(self):
        n = 20
        outer = circle_poly(self.R, n, phase=self.time * 2.0)
        light = tuple(min(255, c + 70) for c in self.color)
        dark = tuple(int(c * 0.45) for c in self.color)
        colors = [light if i % 4 < 2 else dark for i in range(n)]
        inner = circle_poly(self.R - 9, 16)
        return [Shape(outer, gradient(colors), outline=dark),
                Shape(inner, gradient([(20, 20, 40)] * 8 + [dark] * 8))]

    def extra_draw(self, fb, camera):
        squeeze = abs(math.cos(self.time * 1.5))
        camera.draw_ellipse_world(fb, self.x, self.y, self.R + 6, (self.R + 6) * (0.3 + 0.7 * squeeze), self.color)

    def partner(self, parts):
        for p in parts:
            if p is not self and isinstance(p, Portal) and p.channel == self.channel:
                return p
        return None

    def apply_field(self, ball, dt, parts):
        if self.cooldown > 0.0:
            return
        if math.hypot(ball.x - self.x, ball.y - self.y) > self.R - 8:
            return
        other = self.partner(parts)
        if other is None:
            return
        speed = math.hypot(ball.vx, ball.vy)
        if speed < 1e-3:
            dx, dy = 0.0, 1.0
        else:
            dx, dy = ball.vx / speed, ball.vy / speed
        offset = self.R + ball.radius + 2.0
        ball.x = other.x + dx * offset
        ball.y = other.y + dy * offset
        self.cooldown = other.cooldown = self.COOLDOWN


class Magnet(Part):
    label = "IMA"
    hint = "IMA. ATRAI A BOLA E CURVA A TRAJETORIA DELA."
    rotatable = False
    animated = True

    RADIUS = 240.0
    FORCE = 1400.0

    def local_shapes(self):
        n = 16
        red, grey = (220, 60, 60), (200, 200, 210)
        outer = circle_poly(22, n)
        colors = [red if i % 2 == 0 else (150, 30, 30) for i in range(n)]
        core = circle_poly(9, 10)
        return [Shape(outer, gradient(colors), outline=(90, 20, 20)),
                Shape(core, flat(grey), outline=(120, 120, 130))]

    def extra_draw(self, fb, camera):
        # Pulsing field rings (a scale animation drawn with the circle rasterizer)
        for k in range(3):
            r = (self.time * 70.0 + k * self.RADIUS / 3.0) % self.RADIUS
            fade = int(120 * (1.0 - r / self.RADIUS))
            camera.draw_circle_world(fb, self.x, self.y, r, (255, 160 + fade // 2, 160 + fade // 2))

    def apply_field(self, ball, dt, parts):
        dx, dy = self.x - ball.x, self.y - ball.y
        d = math.hypot(dx, dy)
        if 24.0 < d < self.RADIUS:
            a = self.FORCE * (1.0 - d / self.RADIUS) + 250.0
            ball.vx += dx / d * a * dt
            ball.vy += dy / d * a * dt


class TNT(Part):
    label = "DINAMITE"
    hint = "DINAMITE. EXPLODE AO TOQUE E LANCA A BOLA PARA LONGE."
    animated = True

    W, H = 40.0, 56.0
    BLAST = 950.0

    def __init__(self, x, y, angle=0.0, fixed=False):
        super().__init__(x, y, angle, fixed)
        self.exploded = False
        self.boom_time = 0.0
        self.just_exploded = False

    def update(self, dt):
        super().update(dt)
        if self.exploded:
            self.boom_time += dt

    def reset(self):
        self.exploded = False
        self.boom_time = 0.0
        self.just_exploded = False

    def local_shapes(self):
        if self.exploded:
            if self.boom_time > 0.7:
                return []
            # Explosion star scaled up over time (scale transform animation)
            s = 0.5 + 3.5 * min(1.0, self.boom_time * 2.5)
            star = []
            for i in range(16):
                a = 2 * math.pi * i / 16
                r = 26 if i % 2 == 0 else 12
                star.append((r * math.cos(a), r * math.sin(a)))
            star = apply_to_points(compose(scaling(s, s), rotation(self.boom_time * 3.0)), star)
            fade = max(0.0, 1.0 - self.boom_time / 0.7)
            hot = shade((255, 240, 120), fade)
            cool = shade((230, 70, 20), fade)
            return [Shape(star, gradient([hot if i % 2 == 0 else cool for i in range(16)]))]
        body = Shape(rect(self.W, self.H), gradient([(230, 60, 50), (250, 110, 90), (150, 30, 25), (200, 50, 40)]),
                     outline=(70, 15, 10), solid=True, restitution=0.3)
        band1 = Shape(rect(self.W, 6, 0, -14), flat((240, 220, 120)))
        band2 = Shape(rect(self.W, 6, 0, 14), flat((240, 220, 120)))
        return [body, band1, band2]

    def extra_draw(self, fb, camera):
        if self.exploded:
            return
        m = self.model_matrix()
        x0, y0 = apply_to_point(m, 0.0, -self.H / 2)
        x1, y1 = apply_to_point(m, 6.0, -self.H / 2 - 14.0)
        camera.draw_line_world(fb, x0, y0, x1, y1, (60, 40, 30))
        spark = 2.0 + 2.0 * abs(math.sin(self.time * 12.0))
        camera.draw_circle_world(fb, x1, y1, spark, (255, 200, 60))

    def on_contact(self, ball, impact):
        if self.exploded:
            return
        self.exploded = True
        self.just_exploded = True
        dx, dy = ball.x - self.x, ball.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ball.vx = dx / d * self.BLAST
        ball.vy = min(dy / d * self.BLAST, -250.0) - 250.0


PLACEABLE = [Plank, Trampoline, Fan, Conveyor, Box, Wall, Portal, Magnet, TNT]
PART_TYPES = {cls.__name__: cls for cls in PLACEABLE + [Ball, Bucket]}


def part_from_dict(data):
    cls = PART_TYPES[data['type']]
    kwargs = {'angle': data.get('angle', 0.0), 'fixed': data.get('fixed', False)}
    if cls is Portal:
        kwargs['channel'] = data.get('channel', 0)
    return cls(data['x'], data['y'], **kwargs)
