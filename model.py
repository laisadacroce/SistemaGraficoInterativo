class GraphicObject:
    def __init__(self, name, coordinates, drawable=True):
        self.name = name
        self.coordinates = coordinates
        self.drawable = drawable

    @property
    def object_type(self):
        raise NotImplementedError

    def draw_segments(self):
        raise NotImplementedError

    def __str__(self):
        return f"{self.object_type.capitalize()}[{self.name}]"


class Point(GraphicObject):
    def __init__(self, name, x, y):
        super().__init__(name, [(x, y)])

    @property
    def object_type(self):
        return "point"

    def draw_segments(self):
        return []


class Line(GraphicObject):
    def __init__(self, name, p1, p2):
        super().__init__(name, [p1.coordinates[0], p2.coordinates[0]])

    @property
    def object_type(self):
        return "line"

    def draw_segments(self):
        return [(self.coordinates[0], self.coordinates[1])]


class Wireframe(GraphicObject):
    def __init__(self, name, points, drawable=True):
        coords = [p.coordinates[0] for p in points]
        super().__init__(name, coords, drawable)

    @property
    def object_type(self):
        return "wireframe"

    def draw_segments(self):
        segments = []
        for i in range(len(self.coordinates)):
            p1 = self.coordinates[i]
            p2 = self.coordinates[(i + 1) % len(self.coordinates)]
            segments.append((p1, p2))
        return segments


class Window(GraphicObject):
    def __init__(self, x_min, y_min, x_max, y_max):
        coords = [(x_min, y_min), (x_max, y_min),
                   (x_max, y_max), (x_min, y_max)]
        super().__init__("window", coords, drawable=False)
        self._initial_coords = list(coords)

    @property
    def object_type(self):
        return "window"

    def draw_segments(self):
        return []

    def bounds(self):
        xs = [c[0] for c in self.coordinates]
        ys = [c[1] for c in self.coordinates]
        return (min(xs), min(ys), max(xs), max(ys))

    def _set_bounds(self, x_min, y_min, x_max, y_max):
        self.coordinates = [(x_min, y_min), (x_max, y_min),
                            (x_max, y_max), (x_min, y_max)]

    def pan(self, dx, dy, step):
        x_min, y_min, x_max, y_max = self.bounds()
        width = x_max - x_min
        height = y_max - y_min
        self._set_bounds(x_min + dx * width * step,
                         y_min + dy * height * step,
                         x_max + dx * width * step,
                         y_max + dy * height * step)

    def zoom(self, factor, step):
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
        self.coordinates = list(self._initial_coords)


class DisplayFile:
    def __init__(self, window):
        self.window = window
        self._objects = [window]

    def add(self, obj):
        self._objects.append(obj)

    def remove(self, name):
        self._objects = [o for o in self._objects if o.name != name or o is self.window]

    def get_by_name(self, name):
        for obj in self._objects:
            if obj.name == name:
                return obj
        return None

    def has_name(self, name):
        return any(obj.name == name for obj in self._objects)

    def drawable_objects(self):
        return [obj for obj in self._objects if obj.drawable]

    def __iter__(self):
        return iter(self._objects)
