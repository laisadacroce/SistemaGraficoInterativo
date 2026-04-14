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

    def __init__(self, name, points, drawable=True):
        coords = [p.coordinates[0] for p in points]
        super().__init__(name, coords, drawable)

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
