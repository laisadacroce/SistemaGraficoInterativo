import math
import transform3d as t3d


class GraphicObject:
    """Base class for all graphic objects. Subclasses must implement
    object_type and draw_segments."""

    def __init__(self, name, coordinates, drawable=True, color="#000000"):
        self.name = name
        self.coordinates = coordinates  # list of (x, y) tuples in world coords
        self.drawable = drawable
        self.color = color  # RGB hex color for drawing
        self.normalized_coords = []  # SCN cache, computed by DisplayFile.project()
        self.view_coords = []  # coordenadas 3D de view, computadas em project()

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


class BSpline(GraphicObject):
    """Curva B-Spline uniforme cúbica avaliada por Forward Differences.

    Aceita qualquer número n >= 4 de pontos de controle. Com n pontos
    são geradas n - 3 curvas (segmentos), cada uma definida por 4 pontos
    de controle consecutivos numa janela deslizante (P_i .. P_{i+3}).
    A continuidade entre segmentos é C(2) — bem acima do mínimo G(0)
    exigido — por construção da base B-Spline uniforme.

    Cada segmento é um polinômio cúbico P(t) = a t³ + b t² + c t + d
    cujos coeficientes vêm de C = M_BS · G. Em vez de avaliar esse
    polinômio em cada t (caro: potências e multiplicações), usa-se a
    técnica de Forward Differences (diferenças adiantadas): calculam-se
    uma única vez os incrementos iniciais (Δ, Δ², Δ³) e cada ponto
    seguinte é obtido apenas com somas — conforme Trabalho 1.6."""

    STEPS = 100  # número de passos de discretização por segmento

    # Matriz base da B-Spline uniforme cúbica (M_BS) dos slides.
    # O fator 1/6 já está embutido em cada coeficiente.
    M_BS = [
        [-1/6,  3/6, -3/6, 1/6],
        [ 3/6, -6/6,  3/6,   0],
        [-3/6,    0,  3/6,   0],
        [ 1/6,  4/6,  1/6,   0],
    ]

    def __init__(self, name, points, drawable=True):
        coords = [p.coordinates[0] for p in points]
        super().__init__(name, coords, drawable)

    @property
    def object_type(self):
        return "bspline"

    @staticmethod
    def valid_point_count(n):
        """B-Spline aceita qualquer número de pontos de controle, desde
        que seja no mínimo 4."""
        return n >= 4

    def _segment_coefficients(self, p0, p1, p2, p3):
        """Multiplica M_BS pela geometria G dos 4 pontos de controle e
        retorna os coeficientes (a, b, c, d) do polinômio cúbico
        P(t) = a t³ + b t² + c t + d, para x e y separadamente.

        Aplica C = M_BS · G, onde G é o vetor-coluna dos 4 pontos."""
        gx = (p0[0], p1[0], p2[0], p3[0])
        gy = (p0[1], p1[1], p2[1], p3[1])
        cx = [sum(self.M_BS[r][k] * gx[k] for k in range(4)) for r in range(4)]
        cy = [sum(self.M_BS[r][k] * gy[k] for k in range(4)) for r in range(4)]
        return cx, cy

    def _forward_differences(self, coeffs):
        """Gera os STEPS+1 valores de um polinômio cúbico via Forward
        Differences, em t = 0, δ, 2δ, ... 1 (com δ = 1/STEPS).

        Dado P(t) = a t³ + b t² + c t + d, os incrementos iniciais são:
          f    = P(0)            = d
          Δf   = P(δ) - P(0)     = a δ³ + b δ² + c δ
          Δ²f  = Δf(δ) - Δf(0)   = 6a δ³ + 2b δ²
          Δ³f  (constante)       = 6a δ³
        A cada passo, atualiza-se apenas com somas:
          f += Δf ; Δf += Δ²f ; Δ²f += Δ³f"""
        a, b, c, d = coeffs
        n = self.STEPS
        delta = 1.0 / n
        d2 = delta * delta
        d3 = d2 * delta

        f = d
        df = a * d3 + b * d2 + c * delta
        d2f = 6 * a * d3 + 2 * b * d2
        d3f = 6 * a * d3

        values = [f]
        for _ in range(n):
            f += df
            df += d2f
            d2f += d3f
            values.append(f)
        return values

    def _generate_curve_points(self, control_coords):
        """Percorre cada grupo de 4 pontos de controle consecutivos
        (janela deslizante) e concatena os pontos discretizados de
        todos os segmentos, evitando duplicar os pontos de junção."""
        all_points = []
        n = len(control_coords)
        if not self.valid_point_count(n):
            return all_points

        for i in range(n - 3):
            p0, p1, p2, p3 = control_coords[i:i + 4]
            cx, cy = self._segment_coefficients(p0, p1, p2, p3)
            xs = self._forward_differences(cx)
            ys = self._forward_differences(cy)
            segment = list(zip(xs, ys))
            # Evitar duplicar o ponto de junção entre segmentos consecutivos
            if all_points:
                segment = segment[1:]
            all_points.extend(segment)
        return all_points

    def draw_segments(self):
        """Gera segmentos de reta conectando pontos consecutivos da
        B-Spline em coordenadas do mundo."""
        curve_pts = self._generate_curve_points(self.coordinates)
        return [(curve_pts[i], curve_pts[i + 1])
                for i in range(len(curve_pts) - 1)]

    def draw_segments_scn(self):
        """Gera os segmentos de reta da B-Spline em coordenadas SCN.
        O pipeline SCN é afim, logo pode ser aplicado diretamente sobre
        os pontos de controle normalizados."""
        curve_pts = self._generate_curve_points(self.normalized_coords)
        return [(curve_pts[i], curve_pts[i + 1])
                for i in range(len(curve_pts) - 1)]

    def curve_points_scn(self):
        """Retorna a lista de pontos discretizados da B-Spline em SCN.
        Usado pelo clipping de curvas (point clipping em cada amostra)."""
        return self._generate_curve_points(self.normalized_coords)


