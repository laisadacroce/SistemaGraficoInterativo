"""Renderização da cena — laço de desenho do SGI.

Extraído de main.py para isolar o pipeline de rasterização. É aqui que o
pixel shading (framebuffer + z-buffer + iluminação) se integra, sem
inchar o main.py, que cuida da GUI e da interação.

`render_scene` recebe as dependências por parâmetro (injeção de
dependência) em vez de ler globais de main.py: assim o módulo não importa
main.py (evita import circular) e o laço fica testável isoladamente.

Dois modos de desenho:
  - Vetorial (padrão): usa as primitivas do tkinter (create_line etc.).
  - Framebuffer (Trab. 2.1+): objetos 3D são rasterizados pixel a pixel
    num Framebuffer de software e a imagem é exibida no canvas. Objetos
    2D continuam vetoriais por cima."""

from transform import scn_to_viewport
from clipping import (clip_point, cohen_sutherland, liang_barsky,
                      sutherland_hodgman, clip_curve, CLIP_MIN, CLIP_MAX)
import transform3d as t3d
from framebuffer import Framebuffer


class RenderOptions:
    """Opções de renderização vindas da UI (aba Rasterização/Shading).

    use_framebuffer — liga a rasterização por software (Trab. 2.1).
    use_zbuffer     — liga a checagem de profundidade em triângulos (2.2).
    use_phong       — liga a iluminação de Phong por pixel (2.3).
    light, material, ambient — parâmetros de iluminação (2.3)."""

    def __init__(self, use_framebuffer=False, use_zbuffer=True,
                 use_phong=False, light=None, material=None,
                 ambient=(0.2, 0.2, 0.2)):
        self.use_framebuffer = use_framebuffer
        self.use_zbuffer = use_zbuffer
        self.use_phong = use_phong
        self.light = light
        self.material = material
        self.ambient = ambient


