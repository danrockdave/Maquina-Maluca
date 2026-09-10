"""2D geometric transformations with 3x3 homogeneous matrices."""
import math
import numpy as np


def identity():
    return np.eye(3)


def translation(tx, ty):
    return np.array([[1.0, 0.0, tx],
                     [0.0, 1.0, ty],
                     [0.0, 0.0, 1.0]])


def scaling(sx, sy=None):
    if sy is None:
        sy = sx
    return np.array([[sx, 0.0, 0.0],
                     [0.0, sy, 0.0],
                     [0.0, 0.0, 1.0]])


def rotation(theta):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0.0],
                     [s, c, 0.0],
                     [0.0, 0.0, 1.0]])


def rotation_about(theta, cx, cy):
    """Rotation around an arbitrary pivot: T(c) . R . T(-c)."""
    return translation(cx, cy) @ rotation(theta) @ translation(-cx, -cy)


def scaling_about(sx, sy, cx, cy):
    return translation(cx, cy) @ scaling(sx, sy) @ translation(-cx, -cy)


def compose(*matrices):
    m = identity()
    for mat in matrices:
        m = m @ mat
    return m


def apply_to_points(m, points):
    """Applies a 3x3 matrix to a list of (x, y) tuples; returns a list of tuples."""
    if len(points) == 0:
        return []
    pts = np.asarray(points, dtype=float)
    hom = np.hstack([pts, np.ones((pts.shape[0], 1))])
    out = hom @ m.T
    return [(float(p[0]), float(p[1])) for p in out]


def apply_to_point(m, x, y):
    v = m @ np.array([x, y, 1.0])
    return float(v[0]), float(v[1])
