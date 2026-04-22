import math


class GraphicObject:
    """Base class for all graphic objects. Subclasses must implement
    object_type and draw_segments."""

    def __init__(self, name, coordinates, drawable=True, color="#000000"):
        self.name = name
        self.coordinates = coordinates  # list of (x, y) tuples in world coords
        self.drawable = drawable
        self.color = color  # RGB hex color for drawing
        self.normalized_coords = []  # SCN cache, computed by DisplayFile.update_scn()

    @property
    def object_type(self):
        raise NotImplementedError

    def draw_segments(self):
        """Returns a list of ((x1,y1), (x2,y2)) pairs to be drawn as lines."""
        raise NotImplementedError

    def draw_segments_scn(self):
        """Same as draw_segments but using normalized coordinates."""
        raise NotImplementedError

    def center(self):
        """Returns the geometric center (cx, cy) of the object.

        This is the average of all coordinates.
        Used by rotation and scaling to transform 'naturally' around
        the object's center instead of around the origin."""
        n = len(self.coordinates)
        cx = sum(x for x, y in self.coordinates) / n
        cy = sum(y for x, y in self.coordinates) / n
        return (cx, cy)

    def __str__(self):
        return f"{self.object_type.capitalize()}[{self.name}]"


class Point(GraphicObject):
    """A single point in 2D space."""

    def __init__(self, name, x, y):
        super().__init__(name, [(x, y)])

    @property
    def object_type(self):
        return "point"

    def draw_segments(self):
        return []  # points are drawn as small circles, not segments

    def draw_segments_scn(self):
        return []


class Line(GraphicObject):
    """A line segment defined by two points."""

    def __init__(self, name, p1, p2):
        super().__init__(name, [p1.coordinates[0], p2.coordinates[0]])

    @property
    def object_type(self):
        return "line"

    def draw_segments(self):
        return [(self.coordinates[0], self.coordinates[1])]

    def draw_segments_scn(self):
        if len(self.normalized_coords) >= 2:
            return [(self.normalized_coords[0], self.normalized_coords[1])]
        return []


class Wireframe(GraphicObject):
    """A closed polygon defined by a list of connected points."""

    def __init__(self, name, points, drawable=True, filled=False):
        coords = [p.coordinates[0] for p in points]
        super().__init__(name, coords, drawable)
        self.filled = filled

    @property
    def object_type(self):
        return "wireframe"

    def draw_segments(self):
        """Connects each point to the next. The modulo (%) wraps the last
        index back to 0, closing the polygon."""
        segments = []
        for i in range(len(self.coordinates)):
            p1 = self.coordinates[i]
            p2 = self.coordinates[(i + 1) % len(self.coordinates)]
            segments.append((p1, p2))
        return segments

    def draw_segments_scn(self):
        """Same as draw_segments but using normalized coordinates."""
        segments = []
        for i in range(len(self.normalized_coords)):
            p1 = self.normalized_coords[i]
            p2 = self.normalized_coords[(i + 1) % len(self.normalized_coords)]
            segments.append((p1, p2))
        return segments