def _hex_to_rgb(hex_color):
    """'#rrggbb' -> (r, g, b) inteiros em [0, 255]."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _get_framebuffer(canvas, width, height):
    """Devolve um Framebuffer do tamanho pedido, reaproveitando o que
    está guardado no canvas (só realoca quando a janela muda de tamanho —
    evita criar um buffer novo a cada redesenho)."""
    fb = getattr(canvas, "_framebuffer", None)
    if fb is None or fb.width != width or fb.height != height:
        fb = Framebuffer(width, height)
        canvas._framebuffer = fb
    else:
        fb.clear()
    return fb


def render_scene(canvas, display_file, window, algo, options=None):
    """Desenha a cena inteira no canvas.

    canvas        — tk.Canvas alvo
    display_file  — coleção de objetos (com a window)
    window        — câmera 3D (define projeção paralela/perspectiva)
    algo          — algoritmo de clipping de reta: "cohen-sutherland"
                    ou "liang-barsky"
    options       — RenderOptions (ou None para o modo vetorial padrão)
    """
    if options is None:
        options = RenderOptions()

    canvas.delete("all")

    # Projeção (paralela ortogonal ou em perspectiva): recalcula as
    # coordenadas SCN de todos os objetos (2D e 3D) a partir da
    # câmera 3D (window).
    display_file.project(window)

    # O viewport mapeia o SCN inteiro [-1, 1] para o canvas inteiro.
    cw = canvas.winfo_width()
    ch = canvas.winfo_height()
    if cw <= 1:
        cw = canvas.winfo_reqwidth()
    if ch <= 1:
        ch = canvas.winfo_reqheight()
    vp = (0, 0, cw, ch)

    # Modo framebuffer (Trab. 2.1+): cria/reaproveita o buffer de pixels.
    fb = _get_framebuffer(canvas, cw, ch) if options.use_framebuffer else None

    # Moldura vermelha: onde o clipping corta (guia de debug em SCN).
    mx1, my1 = scn_to_viewport(CLIP_MIN, CLIP_MAX, vp)  # top-left
    mx2, my2 = scn_to_viewport(CLIP_MAX, CLIP_MIN, vp)  # bottom-right
    canvas.create_rectangle(mx1, my1, mx2, my2,
                            outline="red", width=2)

    # A rasterização por software respeita a mesma região de clipping.
    if fb is not None:
        fb.set_clip(mx1, my1, mx2, my2)

    line_clip = cohen_sutherland if algo == "cohen-sutherland" else liang_barsky

    def draw_seg_scn(sx1, sy1, sx2, sy2, color):
        """Desenha um segmento já em pixels: no framebuffer (se ligado)
        ou como linha vetorial no canvas."""
        if fb is not None:
            fb.draw_line(sx1, sy1, sx2, sy2, _hex_to_rgb(color))
        else:
            canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

    for obj in display_file.drawable_objects():
        color = obj.color

        if obj.object_type == "point":
            if obj.normalized_coords and obj.normalized_coords[0] is not None:
                x, y = obj.normalized_coords[0]
                if clip_point(x, y):
                    sx, sy = scn_to_viewport(x, y, vp)
                    canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2,
                                       fill=color, outline=color)

        elif obj.object_type == "line":
            if (len(obj.normalized_coords) >= 2
                    and obj.normalized_coords[0] is not None
                    and obj.normalized_coords[1] is not None):
                x1, y1 = obj.normalized_coords[0]
                x2, y2 = obj.normalized_coords[1]
                result = line_clip(x1, y1, x2, y2)
                if result:
                    sx1, sy1 = scn_to_viewport(result[0], result[1], vp)
                    sx2, sy2 = scn_to_viewport(result[2], result[3], vp)
                    canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

        elif obj.object_type in ("curve", "bspline"):
            # Clipagem de curvas (Bézier e B-Spline) — point clipping
            # em cada amostra discretizada.
            if any(c is None for c in obj.normalized_coords):
                segments = []  # ponto de controle atrás do COP
            else:
                segments = clip_curve(obj.curve_points_scn())
            for seg in segments:
                for i in range(len(seg) - 1):
                    sx1, sy1 = scn_to_viewport(seg[i][0], seg[i][1], vp)
                    sx2, sy2 = scn_to_viewport(seg[i+1][0], seg[i+1][1], vp)
                    canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

        elif obj.object_type == "wireframe":
            if obj.filled:
                # Polígono preenchido — Sutherland-Hodgman (precisa fechar)
                if any(c is None for c in obj.normalized_coords):
                    clipped = []  # vértice atrás do COP
                else:
                    clipped = sutherland_hodgman(obj.normalized_coords)
                if clipped:
                    vp_points = [scn_to_viewport(x, y, vp) for x, y in clipped]
                    if len(vp_points) >= 3:
                        if fb is not None:
                            # rasteriza o preenchimento pelo framebuffer
                            fb.draw_polygon(vp_points, _hex_to_rgb(color))
                        else:
                            flat = []
                            for px, py in vp_points:
                                flat.extend([px, py])
                            canvas.create_polygon(*flat, fill=color,
                                                  outline=color)
            else:
                # Wireframe — clipa cada aresta individualmente como linha
                coords = obj.normalized_coords
                for i in range(len(coords)):
                    p1 = coords[i]
                    p2 = coords[(i + 1) % len(coords)]
                    if p1 is None or p2 is None:
                        continue  # vértice atrás do COP
                    x1, y1 = p1
                    x2, y2 = p2
                    result = line_clip(x1, y1, x2, y2)
                    if result:
                        sx1, sy1 = scn_to_viewport(result[0], result[1], vp)
                        sx2, sy2 = scn_to_viewport(result[2], result[3], vp)
                        canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

        elif obj.object_type == "point3d":
            if obj.normalized_coords and obj.normalized_coords[0] is not None:
                x, y = obj.normalized_coords[0]
                if clip_point(x, y):
                    sx, sy = scn_to_viewport(x, y, vp)
                    canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2,
                                       fill=color, outline=color)

        elif obj.object_type == "object3d":
            # Objeto 3D — cada segmento de reta é projetado das coordenadas
            # de view (com clipping de near-plane na perspectiva) e clipado
            # em 2D. No modo framebuffer, é rasterizado por Bresenham.
            vc = obj.view_coords
            for i, j in obj.segments:
                if i >= len(vc) or j >= len(vc):
                    continue
                seg = t3d.project_view_segment(vc[i], vc[j], window)
                if seg is None:
                    continue
                (x1, y1), (x2, y2) = seg
                result = line_clip(x1, y1, x2, y2)
                if result:
                    sx1, sy1 = scn_to_viewport(result[0], result[1], vp)
                    sx2, sy2 = scn_to_viewport(result[2], result[3], vp)
                    draw_seg_scn(sx1, sy1, sx2, sy2, color)

        elif obj.object_type in ("surface", "bsurface"):
            # Superfície bicúbica (Bézier 1.9 / B-Spline 1.10) — malha 3D
            # projetada segmento a segmento; rasterizada no framebuffer
            # quando o modo está ligado.
            for a, b in obj.mesh_view_segments():
                seg = t3d.project_view_segment(a, b, window)
                if seg is None:
                    continue
                (x1, y1), (x2, y2) = seg
                result = line_clip(x1, y1, x2, y2)
                if result:
                    sx1, sy1 = scn_to_viewport(result[0], result[1], vp)
                    sx2, sy2 = scn_to_viewport(result[2], result[3], vp)
                    draw_seg_scn(sx1, sy1, sx2, sy2, color)

        elif obj.object_type == "phong":
            # Objeto de triângulos com normais (Trab. 2.3). Só é
            # rasterizado no modo framebuffer. Cada vértice é projetado
            # para (x_vp, y_vp, z_view, x_mundo, y_mundo, z_mundo).
            vc = obj.view_coords
            rgb = _hex_to_rgb(color)
            eye = window.vrp
            for t in range(obj.n_triangles):
                verts = []
                ok = True
                for k in range(3):
                    idx = 3 * t + k
                    scn = t3d.project_view_point(vc[idx], window)
                    if scn is None:   # vértice atrás do COP
                        ok = False
                        break
                    px, py = scn_to_viewport(scn[0], scn[1], vp)
                    zview = vc[idx][2]
                    wx, wy, wz = obj.coordinates[idx]
                    verts.append((px, py, zview, wx, wy, wz))
                if not ok:
                    continue

                if fb is None:
                    # Sem framebuffer: mostra o arame dos triângulos.
                    for a, b in ((0, 1), (1, 2), (2, 0)):
                        canvas.create_line(verts[a][0], verts[a][1],
                                           verts[b][0], verts[b][1], fill=color)
                    continue

                n = obj.normals
                if options.use_phong and options.light and options.material:
                    fb.draw_triangle_phong(
                        verts[0], verts[1], verts[2],
                        n[3 * t], n[3 * t + 1], n[3 * t + 2],
                        options.material, options.light, eye, options.ambient)
                elif options.use_zbuffer:
                    fb.draw_triangle(verts[0][:3], verts[1][:3], verts[2][:3], rgb)
                else:
                    for a, b in ((0, 1), (1, 2), (2, 0)):
                        fb.draw_line(verts[a][0], verts[a][1],
                                     verts[b][0], verts[b][1], rgb)

    # Modo framebuffer: cola a imagem rasterizada como fundo do canvas.
    # tag_lower manda a imagem para trás, deixando a moldura de clipping e
    # os objetos 2D vetoriais visíveis por cima. A referência ao
    # PhotoImage precisa ficar viva (senão o tkinter a coleta e some).
    if fb is not None:
        photo = fb.to_photoimage()
        canvas._fb_photo = photo
        img_id = canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.tag_lower(img_id)
