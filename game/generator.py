"""
Random level generator with guaranteed solvability.

Strategy: build a staircase of planks that carries the ball from a random start
to a random bucket, verify it by running the physics engine, sprinkle obstacles
that do not break the solution, then hide part of the planks in the inventory.
The hidden planks (at their original positions) are always a valid answer.
"""
import math
import random

from game import config as C
from game import physics
from game.parts import Ball, Bucket, Plank, Box, Wall, Trampoline, Fan, Magnet, TNT
from game.levels import Level


def simulate(parts, seconds=12.0):
    """Runs the machine without drawing. Returns True if the ball reaches a bucket."""
    ball = next(p for p in parts if isinstance(p, Ball))
    buckets = [p for p in parts if isinstance(p, Bucket)]
    for p in parts:
        p.reset()
    ball.reset()
    dt = 1.0 / 60.0
    for _ in range(int(seconds * 60)):
        for p in parts:
            p.update(dt)
        physics.step(ball, parts, dt)
        if any(b.goal_reached(ball) for b in buckets):
            _rewind(parts, ball)
            return True
        if ball.y > C.WORLD_H + 150 or ball.x < -300 or ball.x > C.WORLD_W + 300:
            _rewind(parts, ball)
            return False
    _rewind(parts, ball)
    return False


def _rewind(parts, ball):
    for p in parts:
        p.reset()
    ball.reset()


def _staircase(rng, ball, bucket):
    direction = 1 if bucket.x > ball.x else -1
    planks = []
    x = ball.x + direction * rng.randint(30, 70)
    y = ball.y + rng.randint(90, 150)
    while direction * (bucket.x - x) > 150 and y < bucket.y - 70:
        angle = direction * math.radians(rng.randint(10, 30))
        planks.append(Plank(x, y, angle=angle, fixed=True))
        x += direction * rng.randint(120, 175)
        y += rng.randint(85, 140)
    return planks


def _far_from(parts, x, y, margin):
    for p in parts:
        if abs(p.x - x) < margin and abs(p.y - y) < margin:
            return False
    return True


def generate_random_level(seed=None):
    if seed is None:
        seed = random.randrange(1, 100000)
    rng = random.Random(seed)

    for _attempt in range(40):
        left_to_right = rng.random() < 0.5
        bx = rng.randint(80, 260) if left_to_right else rng.randint(940, 1120)
        gx = rng.randint(860, 1110) if left_to_right else rng.randint(90, 340)
        by = rng.randint(60, 150)
        gy = rng.choice([735, 735, 640, 560])
        ball = Ball(bx, by, fixed=True)
        bucket = Bucket(gx, gy, fixed=True)
        parts = [ball, bucket]
        if gy != 735:
            parts.append(Box(gx, gy + 80, fixed=True))
        planks = _staircase(rng, ball, bucket)
        if len(planks) < 2:
            continue
        parts += planks
        if not simulate(parts):
            continue

        # Obstacles that keep the solution valid
        for _ in range(rng.randint(2, 5)):
            cls = rng.choice([Wall, Box, Box, TNT])
            for _try in range(8):
                ox, oy = rng.randint(60, C.WORLD_W - 60), rng.randint(150, C.WORLD_H - 60)
                if _far_from(parts, ox, oy, 120):
                    obstacle = cls(ox, oy, angle=rng.choice([0.0, 0.0, math.radians(rng.randint(-25, 25))]), fixed=True)
                    parts.append(obstacle)
                    if simulate(parts):
                        break
                    parts.remove(obstacle)

        # Hide part of the planks: they become the player's inventory
        hidden = rng.sample(planks, max(1, len(planks) // 2))
        for p in hidden:
            parts.remove(p)
        inventory = {'Plank': len(hidden) + rng.choice([0, 1])}
        extra = rng.choice([Trampoline, Fan, Magnet, None])
        if extra is not None:
            inventory[extra.__name__] = 1
        data = {
            'name': f"ALEATORIA #{seed}",
            'hint': f"FASE GERADA COM A SEMENTE {seed}. HA PELO MENOS UMA SOLUCAO COM AS TABUAS.",
            'parts': [p.to_dict() for p in parts],
            'inventory': inventory,
        }
        return Level.from_dict(data)

    # Extremely unlikely fallback: a trivial level
    data = {'name': f"ALEATORIA #{seed}", 'hint': "USE AS TABUAS COMO RAMPAS.",
            'parts': [Ball(160, 90, fixed=True).to_dict(), Bucket(1000, 735, fixed=True).to_dict()],
            'inventory': {'Plank': 3}}
    return Level.from_dict(data)
