"""Modelo de iluminação de Phong — Trabalho 2.3.

O modelo de Phong soma três componentes de luz em cada ponto da
superfície:

    I = ka·Ia + kd·(L·N)·Id + ks·(R·V)^n·Is

  - ambiente  ka·Ia          — luz de fundo, uniforme (simula o
                                espalhamento indireto);
  - difusa    kd·(L·N)·Id    — depende do ângulo entre a luz (L) e a
                                normal (N); dá o "corpo" do objeto;
  - especular ks·(R·V)^n·Is  — o brilho: depende do ângulo entre o raio
                                refletido (R) e o observador (V); o
                                expoente n (shininess) controla o tamanho
                                do brilho.

Cada componente é calculada por canal (R, G, B) e o resultado é limitado
a [0, 1]."""

import numpy as np


class LuzPontual:
    """Fonte de luz pontual: uma posição no mundo 3D e uma intensidade
    RGB (cada canal em [0, 1])."""

    def __init__(self, posicao=(0.0, 0.0, 200.0), intensidade=(1.0, 1.0, 1.0)):
        self.posicao = np.array(posicao, dtype=float)
        self.intensidade = np.array(intensidade, dtype=float)


class MaterialPhong:
    """Coeficientes de reflexão do material (por canal) e o expoente
    especular (shininess)."""

    def __init__(self, ka=(0.2, 0.2, 0.2), kd=(0.7, 0.7, 0.7),
                 ks=(0.5, 0.5, 0.5), shininess=32.0):
        self.ka = np.array(ka, dtype=float)
        self.kd = np.array(kd, dtype=float)
        self.ks = np.array(ks, dtype=float)
        self.shininess = float(shininess)


def _normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def calcular_phong(ponto_3d, normal, olho, luz, material,
                   luz_ambiente=(0.2, 0.2, 0.2)):
    """Retorna a cor (R, G, B) em [0, 1] no ponto, pelo modelo de Phong.

    ponto_3d     — posição do ponto na superfície (mundo)
    normal       — normal da superfície no ponto (será normalizada)
    olho         — posição do observador/câmera (mundo)
    luz          — LuzPontual
    material     — MaterialPhong
    luz_ambiente — intensidade RGB da luz ambiente (Ia)
    """
    p = np.asarray(ponto_3d, dtype=float)
    n = _normalize(np.asarray(normal, dtype=float))
    ia = np.asarray(luz_ambiente, dtype=float)

    # L: do ponto para a luz; V: do ponto para o olho.
    l = _normalize(luz.posicao - p)
    v = _normalize(np.asarray(olho, dtype=float) - p)

    # Ambiente
    cor = material.ka * ia

    # Difusa (só se a luz atinge a frente da superfície)
    ndotl = float(np.dot(n, l))
    if ndotl > 0.0:
        cor = cor + material.kd * ndotl * luz.intensidade

        # Especular: R = reflexão de L em torno de N; brilho ∝ (R·V)^n
        r = _normalize(2.0 * ndotl * n - l)
        rdotv = float(np.dot(r, v))
        if rdotv > 0.0:
            cor = cor + material.ks * (rdotv ** material.shininess) * luz.intensidade

    return tuple(np.clip(cor, 0.0, 1.0))


def calcular_phong_lote(pontos, normais, olho, luz, material,
                        luz_ambiente=(0.2, 0.2, 0.2)):
    """Versão vetorizada de calcular_phong para MUITOS pontos de uma vez.

    Aplica exatamente a mesma fórmula, mas sobre arrays (M, 3) — usada
    pela rasterização de triângulos com Phong por pixel (draw_triangle_
    phong), onde M é o número de pixels do triângulo. Retorna um array
    (M, 3) de cores em [0, 1]."""
    p = np.asarray(pontos, dtype=float)
    n = np.asarray(normais, dtype=float)
    n = n / np.clip(np.linalg.norm(n, axis=1, keepdims=True), 1e-12, None)

    l = luz.posicao[None, :] - p
    l = l / np.clip(np.linalg.norm(l, axis=1, keepdims=True), 1e-12, None)
    v = np.asarray(olho, dtype=float)[None, :] - p
    v = v / np.clip(np.linalg.norm(v, axis=1, keepdims=True), 1e-12, None)

    ia = np.asarray(luz_ambiente, dtype=float)
    m = p.shape[0]
    # Ambiente (constante por canal, replicado para os M pixels)
    cor = np.tile(material.ka * ia, (m, 1))

    ndotl = np.sum(n * l, axis=1)                       # (M,)
    # Difusa: negativa vira zero (luz por trás da superfície)
    difuso = np.clip(ndotl, 0.0, None)
    cor = cor + (material.kd * luz.intensidade)[None, :] * difuso[:, None]

    # Especular: R = reflexão de L em torno de N; brilho ∝ (R·V)^n
    r = 2.0 * ndotl[:, None] * n - l
    r = r / np.clip(np.linalg.norm(r, axis=1, keepdims=True), 1e-12, None)
    rdotv = np.clip(np.sum(r * v, axis=1), 0.0, None)
    spec = np.where(ndotl > 0.0, rdotv ** material.shininess, 0.0)
    cor = cor + (material.ks * luz.intensidade)[None, :] * spec[:, None]

    return np.clip(cor, 0.0, 1.0)
