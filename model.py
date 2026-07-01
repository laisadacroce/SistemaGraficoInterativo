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


class Object3DPhong(GraphicObject):
    """Objeto 3D feito de triângulos com normais por vértice, para
    iluminação de Phong — Trabalho 2.3.

    Cada triângulo tem 3 vértices e 3 normais (uma por vértice). Guardamos
    tudo achatado, 3 entradas por triângulo, em ordem: `coordinates` são
    os vértices (herdado de GraphicObject, então a projeção do DisplayFile
    já calcula view_coords/normalized_coords automaticamente) e `normals`
    são as normais alinhadas na mesma ordem. É desenhado pela rasterização
    por software (framebuffer); não aparece no modo vetorial puro."""

    def __init__(self, name, triangulos, color="#888888", drawable=True):
        # triangulos: lista de {'v': [(x,y,z)x3], 'n': [(nx,ny,nz)x3]}
        coords = []
        normals = []
        for tri in triangulos:
            for v in tri["v"]:
                coords.append((float(v[0]), float(v[1]), float(v[2])))
            for nrm in tri["n"]:
                normals.append((float(nrm[0]), float(nrm[1]), float(nrm[2])))
        super().__init__(name, coords, drawable, color)
        self.normals = normals

    @property
    def object_type(self):
        return "phong"

    @property
    def n_triangles(self):
        return len(self.coordinates) // 3

    def center3d(self):
        n = len(self.coordinates)
        cx = sum(p[0] for p in self.coordinates) / n
        cy = sum(p[1] for p in self.coordinates) / n
        cz = sum(p[2] for p in self.coordinates) / n
        return (cx, cy, cz)

    def center(self):
        cx, cy, cz = self.center3d()
        return (cx, cy)

    def draw_segments(self):
        """Arestas dos triângulos (usado só no fallback wireframe)."""
        segs = []
        for t in range(self.n_triangles):
            a = self.coordinates[3 * t]
            b = self.coordinates[3 * t + 1]
            c = self.coordinates[3 * t + 2]
            segs.extend([(a, b), (b, c), (c, a)])
        return segs

    def draw_segments_scn(self):
        return []


