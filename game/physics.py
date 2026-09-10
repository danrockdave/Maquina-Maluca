"""Minimal 2D physics: one ball (circle) against static convex polygons."""
import math

GRAVITY = 900.0
MAX_SPEED = 1500.0
SUBSTEPS = 4
REST_THRESHOLD = 28.0


def closest_point_on_segment(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    l2 = abx * abx + aby * aby
    if l2 == 0.0:
        return ax, ay
    t = ((px - ax) * abx + (py - ay) * aby) / l2
    t = max(0.0, min(1.0, t))
    return ax + t * abx, ay + t * aby


def point_in_polygon(px, py, verts):
    inside = False
    n = len(verts)
    j = n - 1
    for i in range(n):
        xi, yi = verts[i]
        xj, yj = verts[j]
        if (yi > py) != (yj > py):
            x_cross = xi + (py - yi) * (xj - xi) / (yj - yi)
            if px < x_cross:
                inside = not inside
        j = i
    return inside


def collide_ball_shape(ball, shape, part):
    """Resolves penetration and velocity between the ball and one convex polygon.
    Returns the impact speed along the normal (0 when there was no approaching
    contact, None when there was no contact at all)."""
    verts = shape.verts
    n = len(verts)
    r = ball.radius
    best_d2, best_cp, best_edge = None, None, None
    for i in range(n):
        ax, ay = verts[i]
        bx, by = verts[(i + 1) % n]
        cx, cy = closest_point_on_segment(ball.x, ball.y, ax, ay, bx, by)
        d2 = (ball.x - cx) ** 2 + (ball.y - cy) ** 2
        if best_d2 is None or d2 < best_d2:
            best_d2, best_cp, best_edge = d2, (cx, cy), (ax, ay, bx, by)

    inside = point_in_polygon(ball.x, ball.y, verts)
    d = math.sqrt(best_d2)
    if not inside and d >= r:
        return None

    # Outward normal of the nearest edge
    ax, ay, bx, by = best_edge
    ex, ey = bx - ax, by - ay
    el = math.hypot(ex, ey) or 1.0
    nx, ny = -ey / el, ex / el
    cxm = sum(v[0] for v in verts) / n
    cym = sum(v[1] for v in verts) / n
    if (ax - cxm) * nx + (ay - cym) * ny < 0:
        nx, ny = -nx, -ny

    if inside:
        penetration = r + d
    else:
        if d > 1e-6:                        # corners: normal from contact point
            nx, ny = (ball.x - best_cp[0]) / d, (ball.y - best_cp[1]) / d
        penetration = r - d

    ball.x += nx * penetration
    ball.y += ny * penetration

    vn = ball.vx * nx + ball.vy * ny
    impact = -vn if vn < 0.0 else 0.0
    if vn < 0.0:
        jn = -(1.0 + shape.restitution) * vn
        ball.vx += jn * nx
        ball.vy += jn * ny
        vn_after = ball.vx * nx + ball.vy * ny
        if vn_after < REST_THRESHOLD:       # kill tiny bounces so the ball can rest
            ball.vx -= vn_after * nx
            ball.vy -= vn_after * ny

    # Tangential response: friction or conveyor belt drive
    tx, ty = -ny, nx
    vt = ball.vx * tx + ball.vy * ty
    if shape.belt:
        bdx, bdy = math.cos(part.angle), math.sin(part.angle)
        target = shape.belt * (bdx * tx + bdy * ty)
        vt_new = vt + (target - vt) * 0.3
    else:
        vt_new = vt * (1.0 - shape.friction)
    ball.vx += (vt_new - vt) * tx
    ball.vy += (vt_new - vt) * ty
    return impact


def step(ball, parts, dt, on_impact=None):
    """Advances the simulation. on_impact(part, shape, speed) is called once per
    frame with the strongest collision, if any."""
    sub = dt / SUBSTEPS
    colliders = [(p, s) for p in parts if p is not ball for s in p.colliders()]
    strongest = (None, None, 0.0)
    for _ in range(SUBSTEPS):
        ball.vy += GRAVITY * sub
        for part in parts:
            if part is not ball:
                part.apply_field(ball, sub, parts)
        speed = math.hypot(ball.vx, ball.vy)
        if speed > MAX_SPEED:
            ball.vx *= MAX_SPEED / speed
            ball.vy *= MAX_SPEED / speed
        ball.x += ball.vx * sub
        ball.y += ball.vy * sub
        for part, shape in colliders:
            impact = collide_ball_shape(ball, shape, part)
            if impact is None:
                continue
            part.on_contact(ball, impact)
            if impact > strongest[2]:
                strongest = (part, shape, impact)
        ball.angle += ball.vx / ball.radius * sub     # visual rolling
    if on_impact is not None and strongest[0] is not None:
        on_impact(*strongest)
