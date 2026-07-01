"""Framebuffer de software para o SGI — Trabalhos 2.1 e 2.2.

Um framebuffer é uma matriz de pixels em memória onde desenhamos "na
unha" (pixel a pixel), em vez de usar as primitivas vetoriais do tkinter
(canvas.create_line etc.). É a base da rasterização: toda linha, trapézio
e polígono vira um conjunto de pixels escritos aqui.

Armazenamento (numpy, linha-major):
  - `color`: matriz (altura, largura, 3) de uint8 — cor RGB de cada pixel.
  - `depth`: matriz (altura, largura) de float — profundidade (z-buffer),
    usada só a partir do Trabalho 2.2. Inicializada em +infinito.

Para exibir no tkinter, `to_photoimage()` empacota o buffer de cor no
formato PPM (P6) e devolve um tk.PhotoImage, que o render.py desenha no
canvas com create_image."""

import base64
import math
import tkinter as tk

import numpy as np

import phong


class Framebuffer:
    def __init__(self, width, height):
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        # Buffer de cor RGB e buffer de profundidade (z-buffer, Trab. 2.2)
        self.color = np.empty((self.height, self.width, 3), dtype=np.uint8)
        self.depth = np.empty((self.height, self.width), dtype=np.float64)
        # Retângulo de recorte (em pixels): as primitivas só escrevem
        # dentro dele. Por padrão é o buffer inteiro; o render.py o ajusta
        # para a região de clipping (borda vermelha) do SGI.
        self.cx0, self.cy0 = 0, 0
        self.cx1, self.cy1 = self.width - 1, self.height - 1
        self.clear()

    def set_clip(self, x0, y0, x1, y1):
        """Define o retângulo de recorte em pixels (intersecção com o
        buffer). Fora dele nenhum pixel é escrito — é o que faz a
        rasterização respeitar a borda de clipping do SGI."""
        self.cx0 = max(0, int(min(x0, x1)))
        self.cy0 = max(0, int(min(y0, y1)))
        self.cx1 = min(self.width - 1, int(max(x0, x1)))
        self.cy1 = min(self.height - 1, int(max(y0, y1)))

    # ── Limpeza ──────────────────────────────────────────
    def clear(self, color=(255, 255, 255)):
        """Limpa o buffer de cor com `color` e reseta o z-buffer para
        +infinito (nenhum pixel escrito ainda; tudo "infinitamente longe").
        Resetar a profundidade aqui é essencial para o Z-buffer (Trab. 2.2):
        sem isso, restos do quadro anterior bloqueariam o novo desenho."""
        self.color[:, :] = color
        self.depth[:, :] = np.inf

    # ── Pixel ────────────────────────────────────────────
    def draw_pixel(self, x, y, color=(0, 0, 0)):
        """Escreve um pixel na cor dada, sem checar profundidade.
        Faz clipping trivial: ignora coordenadas fora do buffer."""
        xi = int(round(x))
        yi = int(round(y))
        if self.cx0 <= xi <= self.cx1 and self.cy0 <= yi <= self.cy1:
            self.color[yi, xi] = color

    # ── Reta (Bresenham) ─────────────────────────────────
    def draw_line(self, x0, y0, x1, y1, color=(0, 0, 0)):
        """Rasteriza uma reta pelo algoritmo de Bresenham — só aritmética
        inteira, sem ponto flutuante. A cada passo o "erro acumulado"
        decide se andamos em x, em y, ou nos dois (diagonais)."""
        x0 = int(round(x0)); y0 = int(round(y0))
        x1 = int(round(x1)); y1 = int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.draw_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    # ── Span horizontal (preenchimento rápido de uma linha) ──
    def _fill_span(self, y, x_left, x_right, color):
        """Pinta a faixa horizontal [x_left, x_right] na linha y de uma vez
        (fatiamento numpy — bem mais rápido que pixel a pixel)."""
        if y < self.cy0 or y > self.cy1:
            return
        xi0 = max(self.cx0, int(math.ceil(x_left)))
        xi1 = min(self.cx1, int(math.floor(x_right)))
        if xi1 >= xi0:
            self.color[y, xi0:xi1 + 1] = color

    # ── Trapézio alinhado ────────────────────────────────
    def draw_trapezoid(self, x0_top, x1_top, y_top,
                        x0_bot, x1_bot, y_bot, color=(0, 0, 0)):
        """Rasteriza um trapézio com os lados superior e inferior
        horizontais (alinhados ao eixo X), em y_top e y_bot.

        As bordas esquerda (x0_top→x0_bot) e direita (x1_top→x1_bot) são
        interpoladas linearmente a cada scanline; a faixa entre elas é
        preenchida. É o tijolo básico do preenchimento de polígonos e
        triângulos (que são decompostos em trapézios/triângulos)."""
        yt = int(round(y_top))
        yb = int(round(y_bot))
        if yt == yb:
            return
        # Garante varredura de cima para baixo (yt < yb)
        if yt > yb:
            yt, yb = yb, yt
            x0_top, x0_bot = x0_bot, x0_top
            x1_top, x1_bot = x1_bot, x1_top
        dy = yb - yt
        for y in range(yt, yb + 1):
            t = (y - yt) / dy
            xl = x0_top + (x0_bot - x0_top) * t
            xr = x1_top + (x1_bot - x1_top) * t
            if xl > xr:
                xl, xr = xr, xl
            self._fill_span(y, xl, xr, color)

    # ── Polígono (decomposição em trapézios por varredura) ─
    def _crossings(self, vertices, yc):
        """Interseções (x) das arestas do polígono com a scanline yc,
        ordenadas — a base da varredura (regra par-ímpar)."""
        n = len(vertices)
        xs = []
        for i in range(n):
            x0, y0 = vertices[i][0], vertices[i][1]
            x1, y1 = vertices[(i + 1) % n][0], vertices[(i + 1) % n][1]
            if y0 == y1:
                continue  # aresta horizontal não cruza
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                xs.append(x0 + (yc - y0) / (y1 - y0) * (x1 - x0))
        xs.sort()
        return xs

    def draw_polygon(self, vertices, color=(0, 0, 0)):
        """Preenche um polígono decompondo-o em TRAPÉZIOS por varredura.

        Entre cada par de scanlines consecutivas, os spans de cima e de
        baixo (interseções par-ímpar das arestas) formam trapézios, cada
        um desenhado por draw_trapezoid. Suporta polígonos convexos e
        côncavos simples. `vertices` é uma lista de (x, y)."""
        n = len(vertices)
        if n < 3:
            return
        ys = [v[1] for v in vertices]
        y_min = int(math.floor(min(ys)))
        y_max = int(math.ceil(max(ys)))
        for y in range(y_min, y_max):
            top = self._crossings(vertices, y + 0.5)
            bot = self._crossings(vertices, y + 1.5)
            pairs = (min(len(top), len(bot)) // 2) * 2
            for k in range(0, pairs, 2):
                self.draw_trapezoid(top[k], top[k + 1], y,
                                    bot[k], bot[k + 1], y + 1, color)

    # ── Z-buffer: pixel e triângulo com profundidade (Trab. 2.2) ──
    def draw_pixel_depth(self, x, y, z, color=(0, 0, 0)):
        """Escreve um pixel só se ele estiver À FRENTE do que já foi
        desenhado ali (z menor que o guardado no z-buffer). Atualiza o
        z-buffer. É a checagem de profundidade que resolve a oclusão."""
        xi = int(round(x))
        yi = int(round(y))
        if self.cx0 <= xi <= self.cx1 and self.cy0 <= yi <= self.cy1:
            if z < self.depth[yi, xi]:
                self.depth[yi, xi] = z
                self.color[yi, xi] = color

    def draw_triangle(self, v0, v1, v2, color=(0, 0, 0)):
        """Rasteriza um triângulo com checagem de profundidade (Z-buffer).

        v0, v1, v2 são (x_vp, y_vp, z_view): XY em pixels, Z na
        profundidade da câmera. Para cada pixel dentro do triângulo,
        interpola Z linearmente (coordenadas baricêntricas) e só pinta se
        passar no teste de profundidade. Vetorizado em numpy sobre a
        caixa envolvente do triângulo."""
        x0, y0, z0 = v0[0], v0[1], v0[2]
        x1, y1, z1 = v1[0], v1[1], v1[2]
        x2, y2, z2 = v2[0], v2[1], v2[2]

        minx = max(self.cx0, int(math.floor(min(x0, x1, x2))))
        maxx = min(self.cx1, int(math.ceil(max(x0, x1, x2))))
        miny = max(self.cy0, int(math.floor(min(y0, y1, y2))))
        maxy = min(self.cy1, int(math.ceil(max(y0, y1, y2))))
        if maxx < minx or maxy < miny:
            return

        # Denominador das coordenadas baricêntricas (2× a área do triângulo)
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if denom == 0:
            return  # triângulo degenerado (área zero)

        xs = np.arange(minx, maxx + 1) + 0.5   # amostra no centro do pixel
        ys = np.arange(miny, maxy + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)

        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / denom
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / denom
        l2 = 1.0 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)

        z = l0 * z0 + l1 * z1 + l2 * z2
        sub_depth = self.depth[miny:maxy + 1, minx:maxx + 1]
        mask = inside & (z < sub_depth)
        sub_depth[mask] = z[mask]
        self.color[miny:maxy + 1, minx:maxx + 1][mask] = color

    def draw_triangle_phong(self, v0, v1, v2, n0, n1, n2,
                            material, luz, olho, luz_ambiente=(0.2, 0.2, 0.2)):
        """Rasteriza um triângulo com iluminação de Phong POR PIXEL e
        Z-buffer (Trab. 2.3).

        v0/v1/v2 = (x_vp, y_vp, z_view, x_mundo, y_mundo, z_mundo)
        n0/n1/n2 = normais por vértice (mundo)

        Para cada pixel do triângulo interpola-se (baricêntrico): a
        profundidade z, a posição no mundo e a normal. Como a normal é
        interpolada e o Phong é calculado em cada pixel, isto é Phong
        shading de verdade (não Gouraud). O cálculo de cor é vetorizado."""
        x0, y0, z0 = v0[0], v0[1], v0[2]
        x1, y1, z1 = v1[0], v1[1], v1[2]
        x2, y2, z2 = v2[0], v2[1], v2[2]

        minx = max(self.cx0, int(math.floor(min(x0, x1, x2))))
        maxx = min(self.cx1, int(math.ceil(max(x0, x1, x2))))
        miny = max(self.cy0, int(math.floor(min(y0, y1, y2))))
        maxy = min(self.cy1, int(math.ceil(max(y0, y1, y2))))
        if maxx < minx or maxy < miny:
            return

        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if denom == 0:
            return

        xs = np.arange(minx, maxx + 1) + 0.5
        ys = np.arange(miny, maxy + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)

        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / denom
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / denom
        l2 = 1.0 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)

        z = l0 * z0 + l1 * z1 + l2 * z2
        sub_depth = self.depth[miny:maxy + 1, minx:maxx + 1]
        mask = inside & (z < sub_depth)
        if not mask.any():
            return

        # Pesos baricêntricos só dos pixels que passaram no teste de Z
        b0, b1, b2 = l0[mask], l1[mask], l2[mask]

        # Interpola posição no mundo e normal por pixel
        pontos = (b0[:, None] * np.array([v0[3], v0[4], v0[5]])
                  + b1[:, None] * np.array([v1[3], v1[4], v1[5]])
                  + b2[:, None] * np.array([v2[3], v2[4], v2[5]]))
        normais = (b0[:, None] * np.array(n0)
                   + b1[:, None] * np.array(n1)
                   + b2[:, None] * np.array(n2))

        cores = phong.calcular_phong_lote(pontos, normais, olho, luz,
                                          material, luz_ambiente)
        cores_255 = (cores * 255.0).astype(np.uint8)

        self.color[miny:maxy + 1, minx:maxx + 1][mask] = cores_255
        sub_depth[mask] = z[mask]

    # ── Exibição no tkinter ──────────────────────────────
    def to_photoimage(self):
        """Empacota o buffer de cor no formato PPM (P6) e devolve um
        tk.PhotoImage pronto para o canvas exibir. O PPM é
        `P6 <w> <h> 255\\n` seguido dos bytes RGB.

        Tenta primeiro passar os bytes via `data=` (base64), que é o
        caminho rápido. Algumas versões do Tk não decodificam PPM por
        `data=`; nesse caso, grava um PPM temporário e carrega via
        `file=`, que o handler PPM embutido sempre aceita."""
        header = f"P6 {self.width} {self.height} 255\n".encode("ascii")
        ppm = header + self.color.tobytes()
        try:
            return tk.PhotoImage(data=base64.b64encode(ppm))
        except tk.TclError:
            import os
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".ppm")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(ppm)
                return tk.PhotoImage(file=path)
            finally:
                os.remove(path)
