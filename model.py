display_file = []


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
        self.p1 = p1
        self.p2 = p2

    @property
    def object_type(self):
        return "line"

    def draw_segments(self):
        return [(self.coordinates[0], self.coordinates[1])]


class Wireframe(GraphicObject):
    def __init__(self, name, points, drawable=True):
        coords = [p.coordinates[0] for p in points]
        super().__init__(name, coords, drawable)
        self.points = points

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