class Curve2D(GraphicObject):
    """Curva 2D formada por uma ou mais curvas cúbicas de Bézier
    encadeadas com continuidade G(0).

    Estrutura dos pontos de controle:
      - 4 pontos       → 1 curva  (P1, P2, P3, P4)
      - 7 pontos       → 2 curvas (P1..P4, P4..P7)
      - 3k + 1 pontos  → k curvas encadeadas compartilhando extremos

    Cada curva cúbica é avaliada discretizando t em STEPS passos e
    calculando P(t) = T * M_B * G_B para cada um, conforme Eq. 5.21/5.22.
    A continuidade G(0) vem naturalmente da sobreposição do último ponto
    de uma curva com o primeiro da próxima."""

    STEPS = 100  # número de amostras por curva cúbica

    # Matriz de Bézier (M_B) conforme Eq. 5.22 dos slides
    M_B = [
        [-1,  3, -3, 1],
        [ 3, -6,  3, 0],
        [-3,  3,  0, 0],
        [ 1,  0,  0, 0],
    ]

    def __init__(self, name, points, drawable=True):
        coords = [p.coordinates[0] for p in points]
        super().__init__(name, coords, drawable)

    @property
    def object_type(self):
        return "curve"

    @staticmethod
    def valid_point_count(n):
        """Retorna True se n é um número válido de pontos de controle:
        n >= 4 e n ≡ 1 (mod 3)."""
        return n >= 4 and (n - 1) % 3 == 0

    def _generate_curve_points(self, control_coords):
        """Percorre cada grupo de 4 pontos (compartilhando o último com
        o próximo grupo) e gera os pontos discretizados da curva."""
        all_points = []
        n = len(control_coords)
        if not self.valid_point_count(n):
            return all_points

        for i in range(0, n - 3, 3):
            p1, p2, p3, p4 = control_coords[i:i + 4]
            segment = self._bezier_segment(p1, p2, p3, p4)
            # Evitar duplicar o ponto de junção entre curvas consecutivas
            if all_points:
                segment = segment[1:]
            all_points.extend(segment)
        return all_points

    def _bezier_segment(self, p1, p2, p3, p4):
        """Gera STEPS+1 pontos discretizados de uma única curva cúbica."""
        points = []
        for i in range(self.STEPS + 1):
            t = i / self.STEPS
            points.append(self._bezier_point(t, p1, p2, p3, p4))
        return points

    def _bezier_point(self, t, p1, p2, p3, p4):
        """Calcula (x, y) do ponto na curva de Bézier no parâmetro t,
        aplicando P(t) = T * M_B * G_B para as coordenadas x e y
        separadamente (Eq. 5.21/5.22 dos slides).

        O produto T * M_B resulta nas 4 blending functions de Bézier
        (polinômios de Bernstein):
          b0(t) = (1-t)^3
          b1(t) = 3t(1-t)^2
          b2(t) = 3t^2(1-t)
          b3(t) = t^3
        O ponto final é a combinação linear dos pontos de controle
        ponderada pelas blending functions."""
        one_minus_t = 1 - t
        b0 = one_minus_t ** 3
        b1 = 3 * t * one_minus_t ** 2
        b2 = 3 * t ** 2 * one_minus_t
        b3 = t ** 3

        x = b0 * p1[0] + b1 * p2[0] + b2 * p3[0] + b3 * p4[0]
        y = b0 * p1[1] + b1 * p2[1] + b2 * p3[1] + b3 * p4[1]
        return (x, y)

    def draw_segments(self):
        """Gera segmentos de reta conectando pontos consecutivos da curva
        em coordenadas do mundo, baseados nos pontos de controle atuais."""
        curve_pts = self._generate_curve_points(self.coordinates)
        segments = []
        for i in range(len(curve_pts) - 1):
            segments.append((curve_pts[i], curve_pts[i + 1]))
        return segments

    def draw_segments_scn(self):
        """Gera segmentos de reta conectando pontos consecutivos da curva
        em coordenadas SCN. Como transformações afins (incluindo SCN) são
        preservadas pelas blending functions, aplicamos o pipeline sobre
        os pontos de controle normalizados."""
        curve_pts = self._generate_curve_points(self.normalized_coords)
        segments = []
        for i in range(len(curve_pts) - 1):
            segments.append((curve_pts[i], curve_pts[i + 1]))
        return segments

    def curve_points_scn(self):
        """Retorna a lista de pontos discretizados da curva em SCN.
        Usado pelo clipping de curvas (point clipping em cada amostra)."""
        return self._generate_curve_points(self.normalized_coords)


