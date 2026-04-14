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


# ── SCN (Normalized Coordinate System) ───────────────────

def scn_matrix(window):
    """Generates the matrix that transforms world coordinates to SCN.

    Implements the 'Gerar Descrição em SCN' algorithm:
    1. Translate window center (Wc) to the origin
    2. Rotate by -angle to align Vup with the Y axis
    3. Scale to normalize into [-1, 1] range

    The result is a single composed matrix."""
    cx, cy = window.center()
    w = window.width()
    h = window.height()
    return compose_matrices([
        translation_matrix(-cx, -cy),
        rotation_matrix(-window.angle),
        scaling_matrix(2 / w, 2 / h),
    ])


# ── Viewport transformation ──────────────────────────────

def scn_to_viewport(x_scn, y_scn, viewport):
    """Transforms a point from SCN coordinates [-1, 1] to viewport (screen)
    coordinates.

    The SCN window is always fixed at [-1, -1, 1, 1]."""
    vx_min, vy_min, vx_max, vy_max = viewport

    # Map from [-1, 1] to viewport range
    x_vp = (x_scn + 1) / 2 * (vx_max - vx_min) + vx_min
    # Y is inverted: SCN +1 (top) maps to viewport vy_min (top of screen)
    y_vp = (1 - y_scn) / 2 * (vy_max - vy_min) + vy_min

    return x_vp, y_vp


