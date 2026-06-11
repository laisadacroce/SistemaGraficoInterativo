"""Transformações 3D em coordenadas homogêneas (matrizes 4x4) e
projeção paralela ortogonal — Trabalho 1.7.

Convenção: vetores-linha, igual ao módulo 2D `transform.py`.
Um ponto homogêneo p = [x, y, z, 1] é transformado por p' = p · M
(multiplicação à direita). Compor "primeiro A, depois B" é A · B."""

import math


# ── Vetores 3D ───────────────────────────────────────────

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    """Produto vetorial a × b."""
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def length(v):
    return math.sqrt(dot(v, v))


def normalize(v):
    """Retorna o vetor unitário na direção de v. Se v for nulo, devolve v."""
    n = length(v)
    if n == 0:
        return v
    return (v[0] / n, v[1] / n, v[2] / n)


# ── Matrizes 4x4 básicas ─────────────────────────────────

def identity_matrix():
    return [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]


def translation_matrix(dx, dy, dz):
    """Matriz 4x4 de translação. Os deslocamentos vão na última linha,
    pois o ponto é o vetor-linha [x, y, z, 1] multiplicado à esquerda."""
    return [
        [1,  0,  0,  0],
        [0,  1,  0,  0],
        [0,  0,  1,  0],
        [dx, dy, dz, 1],
    ]


def scaling_matrix(sx, sy, sz):
    """Matriz 4x4 de escalonamento em torno da origem."""
    return [
        [sx, 0,  0,  0],
        [0,  sy, 0,  0],
        [0,  0,  sz, 0],
        [0,  0,  0,  1],
    ]


def rotation_x_matrix(angle_degrees):
    """Rotação em torno do eixo X."""
    rad = math.radians(angle_degrees)
    c, s = math.cos(rad), math.sin(rad)
    return [
        [1,  0,  0, 0],
        [0,  c,  s, 0],
        [0, -s,  c, 0],
        [0,  0,  0, 1],
    ]


def rotation_y_matrix(angle_degrees):
    """Rotação em torno do eixo Y."""
    rad = math.radians(angle_degrees)
    c, s = math.cos(rad), math.sin(rad)
    return [
        [c, 0, -s, 0],
        [0, 1,  0, 0],
        [s, 0,  c, 0],
        [0, 0,  0, 1],
    ]


def rotation_z_matrix(angle_degrees):
    """Rotação em torno do eixo Z."""
    rad = math.radians(angle_degrees)
    c, s = math.cos(rad), math.sin(rad)
    return [
        [ c, s, 0, 0],
        [-s, c, 0, 0],
        [ 0, 0, 1, 0],
        [ 0, 0, 0, 1],
    ]


# ── Operações com matrizes ───────────────────────────────

