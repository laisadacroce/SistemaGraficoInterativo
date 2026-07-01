"""Modelo de teste procedural: esfera UV com normais por vértice.

A esfera é o teste canônico da iluminação de Phong — o brilho especular
aparece nítido numa superfície curva, e a normal de cada ponto é trivial
de calcular (aponta radialmente para fora do centro). Serve de modelo
para demonstrar rasterização (2.1), Z-buffer (2.2) e Phong (2.3)."""

import math


def get_sphere_triangles(radius=120.0, stacks=16, slices=16,
                         center=(0.0, 0.0, 0.0)):
    """Gera os triângulos de uma esfera por subdivisão UV.

    stacks — divisões de polo a polo (latitude)
    slices — divisões ao redor (longitude)

    Retorna uma lista de dicts {'v': [3 vértices], 'n': [3 normais]}.
    A normal de cada vértice é a direção radial (posição − centro,
    normalizada) — exata para uma esfera."""
    cx, cy, cz = center

    # Grade de (posição, normal) por vértice
    grid = []
    for i in range(stacks + 1):
        phi = math.pi * i / stacks          # 0 (polo norte) .. pi (polo sul)
        sin_phi, cos_phi = math.sin(phi), math.cos(phi)
        row = []
        for j in range(slices + 1):
            theta = 2.0 * math.pi * j / slices
            nx = sin_phi * math.cos(theta)
            ny = cos_phi
            nz = sin_phi * math.sin(theta)
            pos = (cx + radius * nx, cy + radius * ny, cz + radius * nz)
            row.append((pos, (nx, ny, nz)))
        grid.append(row)

    # Dois triângulos por célula da grade
    triangulos = []
    for i in range(stacks):
        for j in range(slices):
            p00, n00 = grid[i][j]
            p01, n01 = grid[i][j + 1]
            p10, n10 = grid[i + 1][j]
            p11, n11 = grid[i + 1][j + 1]
            triangulos.append({"v": [p00, p10, p11], "n": [n00, n10, n11]})
            triangulos.append({"v": [p00, p11, p01], "n": [n00, n11, n01]})
    return triangulos