class Point3D(GraphicObject):
    """Ponto no espaço 3D (x, y, z) — Trabalho 1.7.

    Capaz de sofrer as 3 transformações básicas (translação,
    escalonamento e rotação) por meio de matrizes 4x4 — ver
    transform3d.py. É também o bloco de construção dos segmentos de
    reta de um Object3D."""

    def __init__(self, name, x, y, z):
        super().__init__(name, [(x, y, z)])

    @property
    def object_type(self):
        return "point3d"

    @property
    def position(self):
        """Coordenada 3D atual do ponto."""
        return self.coordinates[0]

    def center3d(self):
        """O centro de um ponto é o próprio ponto."""
        return self.coordinates[0]

    def draw_segments(self):
        return []  # pontos são desenhados como círculos, não segmentos

    def draw_segments_scn(self):
        return []


class Object3D(GraphicObject):
    """Objeto 3D em modelo de arame (wireframe) — Trabalho 1.7.

    É descrito por:
      - uma lista de pontos de controle 3D (`coordinates`);
      - uma lista de segmentos de reta (`segments`), onde cada segmento
        é um par de índices (i, j) ligando dois pontos. Ou seja: cada
        segmento é constituído por um par de Pontos3D.

    Capaz das 3 operações básicas (translação, escalonamento, rotação)
    e também da rotação em torno de um eixo arbitrário — todas aplicadas
    às coordenadas 3D por matrizes 4x4 (ver transform3d.py)."""

    def __init__(self, name, points, segments, drawable=True):
        # points: lista de Point3D ou de tuplas (x, y, z)
        coords = []
        for p in points:
            if isinstance(p, Point3D):
                coords.append(p.coordinates[0])
            else:
                coords.append((float(p[0]), float(p[1]), float(p[2])))
        super().__init__(name, coords, drawable)
        self.segments = [(int(i), int(j)) for i, j in segments]

    @property
    def object_type(self):
        return "object3d"

    def center3d(self):
        """Centro geométrico 3D — média de todos os pontos de controle."""
        n = len(self.coordinates)
        cx = sum(p[0] for p in self.coordinates) / n
        cy = sum(p[1] for p in self.coordinates) / n
        cz = sum(p[2] for p in self.coordinates) / n
        return (cx, cy, cz)

    def center(self):
        """Projeção 2D do centro (compatibilidade com a interface base)."""
        cx, cy, cz = self.center3d()
        return (cx, cy)

    def draw_segments(self):
        """Pares de pontos 3D (mundo) de cada segmento de reta."""
        return [(self.coordinates[i], self.coordinates[j])
                for i, j in self.segments]

    def draw_segments_scn(self):
        """Pares de pontos 2D já projetados (SCN) de cada segmento."""
        nc = self.normalized_coords
        result = []
        for i, j in self.segments:
            if i < len(nc) and j < len(nc):
                result.append((nc[i], nc[j]))
        return result