def multiply_matrices(m1, m2):
    """Multiplica duas matrizes 4x4."""
    result = [[0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i][j] += m1[i][k] * m2[k][j]
    return result


def compose_matrices(matrices):
    """Compõe uma lista de matrizes 4x4 em uma só, multiplicando da
    esquerda para a direita (a primeira da lista é aplicada primeiro)."""
    result = identity_matrix()
    for m in matrices:
        result = multiply_matrices(result, m)
    return result


def transform_point(point, matrix):
    """Aplica uma matriz 4x4 a um ponto (x, y, z), devolvendo (x', y', z').

    Calcula [x', y', z', 1] = [x, y, z, 1] · matrix."""
    x, y, z = point
    xn = x * matrix[0][0] + y * matrix[1][0] + z * matrix[2][0] + matrix[3][0]
    yn = x * matrix[0][1] + y * matrix[1][1] + z * matrix[2][1] + matrix[3][1]
    zn = x * matrix[0][2] + y * matrix[1][2] + z * matrix[2][2] + matrix[3][2]
    return (xn, yn, zn)


# ── Base ortonormal a partir de uma direção ──────────────

def _basis_from_normal(n, up=None):
    """Constrói uma base ortonormal (u, v, w) com w na direção de n.

    Devolve três vetores unitários e perpendiculares entre si, onde:
      w → mapeado para o eixo Z
      u → mapeado para o eixo X
      v → mapeado para o eixo Y

    Se `up` for fornecido (vetor view-up), v fica o mais alinhado
    possível com ele; caso contrário escolhe-se um eixo de referência
    qualquer não-paralelo a w."""
    w = normalize(n)

    if up is None:
        # Escolhe o eixo do mundo menos alinhado com w como referência
        ax, ay, az = abs(w[0]), abs(w[1]), abs(w[2])
        if ax <= ay and ax <= az:
            up = (1, 0, 0)
        elif ay <= az:
            up = (0, 1, 0)
        else:
            up = (0, 0, 1)

    u = normalize(cross(up, w))
    if length(u) == 0:
        # up paralelo a w — usa fallback
        u = normalize(cross((1, 0, 0), w))
        if length(u) == 0:
            u = normalize(cross((0, 1, 0), w))
    v = cross(w, u)
    return u, v, w


def align_to_z_matrix(n, up=None):
    """Matriz 4x4 que rotaciona o vetor `n` para o eixo +Z.

    As colunas da parte 3x3 são (u, v, w): assim [w 1]·M = [0 0 1 1],
    [u 1]·M = [1 0 0 1] e [v 1]·M = [0 1 0 1]."""
    u, v, w = _basis_from_normal(n, up)
    return [
        [u[0], v[0], w[0], 0],
        [u[1], v[1], w[1], 0],
        [u[2], v[2], w[2], 0],
        [0,    0,    0,    1],
    ]


# ── Transformações compostas ─────────────────────────────

def rotation_around_axis_matrix(angle_degrees, point, direction):
    """Matriz que rotaciona em torno de um eixo arbitrário, definido por
    um ponto `point` e um vetor-direção `direction`, pelo ângulo dado.

    Algoritmo (rotação em torno de eixo arbitrário):
    1. Transladar o eixo para a origem        — T(-point)
    2. Alinhar o eixo com o eixo Z             — A
    3. Rotacionar em torno de Z pelo ângulo    — Rz(angle)
    4. Desfazer o alinhamento                  — A⁻¹
    5. Desfazer a translação                   — T(point)"""
    px, py, pz = point
    align = align_to_z_matrix(direction)
    # A parte rotacional 3x3 é ortonormal → a inversa é a transposta
    align_inv = [
        [align[0][0], align[1][0], align[2][0], 0],
        [align[0][1], align[1][1], align[2][1], 0],
        [align[0][2], align[1][2], align[2][2], 0],
        [0,           0,           0,           1],
    ]
    return compose_matrices([
        translation_matrix(-px, -py, -pz),
        align,
        rotation_z_matrix(angle_degrees),
        align_inv,
        translation_matrix(px, py, pz),
    ])


def rotation_around_center_matrix(angle_degrees, axis, obj):
    """Rotaciona um objeto em torno do seu próprio centro, no eixo dado
    ('x', 'y' ou 'z')."""
    cx, cy, cz = obj.center3d()
    direction = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    return rotation_around_axis_matrix(angle_degrees, (cx, cy, cz), direction)


def natural_scaling_matrix(sx, sy, sz, obj):
    """Escalona um objeto em torno do seu próprio centro geométrico."""
    cx, cy, cz = obj.center3d()
    return compose_matrices([
        translation_matrix(-cx, -cy, -cz),
        scaling_matrix(sx, sy, sz),
        translation_matrix(cx, cy, cz),
    ])


# ── Aplicar transformação ────────────────────────────────

def apply_transform_3d(obj, matrix):
    """Aplica uma matriz 4x4 a todas as coordenadas 3D de um objeto."""
    obj.coordinates = [transform_point(p, matrix) for p in obj.coordinates]


# ── Projeção Paralela Ortogonal ──────────────────────────

def parallel_projection_matrix(window):
    """Gera a matriz da Projeção Paralela Ortogonal — Trabalho 1.7.

    Recebe a window 3D (com VRP, VPN, VUP e tamanho) e devolve a matriz
    4x4 que leva um ponto do mundo 3D para o Sistema de Coordenadas
    Normalizado (SCN) 2D, pronto para clipping e viewport.

    Etapas do algoritmo visto em aula:
    1. Transladar o VRP (primeiro ponto / origem da câmera) para a
       origem do mundo                                  — T(-VRP)
    2. Alinhar o VPN com o eixo Z. Ao final desta etapa o VPN é
       (0, 0, 1), ou seja, paralelo ao eixo Z            — A
    3. Projetar ortogonalmente sobre o plano XY: como o VPN agora é Z,
       basta ignorar a coordenada z de cada ponto (projeção paralela
       ao VPN). A matriz não zera z explicitamente; quem usa o
       resultado simplesmente descarta z.
    4. Normalizar para [-1, 1] escalonando pelo tamanho da window — S

    O VUP é usado no passo 2 para orientar o eixo Y da projeção."""
    vrp = window.vrp
    # align_to_z leva o VPN para (0, 0, 1) e o VUP para o plano +Y
    align = align_to_z_matrix(window.vpn, up=window.vup)
    scale = scaling_matrix(2.0 / window.win_width,
                           2.0 / window.win_height,
                           1.0)
    return compose_matrices([
        translation_matrix(-vrp[0], -vrp[1], -vrp[2]),
        align,
        scale,
    ])


def project_point(point, matrix):
    """Projeta um ponto 3D para coordenadas 2D no SCN.

    Aplica a matriz da projeção paralela ortogonal e descarta a
    coordenada z (projeção ortogonal sobre o plano XY)."""
    xn, yn, _zn = transform_point(point, matrix)
    return (xn, yn)


# ── Coordenadas de view ──────────────────────────────────

def view_matrix(window):
    """Matriz 4x4 que leva um ponto do mundo para as coordenadas de
    view: VRP na origem e VPN alinhado ao eixo +Z.

    O plano de projeção passa a ser o plano z = 0 e o VUP orienta o
    eixo +Y. É a base comum das projeções paralela e perspectiva —
    ao final, o VPN é (0, 0, 1)."""
    vrp = window.vrp
    align = align_to_z_matrix(window.vpn, up=window.vup)
    return compose_matrices([
        translation_matrix(-vrp[0], -vrp[1], -vrp[2]),
        align,
    ])


# ── Projeção em Perspectiva ──────────────────────────────
#
# Após a matriz de view, o plano de projeção é z = 0 e o VPN é +Z.
# O Centro de Projeção (COP) é virtual e fica ATRÁS do plano de
# projeção, em z = -d, onde d = window.cop_distance.
#
# Um ponto (x, y, z) em coordenadas de view projeta-se sobre o plano
# z = 0 pela reta que o liga ao COP. Por semelhança de triângulos:
#       x_p = x · d / (z + d)        y_p = y · d / (z + d)
#
# Quando d → ∞ a perspectiva tende à projeção paralela. Reduzir d
# aproxima o COP do plano e produz a distorção "grande angular";
# aumentar d produz o efeito "teleobjetiva".

# Plano near, logo à frente do COP, usado no clipping de perspectiva
_NEAR_FACTOR = 0.001


def _parallel_scn(p, window):
    """Projeção paralela ortogonal de um ponto (coordenadas de view)
    para o SCN: descarta z e normaliza pelo tamanho da window."""
    return (p[0] / (window.win_width / 2.0),
            p[1] / (window.win_height / 2.0))


def _perspective_scn(p, window):
    """Projeção em perspectiva de um ponto (coordenadas de view) para
    o SCN. O COP está em z = -d (atrás do plano de projeção z = 0)."""
    d = window.cop_distance
    f = d / (p[2] + d)
    return (p[0] * f / (window.win_width / 2.0),
            p[1] * f / (window.win_height / 2.0))


def project_view_point(p, window):
    """Projeta um ponto 3D (em coordenadas de view) para o SCN 2D.

    Devolve (x, y) ou None se o ponto está atrás do COP — caso só
    possível na projeção em perspectiva."""
    if window.projection_mode == "perspective":
        d = window.cop_distance
        if p[2] + d <= d * _NEAR_FACTOR:
            return None
        return _perspective_scn(p, window)
    return _parallel_scn(p, window)


def _clip_near_plane(a, b, window):
    """Clipa um segmento (extremos em coordenadas de view) contra o
    plano near, logo à frente do COP. Necessário porque pontos atrás
    do COP não podem ser projetados em perspectiva.

    Devolve o par de pontos visível ou None se o segmento está
    inteiramente atrás do plano near."""
    d = window.cop_distance
    zn = -d + d * _NEAR_FACTOR   # plano near, imediatamente à frente do COP
    za, zb = a[2], b[2]
    in_a, in_b = za >= zn, zb >= zn
    if in_a and in_b:
        return (a, b)
    if not in_a and not in_b:
        return None
    # O segmento cruza o plano near — calcula a intersecção
    t = (zn - za) / (zb - za)
    mid = (a[0] + t * (b[0] - a[0]),
           a[1] + t * (b[1] - a[1]),
           zn)
    return (mid, b) if in_b else (a, mid)


def project_view_segment(a, b, window):
    """Projeta um segmento de reta (extremos em coordenadas de view)
    para o SCN 2D, conforme o modo de projeção da window.

    Para a perspectiva, faz o clipping de near-plane antes da divisão
    perspectiva. Devolve ((x1,y1),(x2,y2)) em SCN ou None se o
    segmento não é visível."""
    if window.projection_mode == "perspective":
        clipped = _clip_near_plane(a, b, window)
        if clipped is None:
            return None
        a, b = clipped
        return (_perspective_scn(a, window), _perspective_scn(b, window))
    return (_parallel_scn(a, window), _parallel_scn(b, window))