class BezierSurface(GraphicObject):
    """Superfície bicúbica de Bézier 3D — Trabalho 1.9.

    Representada por suas matrizes de geometria: uma lista de retalhos
    (patches), cada um com 16 pontos de controle 3D organizados numa
    matriz 4x4. Os pontos de controle ficam achatados em `coordinates`
    (16 por retalho, em ordem linha-a-linha), de modo que a superfície
    participa do pipeline 3D comum (view → projeção) exatamente como um
    Object3D — inclusive das transformações 3D por matrizes 4x4.

    O desenho avalia a função de suavização para superfícies bicúbicas
    (Eq. 5.27 dos slides):

        P(s, t) = S · M_B · G · M_B^T · T^T

    onde S = [s³ s² s 1], T = [t³ t² t 1], M_B é a matriz de Bézier e G é
    a matriz de geometria 4x4 de UMA das coordenadas (x, y ou z). A
    avaliação é feita sobre os pontos de controle em coordenadas de VIEW
    (3D) — válido porque a matriz de view é afim — gerando uma malha 3D
    de iso-curvas (nas direções s e t). Essa malha 3D é então projetada
    (paralela ortogonal ou perspectiva) segmento a segmento em main.py,
    aproveitando o clipping de near-plane da perspectiva.

    Retalhos que compartilham pontos de controle de borda formam uma
    superfície composta contínua (G(0) por construção)."""

    STEPS = 10  # subdivisões em cada direção (s, t) por retalho

    # Matriz de Bézier (M_B) — mesma das curvas (Eq. 5.22)
    M_B = [
        [-1,  3, -3, 1],
        [ 3, -6,  3, 0],
        [-3,  3,  0, 0],
        [ 1,  0,  0, 0],
    ]

    def __init__(self, name, patches, drawable=True):
        # patches: lista de retalhos; cada retalho é uma lista de 16
        # pontos de controle (Point3D ou tuplas (x, y, z)).
        coords = []
        for patch in patches:
            if not self.valid_patch(patch):
                raise ValueError("cada retalho precisa de 16 pontos de controle")
            for p in patch:
                if isinstance(p, Point3D):
                    coords.append(p.coordinates[0])
                else:
                    coords.append((float(p[0]), float(p[1]), float(p[2])))
        super().__init__(name, coords, drawable)

    @property
    def object_type(self):
        return "surface"

    @staticmethod
    def valid_patch(points):
        """Um retalho bicúbico precisa de exatamente 16 pontos de controle."""
        return len(points) == 16

    @property
    def n_patches(self):
        return len(self.coordinates) // 16

    def patches(self):
        """Lista de retalhos (cada um = 16 tuplas (x,y,z)) reconstruída
        das coordenadas achatadas. Reflete transformações já aplicadas."""
        return [self.coordinates[p * 16:(p + 1) * 16]
                for p in range(self.n_patches)]

    def center3d(self):
        """Centro geométrico 3D — média dos pontos de controle."""
        n = len(self.coordinates)
        cx = sum(p[0] for p in self.coordinates) / n
        cy = sum(p[1] for p in self.coordinates) / n
        cz = sum(p[2] for p in self.coordinates) / n
        return (cx, cy, cz)

    def center(self):
        """Projeção 2D do centro (compatibilidade com a interface base)."""
        cx, cy, cz = self.center3d()
        return (cx, cy)

    # ── Álgebra de matrizes (locais) ─────────────────────
    @staticmethod
    def _mat_mult(a, b):
        """Multiplica a (m×n) por b (n×p)."""
        m, n, p = len(a), len(b), len(b[0])
        result = [[0.0] * p for _ in range(m)]
        for i in range(m):
            for k in range(n):
                aik = a[i][k]
                if aik == 0:
                    continue
                for j in range(p):
                    result[i][j] += aik * b[k][j]
        return result

    @staticmethod
    def _transpose(matrix):
        return [list(row) for row in zip(*matrix)]

    def _coeff_matrix(self, geometry):
        """Pré-calcula C = M_B · G · M_B^T para uma coordenada do retalho.
        Com C pronta, cada ponto da malha custa apenas S · C · T^T."""
        mb_t = self._transpose(self.M_B)
        return self._mat_mult(self._mat_mult(self.M_B, geometry), mb_t)

    def _patch_geometry(self, flat_coords, patch_index):
        """Reconstrói as matrizes de geometria 4x4 (Gx, Gy, Gz) de um
        retalho a partir das coordenadas 3D achatadas."""
        base = patch_index * 16
        pts = flat_coords[base:base + 16]
        gx = [[pts[r * 4 + c][0] for c in range(4)] for r in range(4)]
        gy = [[pts[r * 4 + c][1] for c in range(4)] for r in range(4)]
        gz = [[pts[r * 4 + c][2] for c in range(4)] for r in range(4)]
        return gx, gy, gz

    @staticmethod
    def _eval(cx, cy, cz, s, t):
        """Avalia P(s, t) = S · C · T^T para x, y e z."""
        s_vec = [s ** 3, s ** 2, s, 1]
        t_vec = [t ** 3, t ** 2, t, 1]

        def coord(c):
            v = [sum(s_vec[k] * c[k][j] for k in range(4)) for j in range(4)]
            return sum(v[j] * t_vec[j] for j in range(4))

        return (coord(cx), coord(cy), coord(cz))

    def _mesh_segments(self, flat_coords):
        """Gera os segmentos de reta 3D da malha (iso-curvas em s e em t)
        de todos os retalhos, a partir das coordenadas 3D achatadas."""
        segments = []
        steps = self.STEPS
        for p in range(len(flat_coords) // 16):
            gx, gy, gz = self._patch_geometry(flat_coords, p)
            cx = self._coeff_matrix(gx)
            cy = self._coeff_matrix(gy)
            cz = self._coeff_matrix(gz)

            grid = []
            for i in range(steps + 1):
                s = i / steps
                row = [self._eval(cx, cy, cz, s, j / steps)
                       for j in range(steps + 1)]
                grid.append(row)

            # Iso-curvas em t (liga colunas dentro de cada linha)
            for i in range(steps + 1):
                for j in range(steps):
                    segments.append((grid[i][j], grid[i][j + 1]))
            # Iso-curvas em s (liga linhas dentro de cada coluna)
            for j in range(steps + 1):
                for i in range(steps):
                    segments.append((grid[i][j], grid[i + 1][j]))

        return segments

    def mesh_view_segments(self):
        """Segmentos 3D da malha em coordenadas de VIEW, prontos para
        projeção (paralela ou perspectiva) segmento a segmento."""
        return self._mesh_segments(self.view_coords)

    def draw_segments(self):
        """Segmentos 3D da malha em coordenadas do mundo."""
        return self._mesh_segments(self.coordinates)

    def draw_segments_scn(self):
        """Não usado: a superfície é projetada em main.py a partir da
        malha 3D em coordenadas de view (perspectiva-correto). Mantido
        por completude da interface GraphicObject."""
        return []


class BSplineSurface(GraphicObject):
    """Superfície bicúbica B-Spline 3D desenhada por Diferenças Adiante
    (Forward Differences) — Trabalho 1.10.

    Recebe uma matriz n×m de pontos de controle 3D (4 ≤ n, m ≤ 20),
    achatada em `coordinates` (ordem linha-a-linha). O SGI subdivide
    automaticamente em (n-3)×(m-3) retalhos, cada um uma janela
    deslizante 4×4 sobre a matriz — exatamente como a curva B-Spline
    desliza uma janela de 4 pontos. Cada retalho é uma superfície
    bicúbica B-Spline (base uniforme M_BS), com continuidade C(2) entre
    retalhos por construção.

    Cada retalho é desenhado pelo Método das Diferenças Adiante: em vez
    de avaliar P(s,t) = S · C · T^T (com C = M_BS · G · M_BS^T) a cada
    passo, pré-calcula uma única vez a matriz de diferenças

        DD = E(δs) · C · E(δt)^T

    e gera toda a grade de pontos do retalho apenas com SOMAS. E(δ) é a
    matriz que converte os coeficientes de um polinômio cúbico nas suas
    diferenças adiante iniciais [f, Δf, Δ²f, Δ³f].

    Diferente do pseudocódigo de Foley & van Dam, cada iso-curva em t é
    percorrida sobre uma CÓPIA da primeira linha de DD, preservando DD
    intacta para o avanço em s — assim nem a varredura em t nem a em s
    corrompem as diferenças necessárias à outra direção (este é o erro
    clássico do algoritmo do livro). A avaliação é feita em coordenadas
    de VIEW (afim), e a malha 3D é projetada segmento a segmento em
    main.py (paralela ou perspectiva)."""

    STEPS = 10  # passos de forward differences por direção, por retalho

    # Matriz base da B-Spline uniforme cúbica (M_BS), fator 1/6 embutido
    # (a mesma usada na curva BSpline).
    M_BS = [
        [-1/6,  3/6, -3/6, 1/6],
        [ 3/6, -6/6,  3/6,   0],
        [-3/6,    0,  3/6,   0],
        [ 1/6,  4/6,  1/6,   0],
    ]

    def __init__(self, name, grid, drawable=True):
        # grid: lista de linhas; cada linha é uma lista de pontos
        # (Point3D ou tuplas (x, y, z)). Todas as linhas com o mesmo
        # número de colunas.
        self.n_rows = len(grid)
        self.n_cols = len(grid[0]) if grid else 0
        if not self.valid_dims(self.n_rows, self.n_cols):
            raise ValueError("a matriz de controle deve ter entre 4x4 e 20x20")
        coords = []
        for row in grid:
            if len(row) != self.n_cols:
                raise ValueError("todas as linhas precisam do mesmo número de pontos")
            for p in row:
                if isinstance(p, Point3D):
                    coords.append(p.coordinates[0])
                else:
                    coords.append((float(p[0]), float(p[1]), float(p[2])))
        super().__init__(name, coords, drawable)

    @property
    def object_type(self):
        return "bsurface"

    @staticmethod
    def valid_dims(n_rows, n_cols):
        """A matriz de pontos de controle deve ter dimensão 4x4 a 20x20."""
        return 4 <= n_rows <= 20 and 4 <= n_cols <= 20

    @property
    def n_patches(self):
        return (self.n_rows - 3) * (self.n_cols - 3)

    def center3d(self):
        """Centro geométrico 3D — média dos pontos de controle."""
        n = len(self.coordinates)
        cx = sum(p[0] for p in self.coordinates) / n
        cy = sum(p[1] for p in self.coordinates) / n
        cz = sum(p[2] for p in self.coordinates) / n
        return (cx, cy, cz)

    def center(self):
        """Projeção 2D do centro (compatibilidade com a interface base)."""
        cx, cy, cz = self.center3d()
        return (cx, cy)

    # ── Álgebra de matrizes (locais) ─────────────────────
    @staticmethod
    def _mat_mult(a, b):
        """Multiplica a (m×n) por b (n×p)."""
        m, n, p = len(a), len(b), len(b[0])
        result = [[0.0] * p for _ in range(m)]
        for i in range(m):
            for k in range(n):
                aik = a[i][k]
                if aik == 0:
                    continue
                for j in range(p):
                    result[i][j] += aik * b[k][j]
        return result

    @staticmethod
    def _transpose(matrix):
        return [list(row) for row in zip(*matrix)]

    @staticmethod
    def _e_matrix(delta):
        """Matriz E(δ) das diferenças adiante de um polinômio cúbico:
        dado o vetor de coeficientes [a, b, c, d] de a t³+b t²+c t+d,
        E(δ)·[a,b,c,d]^T = [f(0), Δf, Δ²f, Δ³f]^T, com passo δ."""
        d2 = delta * delta
        d3 = d2 * delta
        return [
            [0,       0,      0,     1],   # f(0)  = d
            [d3,      d2,     delta, 0],   # Δf
            [6 * d3,  2 * d2, 0,     0],   # Δ²f
            [6 * d3,  0,      0,     0],   # Δ³f
        ]

    def _window_geometry(self, flat_coords, pi, pj):
        """Matrizes de geometria 4x4 (Gx, Gy, Gz) da janela deslizante
        que começa na linha pi, coluna pj da matriz de controle."""
        gx = [[None] * 4 for _ in range(4)]
        gy = [[None] * 4 for _ in range(4)]
        gz = [[None] * 4 for _ in range(4)]
        for r in range(4):
            for c in range(4):
                p = flat_coords[(pi + r) * self.n_cols + (pj + c)]
                gx[r][c] = p[0]
                gy[r][c] = p[1]
                gz[r][c] = p[2]
        return gx, gy, gz

    def _fwd_diff_grid(self, dd, ns, nt):
        """Gera a grade (ns+1)×(nt+1) de valores de UMA coordenada do
        retalho, a partir da matriz de diferenças DD, usando só somas.

        Trabalha sobre uma cópia de DD. Para cada passo em s, percorre a
        iso-curva em t sobre uma cópia da primeira linha — preservando DD
        para o avanço em s (correção do algoritmo de Foley & van Dam)."""
        m = [row[:] for row in dd]
        grid = []
        for _i in range(ns + 1):
            # iso-curva em t a partir de m[0], sem destruir m[0]
            a0, a1, a2, a3 = m[0][0], m[0][1], m[0][2], m[0][3]
            row = []
            for _j in range(nt + 1):
                row.append(a0)
                a0 += a1
                a1 += a2
                a2 += a3
            grid.append(row)
            # avanço em s: diferença adiante das linhas de DD
            for k in range(4):
                m[0][k] += m[1][k]
                m[1][k] += m[2][k]
                m[2][k] += m[3][k]
        return grid

    def _patch_segments(self, gx, gy, gz):
        """Diferenças adiante de um retalho 4×4: calcula C = M_BS·G·M_BS^T
        e DD = E(δs)·C·E(δt)^T para x, y, z, gera as três grades e liga
        os pontos numa malha de iso-curvas (direções s e t)."""
        ns = nt = self.STEPS
        mbs_t = self._transpose(self.M_BS)
        es = self._e_matrix(1.0 / ns)
        et_t = self._transpose(self._e_matrix(1.0 / nt))

        def grade(g):
            c = self._mat_mult(self._mat_mult(self.M_BS, g), mbs_t)
            dd = self._mat_mult(self._mat_mult(es, c), et_t)
            return self._fwd_diff_grid(dd, ns, nt)

        sx, sy, sz = grade(gx), grade(gy), grade(gz)
        pts = [[(sx[i][j], sy[i][j], sz[i][j]) for j in range(nt + 1)]
               for i in range(ns + 1)]

        segments = []
        for i in range(ns + 1):
            for j in range(nt):
                segments.append((pts[i][j], pts[i][j + 1]))
        for j in range(nt + 1):
            for i in range(ns):
                segments.append((pts[i][j], pts[i + 1][j]))
        return segments

    def _mesh_segments(self, flat_coords):
        """Percorre todas as janelas deslizantes 4×4 (subdivisão
        automática) e concatena os segmentos da malha de cada retalho."""
        segments = []
        for pi in range(self.n_rows - 3):
            for pj in range(self.n_cols - 3):
                gx, gy, gz = self._window_geometry(flat_coords, pi, pj)
                segments.extend(self._patch_segments(gx, gy, gz))
        return segments

    def mesh_view_segments(self):
        """Segmentos 3D da malha em coordenadas de VIEW, prontos para
        projeção segmento a segmento (paralela ou perspectiva)."""
        return self._mesh_segments(self.view_coords)

    def draw_segments(self):
        """Segmentos 3D da malha em coordenadas do mundo."""
        return self._mesh_segments(self.coordinates)

    def draw_segments_scn(self):
        """Não usado: projetada em main.py a partir da malha 3D em
        coordenadas de view. Mantido por completude da interface."""
        return []


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
