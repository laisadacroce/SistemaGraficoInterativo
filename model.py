class GraphicObject:
    """Base class for all graphic objects. Subclasses must implement
    object_type and draw_segments."""

    def __init__(self, name, coordinates, drawable=True, color="#000000"):
        self.name = name
        self.coordinates = coordinates  # list of (x, y) tuples
        self.drawable = drawable
        self.color = color  # RGB hex color for drawing

    @property
    def object_type(self):
        raise NotImplementedError

    def draw_segments(self):
        """Returns a list of ((x1,y1), (x2,y2)) pairs to be drawn as lines."""
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


class Line(GraphicObject):
    """A line segment defined by two points."""

    def __init__(self, name, p1, p2):
        super().__init__(name, [p1.coordinates[0], p2.coordinates[0]])

    @property
    def object_type(self):
        return "line"

    def draw_segments(self):
        return [(self.coordinates[0], self.coordinates[1])]


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


class Window(GraphicObject):
    """The visible region of the world. Lives in the display file as the
    first element (drawable=False) so that transformations can be applied
    to it just like any other object."""

    def __init__(self, x_min, y_min, x_max, y_max):
        coords = [(x_min, y_min), (x_max, y_min),
                   (x_max, y_max), (x_min, y_max)]
        super().__init__("window", coords, drawable=False)
        # Copy of the initial coordinates for reset
        self._initial_coords = list(coords)

    @property
    def object_type(self):
        return "window"

    def draw_segments(self):
        return []

    def bounds(self):
        """Returns (x_min, y_min, x_max, y_max) from the corner coordinates."""
        xs = [c[0] for c in self.coordinates]
        ys = [c[1] for c in self.coordinates]
        return (min(xs), min(ys), max(xs), max(ys))

    def _set_bounds(self, x_min, y_min, x_max, y_max):
        self.coordinates = [(x_min, y_min), (x_max, y_min),
                            (x_max, y_max), (x_min, y_max)]

    def pan(self, dx, dy, step):
        """Shifts the window by a fraction (step) of its size in the
        direction given by dx, dy."""
        x_min, y_min, x_max, y_max = self.bounds()
        width = x_max - x_min
        height = y_max - y_min
        self._set_bounds(x_min + dx * width * step,
                         y_min + dy * height * step,
                         x_max + dx * width * step,
                         y_max + dy * height * step)

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

    def reset(self):
        """Restores the window to its initial coordinates."""
        self.coordinates = list(self._initial_coords)


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

    def __iter__(self):
        return iter(self._objects)
