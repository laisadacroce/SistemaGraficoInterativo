import math


# ── Transformation matrices ──────────────────────────────

def identity_matrix():
    """Returns the 3x3 identity matrix. Multiplying any point by this
    matrix returns the same point — it's the starting value for
    composing transformations (like 0 for addition or 1 for multiplication)."""
    return [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
    ]


def translation_matrix(dx, dy):
    """Returns a 3x3 matrix that translates (shifts) a point by (dx, dy).

    The point is a row vector [x, y, 1] multiplied on the left:
      [x', y', 1] = [x, y, 1] * matrix
    The translation values go in the bottom row."""
    return [
        [1,  0,  0],
        [0,  1,  0],
        [dx, dy, 1],
    ]


def scaling_matrix(sx, sy):
    """Returns a 3x3 matrix that scales a point by factors (sx, sy).

    This scales relative to the origin (0,0). For 'natural' scaling
    around the object's center, use natural_scaling_matrix() instead."""
    return [
        [sx, 0,  0],
        [0,  sy, 0],
        [0,  0,  1],
    ]


def rotation_matrix(angle_degrees):
    """Returns a 3x3 matrix that rotates a point by the given angle
    around the origin (0,0).

    The angle is in degrees (converted to radians internally) because
    degrees are more intuitive for the user. Positive angles rotate
    counter-clockwise, following the standard math convention."""
    rad = math.radians(angle_degrees)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return [
        [ cos, sin, 0],
        [-sin, cos, 0],
        [ 0,   0,   1],
    ]


# ── Matrix operations ────────────────────────────────────

def multiply_matrices(m1, m2):
    """Multiplies two 3x3 matrices and returns the result.

    This is the core operation for composing transformations — multiplying
    two transformation matrices produces a single matrix that has the
    combined effect of both."""
    result = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                result[i][j] += m1[i][k] * m2[k][j]
    return result


def compose_matrices(matrices):
    """Composes a list of transformation matrices into a single matrix.

    Multiplies them left to right, so the first matrix in the list is
    applied first."""
    result = identity_matrix()
    for m in matrices:
        result = multiply_matrices(result, m)
    return result


# ── Composite transformations ────────────────────────────

def rotation_around_point_matrix(angle_degrees, px, py):
    """Returns a matrix that rotates around an arbitrary point (px, py).

    This requires three steps:
    1. Translate the point to the origin
    2. Rotate
    3. Translate back

    The three matrices are composed into one."""
    return compose_matrices([
        translation_matrix(-px, -py),
        rotation_matrix(angle_degrees),
        translation_matrix(px, py),
    ])


def rotation_around_center_matrix(angle_degrees, obj):
    """Returns a matrix that rotates an object around its own center.

    This is the 'natural' rotation — the object spins in place. Uses
    the object's center() method to find the geometric center."""
    cx, cy = obj.center()
    return rotation_around_point_matrix(angle_degrees, cx, cy)


def natural_scaling_matrix(sx, sy, obj):
    """Returns a matrix that scales an object around its own center.

    Without this, scaling would move the object toward/away from the
    origin. By translating the center to the origin first, the object
    'inflates' or 'shrinks' in place."""
    cx, cy = obj.center()
    return compose_matrices([
        translation_matrix(-cx, -cy),
        scaling_matrix(sx, sy),
        translation_matrix(cx, cy),
    ])


# ── Apply transformation ─────────────────────────────────

def apply_transform(obj, matrix):
    """Applies a transformation matrix to all coordinates of an object.

    This is the generic 'engine': it takes any 3x3 matrix and 
    any object, and transforms every point. It doesn't
    need to know which transformation the matrix represents.

    For each point (x, y), it computes:
      [x', y', 1] = [x, y, 1] * matrix
    """
    new_coords = []
    for x, y in obj.coordinates:
        # Multiply the row vector [x, y, 1] by the matrix
        x_new = x * matrix[0][0] + y * matrix[1][0] + 1 * matrix[2][0]
        y_new = x * matrix[0][1] + y * matrix[1][1] + 1 * matrix[2][1]
        new_coords.append((x_new, y_new))
    obj.coordinates = new_coords


# ── Viewport transformation ──────────────────────────────

def window_to_viewport(x_w, y_w, window, viewport):
    """
    Transforms a point from window (world) coordinates to viewport (screen) coordinates.

    window:   (x_min, y_min, x_max, y_max) — the world rectangle we're looking at.
    viewport: (x_min, y_min, x_max, y_max) — the screen rectangle we draw into.

    Uses uniform scaling to avoid distortion.
    """
    wx_min, wy_min, wx_max, wy_max = window
    vx_min, vy_min, vx_max, vy_max = viewport

    # Scale factors for x and y
    sx = (vx_max - vx_min) / (wx_max - wx_min)
    sy = (vy_max - vy_min) / (wy_max - wy_min)

    # Use the smaller scale factor to maintain aspect ratio
    s = min(sx, sy)

    # Center the result in the viewport (the axis with leftover space gets centered)
    used_width = (wx_max - wx_min) * s
    used_height = (wy_max - wy_min) * s
    offset_x = vx_min + ((vx_max - vx_min) - used_width) / 2
    offset_y = vy_min + ((vy_max - vy_min) - used_height) / 2

    x_vp = (x_w - wx_min) * s + offset_x
    y_vp = (wy_max - y_w) * s + offset_y
    return x_vp, y_vp