class Window(GraphicObject):
    """The visible region of the world. Lives in the display file as the
    first element (drawable=False) so that transformations can be applied
    to it just like any other object.

    The window has a view-up vector (vup) that defines which direction
    is 'up' from the user's perspective. When the window rotates, vup
    changes, and pan directions follow it."""

    def __init__(self, x_min, y_min, x_max, y_max):
        coords = [(x_min, y_min), (x_max, y_min),
                   (x_max, y_max), (x_min, y_max)]
        super().__init__("window", coords, drawable=False)
        self._initial_coords = list(coords)
        self.angle = 0  # accumulated rotation angle in degrees
        self.vup = (0, 1)  # view-up vector, starts pointing up (+Y)

    @property
    def object_type(self):
        return "window"

    def draw_segments(self):
        return []

    def draw_segments_scn(self):
        return []

    def bounds(self):
        """Returns (x_min, y_min, x_max, y_max) from the corner coordinates."""
        xs = [c[0] for c in self.coordinates]
        ys = [c[1] for c in self.coordinates]
        return (min(xs), min(ys), max(xs), max(ys))

    def width(self):
        x_min, y_min, x_max, y_max = self.bounds()
        return x_max - x_min

    def height(self):
        x_min, y_min, x_max, y_max = self.bounds()
        return y_max - y_min

    def _set_bounds(self, x_min, y_min, x_max, y_max):
        self.coordinates = [(x_min, y_min), (x_max, y_min),
                            (x_max, y_max), (x_min, y_max)]

    def pan(self, dx, dy, step):
        """Shifts the window in the direction relative to the current vup.

        When the window is rotated, 'up' is no longer +Y. The vup vector
        and its perpendicular define the actual up/right directions."""
        x_min, y_min, x_max, y_max = self.bounds()
        width = x_max - x_min
        height = y_max - y_min

        # vup is the 'up' direction, vright is perpendicular (90° clockwise)
        vup_x, vup_y = self.vup
        vright_x, vright_y = vup_y, -vup_x

        # dx controls right/left, dy controls up/down, both relative to view
        offset_x = (dx * vright_x + dy * vup_x) * width * step
        offset_y = (dx * vright_y + dy * vup_y) * height * step

        self._set_bounds(x_min + offset_x, y_min + offset_y,
                         x_max + offset_x, y_max + offset_y)

    def zoom(self, factor, step):
        """Resizes the window around its center. factor=1 zooms in
        (shrinks window), factor=-1 zooms out (expands window)."""
        x_min, y_min, x_max, y_max = self.bounds()
        width = x_max - x_min
        height = y_max - y_min
        cx = (x_min + x_max) / 2
        cy = (y_min + y_max) / 2
        new_width = width * (1 - factor * step)
        new_height = height * (1 - factor * step)
        self._set_bounds(cx - new_width / 2, cy - new_height / 2,
                         cx + new_width / 2, cy + new_height / 2)

    def rotate(self, angle_degrees):
        """Rotates the window by the given angle. Updates the vup vector
        so that pan directions follow the rotation."""
        self.angle += angle_degrees
        rad = math.radians(angle_degrees)
        cos = math.cos(rad)
        sin = math.sin(rad)
        vx, vy = self.vup
        self.vup = (vx * cos - vy * sin, vx * sin + vy * cos)

    def reset(self):
        """Restores the window to its initial coordinates and rotation."""
        self.coordinates = list(self._initial_coords)
        self.angle = 0
        self.vup = (0, 1)


class DisplayFile:
    """Manages the collection of graphic objects. The window is always
    the first element and cannot be removed."""

    def __init__(self, window):
        self.window = window
        self._objects = [window]

    def add(self, obj):
        self._objects.append(obj)

    def remove(self, name):
        # 'is' checks identity (same object in memory), ensuring
        # the window is never removed even if name matches
        self._objects = [o for o in self._objects if o.name != name or o is self.window]

    def get_by_name(self, name):
        """Returns the object with the given name, or None."""
        for obj in self._objects:
            if obj.name == name:
                return obj
        return None

    def has_name(self, name):
        return any(obj.name == name for obj in self._objects)

    def drawable_objects(self):
        """Returns only objects that should be drawn (excludes the window)."""
        return [obj for obj in self._objects if obj.drawable]

    def update_scn(self, scn_matrix_func):
        """Recalculates normalized (SCN) coordinates for all drawable objects.

        Receives a function that generates the SCN matrix from the window,
        keeping model.py independent of transform.py."""
        matrix = scn_matrix_func(self.window)
        for obj in self.drawable_objects():
            new_coords = []
            for x, y in obj.coordinates:
                x_new = x * matrix[0][0] + y * matrix[1][0] + 1 * matrix[2][0]
                y_new = x * matrix[0][1] + y * matrix[1][1] + 1 * matrix[2][1]
                new_coords.append((x_new, y_new))
            obj.normalized_coords = new_coords

    def __iter__(self):
        return iter(self._objects)