class Window(GraphicObject):
    """Window/câmera do sistema. A partir do Trabalho 1.7 é uma câmera
    3D, definida por:
      - VRP (View Reference Point): posição da câmera no mundo 3D;
      - VPN (View Plane Normal): direção para onde a câmera olha;
      - VUP (View Up): vetor que define o 'para cima' da câmera;
      - win_width / win_height: tamanho da janela no plano de projeção
        (alterado pelo zoom).

    A navegação no espaço 3D opera sobre esses parâmetros. A projeção
    paralela ortogonal (transform3d.parallel_projection_matrix) translada
    o VRP para a origem, alinha o VPN ao eixo Z e normaliza para o SCN.

    Com a configuração inicial (VRP na origem, VPN = +Z, VUP = +Y) a
    visualização equivale exatamente ao sistema 2D anterior."""

    def __init__(self, x_min, y_min, x_max, y_max):
        super().__init__("window", [], drawable=False)
        # VRP inicial: centro do retângulo informado, no plano z = 0
        cx = (x_min + x_max) / 2
        cy = (y_min + y_max) / 2
        self._initial_vrp = (cx, cy, 0.0)
        self._initial_width = float(x_max - x_min)
        self._initial_height = float(y_max - y_min)
        # Modo de projeção: 'parallel' (ortogonal) ou 'perspective'.
        # cop_distance é a distância do COP ao plano de projeção:
        # menor → grande angular; maior → teleobjetiva.
        self.projection_mode = "parallel"
        self.cop_distance = 800.0
        self.reset()

    @property
    def object_type(self):
        return "window"

    def draw_segments(self):
        return []

    def draw_segments_scn(self):
        return []

    def center(self):
        """Posição (x, y) do VRP — usado apenas por compatibilidade."""
        return (self.vrp[0], self.vrp[1])

    def width(self):
        return self.win_width

    def height(self):
        return self.win_height

    # ── Helpers de vetor ─────────────────────────────────
    def _view_right(self):
        """Eixo horizontal da câmera (direita), no espaço do mundo."""
        return t3d.normalize(t3d.cross(self.vup, self.vpn))

    def _rotate_vec(self, vec, axis, angle):
        """Rotaciona um vetor em torno de um eixo que passa pela origem."""
        m = t3d.rotation_around_axis_matrix(angle, (0, 0, 0), axis)
        return t3d.normalize(t3d.transform_point(vec, m))

    # ── Navegação 3D ─────────────────────────────────────
    def pan(self, dx, dy, step):
        """Desloca a câmera (VRP) no plano de visão: dx para a direita,
        dy para cima, relativo à orientação atual da câmera."""
        right = self._view_right()
        up = t3d.normalize(self.vup)
        sx = step * dx * self.win_width
        sy = step * dy * self.win_height
        self.vrp = (self.vrp[0] + right[0] * sx + up[0] * sy,
                    self.vrp[1] + right[1] * sx + up[1] * sy,
                    self.vrp[2] + right[2] * sx + up[2] * sy)

    def move_forward(self, factor, step):
        """Desloca a câmera ao longo do VPN (frente/trás). Numa projeção
        paralela ortogonal isto não altera a imagem projetada — o
        deslocamento é paralelo à direção de projeção —, mas movimenta
        de fato a câmera no espaço 3D."""
        n = t3d.normalize(self.vpn)
        d = factor * step * self.win_width
        self.vrp = (self.vrp[0] + n[0] * d,
                    self.vrp[1] + n[1] * d,
                    self.vrp[2] + n[2] * d)

    def zoom(self, factor, step):
        """Aumenta/diminui o tamanho da window no plano de projeção.
        factor=1 aproxima (encolhe a window), factor=-1 afasta."""
        f = 1 - factor * step
        self.win_width *= f
        self.win_height *= f

    def rotate(self, angle_degrees):
        """Roll: gira a câmera em torno do próprio VPN (eixo de visão).
        Mantido com este nome por compatibilidade com o sistema 2D."""
        self.vup = self._rotate_vec(self.vup, self.vpn, angle_degrees)
        self.angle += angle_degrees

    roll = rotate

    def pitch(self, angle_degrees):
        """Inclina a câmera para cima/baixo, girando VPN e VUP em torno
        do eixo horizontal da câmera (view-right)."""
        axis = self._view_right()
        self.vpn = self._rotate_vec(self.vpn, axis, angle_degrees)
        self.vup = self._rotate_vec(self.vup, axis, angle_degrees)

    def yaw(self, angle_degrees):
        """Gira a câmera para os lados, girando o VPN em torno do VUP."""
        self.vpn = self._rotate_vec(self.vpn, self.vup, angle_degrees)

    def reset(self):
        """Restaura a câmera para a configuração inicial: olhando ao
        longo do eixo Z (VPN = +Z) com VUP no eixo Y."""
        self.vrp = self._initial_vrp
        self.vpn = (0.0, 0.0, 1.0)
        self.vup = (0.0, 1.0, 0.0)
        self.win_width = self._initial_width
        self.win_height = self._initial_height
        self.angle = 0  # ângulo de roll acumulado


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

    def project(self, window):
        """Recalcula as coordenadas de view e as coordenadas
        normalizadas (SCN) de todos os objetos desenháveis.

        Aplica a matriz de view (transladar o VRP para a origem e
        alinhar o VPN ao eixo Z) e, em seguida, a projeção — paralela
        ortogonal ou em perspectiva, conforme `window.projection_mode`.

        Objetos 2D são tratados como pontos 3D com z = 0. Cada objeto
        recebe `view_coords` (pontos 3D em coordenadas de view) e
        `normalized_coords` (pontos 2D em SCN; None onde o ponto está
        atrás do COP, situação possível só na perspectiva)."""
        vmat = t3d.view_matrix(window)
        for obj in self.drawable_objects():
            view_coords = []
            for c in obj.coordinates:
                x = c[0]
                y = c[1]
                z = c[2] if len(c) > 2 else 0.0
                view_coords.append(t3d.transform_point((x, y, z), vmat))
            obj.view_coords = view_coords
            obj.normalized_coords = [t3d.project_view_point(p, window)
                                     for p in view_coords]

    def __iter__(self):
        return iter(self._objects)
