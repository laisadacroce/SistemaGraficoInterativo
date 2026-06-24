import math
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from model import (DisplayFile, Window, Point, Line, Wireframe, Curve2D,
                    BSpline, Point3D, Object3D, BezierSurface, BSplineSurface)
from transform import (scn_to_viewport, apply_transform,
                        compose_matrices, translation_matrix,
                        natural_scaling_matrix, rotation_matrix,
                        rotation_around_center_matrix,
                        rotation_around_point_matrix)
import transform3d as t3d
from obj_io import save_obj, load_obj, load_obj_3d
from clipping import (clip_point, cohen_sutherland, liang_barsky,
                       sutherland_hodgman, clip_curve,
                       CLIP_MIN, CLIP_MAX)

window = Window(-300, -300, 300, 300)
display_file = DisplayFile(window)

root = tk.Tk()
root.title("Sistema Gráfico Interativo - INE5420")

# ── Left panel ───────────────────────────────────────────
panel = tk.Frame(root, width=200, bg="lightgray")
panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

# Section: object list
tk.Label(panel, text="Objects", bg="lightgray", anchor="w").pack(fill=tk.X)
object_listbox = tk.Listbox(panel, height=6)
object_listbox.pack(fill=tk.X, pady=(0, 10))

# Section: Window controls
window_frame = tk.LabelFrame(panel, text="Window", bg="lightgray")
window_frame.pack(fill=tk.X, pady=5)

# Step size
step_frame = tk.Frame(window_frame, bg="lightgray")
step_frame.pack(fill=tk.X, padx=5, pady=2)
tk.Label(step_frame, text="Step:", bg="lightgray").pack(side=tk.LEFT)
step_entry = tk.Entry(step_frame, width=5)
step_entry.insert(0, "10")
step_entry.pack(side=tk.LEFT)
tk.Label(step_frame, text="%", bg="lightgray").pack(side=tk.LEFT)

def get_step():
    return float(step_entry.get()) / 100

# Pan / Zoom functions
def pan(dx, dy):
    window.pan(dx, dy, get_step())
    redraw()

def zoom(factor):
    window.zoom(factor, get_step())
    redraw()

def reset():
    window.reset()
    redraw()

# Pan buttons
tk.Button(window_frame, text="Up",    command=lambda: pan(0, 1)).pack(pady=1)

left_right_frame = tk.Frame(window_frame, bg="lightgray")
left_right_frame.pack()
tk.Button(left_right_frame, text="Left",  command=lambda: pan(-1, 0)).pack(side=tk.LEFT, padx=2)
tk.Button(left_right_frame, text="Right", command=lambda: pan(1, 0)).pack(side=tk.LEFT, padx=2)

tk.Button(window_frame, text="Down",  command=lambda: pan(0, -1)).pack(pady=1)

# Zoom buttons
zoom_frame = tk.Frame(window_frame, bg="lightgray")
zoom_frame.pack(pady=5)
tk.Label(zoom_frame, text="Zoom", bg="lightgray").pack(side=tk.LEFT, padx=5)
tk.Button(zoom_frame, text="+", width=3, command=lambda: zoom(1)).pack(side=tk.LEFT, padx=2)
tk.Button(zoom_frame, text="-", width=3, command=lambda: zoom(-1)).pack(side=tk.LEFT, padx=2)

# Window rotation
rotate_frame = tk.Frame(window_frame, bg="lightgray")
rotate_frame.pack(fill=tk.X, padx=5, pady=2)
tk.Label(rotate_frame, text="Rotate:", bg="lightgray").pack(side=tk.LEFT)
rotate_entry = tk.Entry(rotate_frame, width=5)
rotate_entry.insert(0, "15")
rotate_entry.pack(side=tk.LEFT)
tk.Label(rotate_frame, text="\u00b0", bg="lightgray").pack(side=tk.LEFT)

def rotate_window(direction):
    try:
        angle = float(rotate_entry.get()) * direction
        window.rotate(angle)
        redraw()
    except ValueError:
        pass

rotate_btn_frame = tk.Frame(window_frame, bg="lightgray")
rotate_btn_frame.pack(pady=2)
tk.Button(rotate_btn_frame, text="\u21b6", width=3,
          command=lambda: rotate_window(1)).pack(side=tk.LEFT, padx=2)
tk.Button(rotate_btn_frame, text="\u21b7", width=3,
          command=lambda: rotate_window(-1)).pack(side=tk.LEFT, padx=2)

tk.Button(window_frame, text="Reset", command=reset).pack(pady=5)

# Section: 3D camera navigation
camera_frame = tk.LabelFrame(panel, text="Camera 3D", bg="lightgray")
camera_frame.pack(fill=tk.X, pady=5)

def camera_move_forward(factor):
    """Move a câmera ao longo do VPN (frente/trás)."""
    window.move_forward(factor, get_step())
    redraw()

def camera_pitch(direction):
    """Inclina a câmera para cima/baixo (gira VPN/VUP em torno do
    eixo horizontal da câmera)."""
    try:
        window.pitch(float(rotate_entry.get()) * direction)
        redraw()
    except ValueError:
        pass

def camera_yaw(direction):
    """Gira a câmera para os lados (gira o VPN em torno do VUP)."""
    try:
        window.yaw(float(rotate_entry.get()) * direction)
        redraw()
    except ValueError:
        pass

fwd_frame = tk.Frame(camera_frame, bg="lightgray")
fwd_frame.pack(pady=2)
tk.Label(fwd_frame, text="Move", bg="lightgray", width=6).pack(side=tk.LEFT)
tk.Button(fwd_frame, text="Forward",
          command=lambda: camera_move_forward(1)).pack(side=tk.LEFT, padx=2)
tk.Button(fwd_frame, text="Back",
          command=lambda: camera_move_forward(-1)).pack(side=tk.LEFT, padx=2)

pitch_frame = tk.Frame(camera_frame, bg="lightgray")
pitch_frame.pack(pady=2)
tk.Label(pitch_frame, text="Pitch", bg="lightgray", width=6).pack(side=tk.LEFT)
tk.Button(pitch_frame, text="↑", width=3,
          command=lambda: camera_pitch(1)).pack(side=tk.LEFT, padx=2)
tk.Button(pitch_frame, text="↓", width=3,
          command=lambda: camera_pitch(-1)).pack(side=tk.LEFT, padx=2)

yaw_frame = tk.Frame(camera_frame, bg="lightgray")
yaw_frame.pack(pady=2)
tk.Label(yaw_frame, text="Yaw", bg="lightgray", width=6).pack(side=tk.LEFT)
tk.Button(yaw_frame, text="←", width=3,
          command=lambda: camera_yaw(1)).pack(side=tk.LEFT, padx=2)
tk.Button(yaw_frame, text="→", width=3,
          command=lambda: camera_yaw(-1)).pack(side=tk.LEFT, padx=2)

tk.Label(camera_frame, text="(Pan/Zoom/Rotate acima também\n"
         "operam a câmera no espaço 3D)", bg="lightgray",
         font=("", 7)).pack(pady=2)

# Section: projection mode (parallel / perspective)
projection_frame = tk.LabelFrame(panel, text="Projection", bg="lightgray")
projection_frame.pack(fill=tk.X, pady=5)

projection_var = tk.StringVar(value="parallel")

def set_projection_mode():
    window.projection_mode = projection_var.get()
    redraw()

tk.Radiobutton(projection_frame, text="Parallel (orthogonal)",
               variable=projection_var, value="parallel", bg="lightgray",
               command=set_projection_mode).pack(anchor="w")
tk.Radiobutton(projection_frame, text="Perspective",
               variable=projection_var, value="perspective", bg="lightgray",
               command=set_projection_mode).pack(anchor="w")

cop_frame = tk.Frame(projection_frame, bg="lightgray")
cop_frame.pack(fill=tk.X, padx=5, pady=2)
tk.Label(cop_frame, text="COP dist:", bg="lightgray").pack(side=tk.LEFT)
cop_entry = tk.Entry(cop_frame, width=7)
cop_entry.insert(0, str(int(window.cop_distance)))
cop_entry.pack(side=tk.LEFT, padx=2)

def refresh_cop_entry():
    cop_entry.delete(0, tk.END)
    cop_entry.insert(0, str(int(window.cop_distance)))

def set_cop_distance():
    """Define a distância do Centro de Projeção ao plano de projeção."""
    try:
        d = float(cop_entry.get())
        if d > 0:
            window.cop_distance = d
            redraw()
    except ValueError:
        pass

tk.Button(cop_frame, text="Set", command=set_cop_distance).pack(side=tk.LEFT)

def scale_cop(factor):
    """Aproxima/afasta o COP: menor distância = grande angular,
    maior distância = teleobjetiva."""
    window.cop_distance = max(1.0, window.cop_distance * factor)
    refresh_cop_entry()
    redraw()

cop_btn_frame = tk.Frame(projection_frame, bg="lightgray")
cop_btn_frame.pack(pady=2)
tk.Button(cop_btn_frame, text="Wide angle",
          command=lambda: scale_cop(1 / 1.5)).pack(side=tk.LEFT, padx=2)
tk.Button(cop_btn_frame, text="Telephoto",
          command=lambda: scale_cop(1.5)).pack(side=tk.LEFT, padx=2)

# Section: Clipping algorithm selection
clip_frame = tk.LabelFrame(panel, text="Line Clipping", bg="lightgray")
clip_frame.pack(fill=tk.X, pady=5)

clip_algorithm = tk.StringVar(value="cohen-sutherland")
tk.Radiobutton(clip_frame, text="Cohen-Sutherland", variable=clip_algorithm,
               value="cohen-sutherland", bg="lightgray",
               command=lambda: redraw()).pack(anchor="w")
tk.Radiobutton(clip_frame, text="Liang-Barsky", variable=clip_algorithm,
               value="liang-barsky", bg="lightgray",
               command=lambda: redraw()).pack(anchor="w")

# ── Canvas (viewport) ────────────────────────────────────
canvas = tk.Canvas(root, width=800, height=800, bg="white",
                   highlightthickness=1, highlightbackground="gray")
canvas.pack(side=tk.LEFT, padx=10, pady=10)

def redraw():
    canvas.delete("all")

    # Projeção (paralela ortogonal ou em perspectiva): recalcula as
    # coordenadas SCN de todos os objetos (2D e 3D) a partir da
    # câmera 3D (window).
    display_file.project(window)

    # O viewport mapeia o SCN inteiro [-1, 1] para o canvas inteiro.
    # A moldura vermelha mostra visualmente onde o clipping corta
    # (em [-0.90, 0.90] no SCN), servindo como ferramenta de debug.
    cw = canvas.winfo_width()
    ch = canvas.winfo_height()
    if cw <= 1:
        cw = canvas.winfo_reqwidth()
    if ch <= 1:
        ch = canvas.winfo_reqheight()
    vp = (0, 0, cw, ch)

    # Desenhar moldura vermelha na posição correspondente ao clipping
    # CLIP_MIN/MAX em SCN mapeados para pixels
    mx1, my1 = scn_to_viewport(CLIP_MIN, CLIP_MAX, vp)  # top-left
    mx2, my2 = scn_to_viewport(CLIP_MAX, CLIP_MIN, vp)  # bottom-right
    canvas.create_rectangle(mx1, my1, mx2, my2,
                            outline="red", width=2)

    algo = clip_algorithm.get()

    for obj in display_file.drawable_objects():
        color = obj.color

        if obj.object_type == "point":
            if obj.normalized_coords and obj.normalized_coords[0] is not None:
                x, y = obj.normalized_coords[0]
                # Clipagem de pontos
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
                # Clipagem de retas — algoritmo selecionado pelo usuário
                if algo == "cohen-sutherland":
                    result = cohen_sutherland(x1, y1, x2, y2)
                else:
                    result = liang_barsky(x1, y1, x2, y2)
                if result:
                    sx1, sy1 = scn_to_viewport(result[0], result[1], vp)
                    sx2, sy2 = scn_to_viewport(result[2], result[3], vp)
                    canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

        elif obj.object_type in ("curve", "bspline"):
            # Clipagem de curvas (Bézier e B-Spline) — point clipping
            # em cada amostra discretizada.
            # Trechos contíguos visíveis viram linhas conectadas.
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
                        flat = []
                        for px, py in vp_points:
                            flat.extend([px, py])
                        canvas.create_polygon(*flat, fill=color,
                                              outline=color)
            else:
                # Wireframe — clipa cada aresta individualmente como linha
                line_clip = cohen_sutherland if algo == "cohen-sutherland" else liang_barsky
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
            # Ponto 3D — já projetado para SCN; clipagem de ponto.
            # normalized_coords[0] pode ser None se estiver atrás do COP.
            if obj.normalized_coords and obj.normalized_coords[0] is not None:
                x, y = obj.normalized_coords[0]
                if clip_point(x, y):
                    sx, sy = scn_to_viewport(x, y, vp)
                    canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2,
                                       fill=color, outline=color)

        elif obj.object_type == "object3d":
            # Objeto 3D — cada segmento de reta é projetado a partir das
            # coordenadas de view (com clipping de near-plane na
            # perspectiva) e depois clipado em 2D como linha.
            line_clip = cohen_sutherland if algo == "cohen-sutherland" else liang_barsky
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
                    canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

        elif obj.object_type in ("surface", "bsurface"):
            # Superfície bicúbica (Bézier 1.9 ou B-Spline por forward
            # differences 1.10) — a malha 3D (iso-curvas) é gerada em
            # coordenadas de view e cada segmento é projetado (com
            # near-plane na perspectiva) e clipado em 2D como linha.
            line_clip = cohen_sutherland if algo == "cohen-sutherland" else liang_barsky
            for a, b in obj.mesh_view_segments():
                seg = t3d.project_view_segment(a, b, window)
                if seg is None:
                    continue
                (x1, y1), (x2, y2) = seg
                result = line_clip(x1, y1, x2, y2)
                if result:
                    sx1, sy1 = scn_to_viewport(result[0], result[1], vp)
                    sx2, sy2 = scn_to_viewport(result[2], result[3], vp)
                    canvas.create_line(sx1, sy1, sx2, sy2, fill=color)

# ── Add object dialog ────────────────────────────────────

def parse_surface_patches(raw):
    """Converte o texto da aba Surface em uma lista de retalhos.

    Formato (mesmo padrão dos outros objetos, com as linhas da matriz
    separadas por ';'): 4 pontos (x,y,z) por linha. Cada grupo de 4
    linhas (4x4 = 16 pontos) forma um retalho; basta repetir para entrar
    com mais retalhos. Retorna uma lista de retalhos, cada um com 16
    tuplas (x, y, z)."""
    rows = [r.strip() for r in raw.split(";") if r.strip()]
    parsed_rows = []
    for r in rows:
        value = eval(r)
        # Normaliza uma linha com um único ponto "(x,y,z)" para sequência
        if value and isinstance(value[0], (int, float)):
            value = (value,)
        parsed_rows.append([tuple(float(c) for c in pt) for pt in value])

    if not parsed_rows or len(parsed_rows) % 4 != 0:
        raise ValueError("o número de linhas deve ser múltiplo de 4")
    for points in parsed_rows:
        if len(points) != 4 or any(len(pt) != 3 for pt in points):
            raise ValueError("cada linha precisa de 4 pontos (x,y,z)")

    patches = []
    for k in range(0, len(parsed_rows), 4):
        patch = []
        for r in range(4):
            patch.extend(parsed_rows[k + r])
        patches.append(patch)  # 16 pontos de controle
    return patches


def parse_bspline_grid(raw):
    """Converte o texto da aba B-Spline Surf numa matriz n×m de pontos
    de controle (lista de linhas; cada linha é uma lista de tuplas
    (x, y, z)). Linhas separadas por ';', pontos (x,y,z) por linha.
    Todas as linhas precisam do mesmo número de colunas; a dimensão deve
    ficar entre 4x4 e 20x20 — a subdivisão em retalhos é automática."""
    rows = [r.strip() for r in raw.split(";") if r.strip()]
    grid = []
    for r in rows:
        value = eval(r)
        if value and isinstance(value[0], (int, float)):
            value = (value,)  # linha com um único ponto "(x,y,z)"
        grid.append([tuple(float(c) for c in pt) for pt in value])

    if not grid:
        raise ValueError("matriz de controle vazia")
    n_cols = len(grid[0])
    if any(len(row) != n_cols for row in grid):
        raise ValueError("todas as linhas precisam do mesmo número de pontos")
    if any(len(pt) != 3 for row in grid for pt in row):
        raise ValueError("cada ponto precisa de (x, y, z)")
    if not BSplineSurface.valid_dims(len(grid), n_cols):
        raise ValueError("a matriz deve ter entre 4x4 e 20x20 pontos")
    return grid


def open_add_object_dialog():
    dialog = tk.Toplevel(root)
    dialog.title("Add Object")
    dialog.grab_set()

    # Name field
    name_frame = tk.Frame(dialog)
    name_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Label(name_frame, text="Name").pack(side=tk.LEFT)
    name_entry = tk.Entry(name_frame)
    name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # Color field
    color_frame = tk.Frame(dialog)
    color_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Label(color_frame, text="Color").pack(side=tk.LEFT)
    color_var = tk.StringVar(value="#000000")
    color_preview = tk.Label(color_frame, bg="#000000", width=3)
    color_preview.pack(side=tk.RIGHT, padx=5)
    color_entry = tk.Entry(color_frame, textvariable=color_var, width=10)
    color_entry.pack(side=tk.LEFT, padx=5)

    def pick_color():
        result = colorchooser.askcolor(color=color_var.get(), parent=dialog)
        if result[1]:
            color_var.set(result[1])
            color_preview.config(bg=result[1])

    tk.Button(color_frame, text="Pick", command=pick_color).pack(side=tk.LEFT)

    def on_color_change(*args):
        try:
            color_preview.config(bg=color_var.get())
        except tk.TclError:
            pass
    color_var.trace_add("write", on_color_change)

    # Type tabs
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    point_tab     = tk.Frame(notebook)
    line_tab      = tk.Frame(notebook)
    wireframe_tab = tk.Frame(notebook)
    curve_tab     = tk.Frame(notebook)
    bspline_tab   = tk.Frame(notebook)
    object3d_tab  = tk.Frame(notebook)
    surface_tab   = tk.Frame(notebook)
    bsurface_tab  = tk.Frame(notebook)

    notebook.add(point_tab,     text="Point")
    notebook.add(line_tab,      text="Line")
    notebook.add(wireframe_tab, text="Wireframe")
    notebook.add(curve_tab,     text="Curve")
    notebook.add(bspline_tab,   text="B-Spline")
    notebook.add(object3d_tab,  text="3D Object")
    notebook.add(surface_tab,   text="Surface")
    notebook.add(bsurface_tab,  text="B-Spline Surf")

    # Point tab
    tk.Label(point_tab, text="Coordinates:").pack(pady=5)
    tk.Label(point_tab, text="(x, y)").pack()
    point_entry = tk.Entry(point_tab, width=30)
    point_entry.pack(pady=5)

    # Line tab
    tk.Label(line_tab, text="Coordinates:").pack(pady=5)
    tk.Label(line_tab, text="(x1,y1),(x2,y2)").pack()
    line_entry = tk.Entry(line_tab, width=30)
    line_entry.pack(pady=5)

    # Wireframe tab
    tk.Label(wireframe_tab, text="Coordinates:").pack(pady=5)
    tk.Label(wireframe_tab, text="(x1,y1),(x2,y2),(x3,y3),...").pack()
    wireframe_entry = tk.Entry(wireframe_tab, width=30)
    wireframe_entry.pack(pady=5)
    filled_var = tk.BooleanVar(value=False)
    tk.Checkbutton(wireframe_tab, text="Filled", variable=filled_var).pack(pady=5)

    # Curve tab
    tk.Label(curve_tab, text="Bézier Curve (G(0) continuity)").pack(pady=5)
    tk.Label(curve_tab, text="Points: 4, 7, 10, 13, ... (3k+1)").pack()
    tk.Label(curve_tab, text="(x1,y1),(x2,y2),(x3,y3),(x4,y4),...").pack()
    curve_entry = tk.Entry(curve_tab, width=30)
    curve_entry.pack(pady=5)

    # B-Spline tab
    tk.Label(bspline_tab, text="B-Spline (Forward Differences)").pack(pady=5)
    tk.Label(bspline_tab, text="Points: any number >= 4").pack()
    tk.Label(bspline_tab, text="(x1,y1),(x2,y2),(x3,y3),(x4,y4),...").pack()
    bspline_entry = tk.Entry(bspline_tab, width=30)
    bspline_entry.pack(pady=5)

    # 3D Object tab — modelo de arame: vértices 3D + segmentos de reta
    tk.Label(object3d_tab, text="3D Wireframe Object").pack(pady=5)
    tk.Label(object3d_tab, text="Vertices: (x1,y1,z1),(x2,y2,z2),...").pack()
    object3d_verts_entry = tk.Entry(object3d_tab, width=46)
    object3d_verts_entry.insert(0,
        "(-100,-100,-100),(100,-100,-100),(100,100,-100),(-100,100,-100),"
        "(-100,-100,100),(100,-100,100),(100,100,100),(-100,100,100)")
    object3d_verts_entry.pack(pady=3)
    tk.Label(object3d_tab,
             text="Edges (segmentos): pares de índices (i,j),(i,j),...").pack()
    object3d_edges_entry = tk.Entry(object3d_tab, width=46)
    object3d_edges_entry.insert(0,
        "(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),"
        "(0,4),(1,5),(2,6),(3,7)")
    object3d_edges_entry.pack(pady=3)
    tk.Label(object3d_tab,
             text="(o exemplo acima desenha um cubo)").pack()

    # Surface tab — superfície bicúbica de Bézier (16 pontos / retalho)
    tk.Label(surface_tab, text="Bicubic Bézier Surface (3D)").pack(pady=3)
    tk.Label(surface_tab,
             text="Linhas da matriz separadas por ';', 4 pontos (x,y,z) "
                  "por linha,\n4 linhas (4x4 = 16) por retalho. Repita "
                  "para mais retalhos.").pack()
    surface_text = tk.Text(surface_tab, width=52, height=8)
    surface_text.insert("1.0",
        "(-150,-150,0),(-50,-150,100),(50,-150,100),(150,-150,0);\n"
        "(-150,-50,100),(-50,-50,200),(50,-50,200),(150,-50,100);\n"
        "(-150,50,100),(-50,50,200),(50,50,200),(150,50,100);\n"
        "(-150,150,0),(-50,150,100),(50,150,100),(150,150,0)")
    surface_text.pack(pady=3, padx=5)
    tk.Label(surface_tab,
             text="(o exemplo acima desenha um retalho em forma de bossa)").pack()

    # B-Spline Surface tab — matriz n×m (4..20) por Forward Differences
    tk.Label(bsurface_tab, text="Bicubic B-Spline Surface (Forward Differences)").pack(pady=3)
    tk.Label(bsurface_tab,
             text="Matriz de controle n×m (4x4 até 20x20). Linhas separadas\n"
                  "por ';', pontos (x,y,z) por linha. Subdivisão automática.").pack()
    bsurface_text = tk.Text(bsurface_tab, width=52, height=8)
    bsurface_text.insert("1.0",
        "(-200,-200,0),(-100,-200,0),(0,-200,0),(100,-200,0),(200,-200,0);\n"
        "(-200,-100,0),(-100,-100,200),(0,-100,200),(100,-100,200),(200,-100,0);\n"
        "(-200,0,0),(-100,0,200),(0,0,300),(100,0,200),(200,0,0);\n"
        "(-200,100,0),(-100,100,200),(0,100,200),(100,100,200),(200,100,0);\n"
        "(-200,200,0),(-100,200,0),(0,200,0),(100,200,0),(200,200,0)")
    bsurface_text.pack(pady=3, padx=5)
    tk.Label(bsurface_tab,
             text="(exemplo: malha 5x5 → 2x2 = 4 retalhos)").pack()

    def on_ok():
        name = name_entry.get().strip()
        if not name:
            messagebox.showwarning("Missing name",
                "Please enter a name for the object.", parent=dialog)
            return

        if display_file.has_name(name):
            messagebox.showwarning("Duplicate name",
                f"An object named '{name}' already exists.", parent=dialog)
            return

        tab = notebook.index(notebook.select())
        color = color_var.get()

        try:
            if tab == 0: # Point
                # Espera: (x, y)
                raw = point_entry.get().strip()
                coords = list(eval(raw))
                if len(coords) != 2 or not all(isinstance(c, (int, float)) for c in coords):
                    raise ValueError
                obj = Point(name, float(coords[0]), float(coords[1]))

            elif tab == 1: # Line
                # Espera: (x1,y1),(x2,y2)
                raw = line_entry.get().strip()
                coords = list(eval(raw))
                if len(coords) != 2:
                    raise ValueError
                p1 = Point("", float(coords[0][0]), float(coords[0][1]))
                p2 = Point("", float(coords[1][0]), float(coords[1][1]))
                obj = Line(name, p1, p2)

            elif tab == 2: # Wireframe
                # Espera: (x1,y1),(x2,y2),(x3,y3),...
                raw = wireframe_entry.get().strip()
                coords = list(eval(raw))
                if len(coords) < 3:
                    raise ValueError
                points = [Point("", float(c[0]), float(c[1])) for c in coords]
                obj = Wireframe(name, points, filled=filled_var.get())

            elif tab == 3: # Curve
                coords = list(eval(curve_entry.get()))
                if not Curve2D.valid_point_count(len(coords)):
                    messagebox.showerror("Invalid point count",
                        f"A curva precisa de 4, 7, 10, 13, ... pontos (3k+1). "
                        f"Recebido: {len(coords)}", parent=dialog)
                    return
                points = [Point("", c[0], c[1]) for c in coords]
                obj = Curve2D(name, points)

            elif tab == 4: # B-Spline
                coords = list(eval(bspline_entry.get()))
                if not BSpline.valid_point_count(len(coords)):
                    messagebox.showerror("Invalid point count",
                        f"A B-Spline precisa de no mínimo 4 pontos de "
                        f"controle. Recebido: {len(coords)}", parent=dialog)
                    return
                points = [Point("", c[0], c[1]) for c in coords]
                obj = BSpline(name, points)

            elif tab == 5: # Object3D
                verts = list(eval(object3d_verts_entry.get()))
                edges = list(eval(object3d_edges_entry.get()))
                if len(verts) < 2 or not edges:
                    raise ValueError
                n = len(verts)
                for i, j in edges:
                    if not (0 <= i < n and 0 <= j < n):
                        messagebox.showerror("Invalid edge",
                            f"Índice de segmento fora do intervalo "
                            f"0..{n - 1}: ({i}, {j})", parent=dialog)
                        return
                points = [Point3D("", float(v[0]), float(v[1]), float(v[2]))
                          for v in verts]
                obj = Object3D(name, points, edges)

            elif tab == 6: # Surface (bicubic Bézier)
                patches = parse_surface_patches(surface_text.get("1.0", tk.END))
                obj = BezierSurface(name, patches)

            elif tab == 7: # B-Spline Surface (forward differences)
                grid = parse_bspline_grid(bsurface_text.get("1.0", tk.END))
                obj = BSplineSurface(name, grid)
        except Exception:
            messagebox.showerror("Invalid input",
                "Could not parse coordinates. Check the format.", parent=dialog)
            return

        obj.color = color
        display_file.add(obj)
        object_listbox.insert(tk.END, str(obj))
        redraw()
        dialog.destroy()

    # OK / Cancel buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    tk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT)

tk.Button(panel, text="Add Object", command=open_add_object_dialog).pack(fill=tk.X, pady=2)

def delete_selected_object():
    selection = object_listbox.curselection()
    if not selection:
        return
    index = selection[0]
    name = object_listbox.get(index).split("[")[1].split("]")[0]
    display_file.remove(name)
    object_listbox.delete(index)
    redraw()

tk.Button(panel, text="Delete Object", command=delete_selected_object).pack(fill=tk.X, pady=2)

# ── Transform dialog ─────────────────────────────────────

def get_selected_object():
    """Returns the selected drawable object, or None."""
    selection = object_listbox.curselection()
    if not selection:
        return None
    name = object_listbox.get(selection[0]).split("[")[1].split("]")[0]
    return display_file.get_by_name(name)

def open_transform_dialog():
    obj = get_selected_object()
    if obj is None:
        messagebox.showinfo("No selection", "Select an object from the list first.")
        return

    is_3d = obj.object_type in ("object3d", "point3d", "surface", "bsurface")

    dialog = tk.Toplevel(root)
    dialog.title(f"Transform: {obj}")
    dialog.grab_set()

    pending = []

    # ── Left side: transformation input ──
    input_frame = tk.Frame(dialog)
    input_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

    tk.Label(input_frame, text="Transformation:").pack(anchor="w")
    if is_3d:
        type_values = [
            "Translation",
            "Scaling",
            "Rotation X (object center)",
            "Rotation Y (object center)",
            "Rotation Z (object center)",
            "Rotation - Arbitrary axis",
        ]
    else:
        type_values = [
            "Translation",
            "Scaling",
            "Rotation - World center",
            "Rotation - Object center",
            "Rotation - Arbitrary point",
        ]
    transform_type = ttk.Combobox(input_frame, state="readonly",
                                  values=type_values)
    transform_type.set(type_values[0])
    transform_type.pack(fill=tk.X, pady=5)

    params_frame = tk.Frame(input_frame)
    params_frame.pack(fill=tk.X, pady=5)
    param_entries = {}

    def update_params(*args):
        for widget in params_frame.winfo_children():
            widget.destroy()
        param_entries.clear()

        choice = transform_type.get()

        if choice == "Translation":
            labels = [("Dx:", "dx"), ("Dy:", "dy")]
            if is_3d:
                labels.append(("Dz:", "dz"))
        elif choice == "Scaling":
            labels = [("Sx:", "sx"), ("Sy:", "sy")]
            if is_3d:
                labels.append(("Sz:", "sz"))
        elif choice == "Rotation - Arbitrary point":
            labels = [("Angle:", "angle"), ("Px:", "px"), ("Py:", "py")]
        elif choice == "Rotation - Arbitrary axis":
            labels = [("Angle:", "angle"),
                      ("Px:", "px"), ("Py:", "py"), ("Pz:", "pz"),
                      ("Dir x:", "dx"), ("Dir y:", "dy"), ("Dir z:", "dz")]
        elif "Rotation" in choice:
            # rotações definidas apenas por um ângulo
            labels = [("Angle:", "angle")]
        else:
            labels = []

        for row, (text, key) in enumerate(labels):
            tk.Label(params_frame, text=text).grid(row=row, column=0, sticky="w")
            entry = tk.Entry(params_frame, width=10)
            entry.grid(row=row, column=1, padx=5)
            param_entries[key] = entry

    transform_type.bind("<<ComboboxSelected>>", update_params)
    update_params()

    # ── Right side: pending list ──
    list_frame = tk.Frame(dialog)
    list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)

    tk.Label(list_frame, text="Pending transformations:").pack(anchor="w")
    pending_listbox = tk.Listbox(list_frame, height=10, width=30)
    pending_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

    # ── Builder functions ──
    def build_translation():
        dx = float(param_entries["dx"].get())
        dy = float(param_entries["dy"].get())
        # Rotate (dx, dy) by the window angle so the translation is
        # relative to the user's view, not world axes
        angle = window.angle
        if angle != 0:
            rad = math.radians(angle)
            cos = math.cos(rad)
            sin = math.sin(rad)
            dx_world = dx * cos - dy * sin
            dy_world = dx * sin + dy * cos
        else:
            dx_world, dy_world = dx, dy
        return translation_matrix(dx_world, dy_world), f"Translate ({dx}, {dy})"

    def build_scaling():
        sx = float(param_entries["sx"].get())
        sy = float(param_entries["sy"].get())
        return natural_scaling_matrix(sx, sy, obj), f"Scale ({sx}, {sy})"

    def build_rotation_world():
        angle = float(param_entries["angle"].get())
        return rotation_matrix(angle), f"Rotate {angle}\u00b0 (world)"

    def build_rotation_center():
        angle = float(param_entries["angle"].get())
        return rotation_around_center_matrix(angle, obj), f"Rotate {angle}\u00b0 (object)"

    def build_rotation_point():
        angle = float(param_entries["angle"].get())
        px = float(param_entries["px"].get())
        py = float(param_entries["py"].get())
        return rotation_around_point_matrix(angle, px, py), f"Rotate {angle}\u00b0 around ({px}, {py})"

    # ── Builders 3D (matrizes 4x4) ──
    def build_translation_3d():
        dx = float(param_entries["dx"].get())
        dy = float(param_entries["dy"].get())
        dz = float(param_entries["dz"].get())
        return (t3d.translation_matrix(dx, dy, dz),
                f"Translate ({dx}, {dy}, {dz})")

    def build_scaling_3d():
        sx = float(param_entries["sx"].get())
        sy = float(param_entries["sy"].get())
        sz = float(param_entries["sz"].get())
        return (t3d.natural_scaling_matrix(sx, sy, sz, obj),
                f"Scale ({sx}, {sy}, {sz})")

    def build_rotation_axis_3d(axis):
        angle = float(param_entries["angle"].get())
        return (t3d.rotation_around_center_matrix(angle, axis, obj),
                f"Rotate {angle}° ({axis.upper()}, center)")

    def build_rotation_arbitrary_3d():
        angle = float(param_entries["angle"].get())
        point = (float(param_entries["px"].get()),
                 float(param_entries["py"].get()),
                 float(param_entries["pz"].get()))
        direction = (float(param_entries["dx"].get()),
                     float(param_entries["dy"].get()),
                     float(param_entries["dz"].get()))
        if t3d.length(direction) == 0:
            raise ValueError("direção do eixo não pode ser nula")
        return (t3d.rotation_around_axis_matrix(angle, point, direction),
                f"Rotate {angle}° around arbitrary axis")

    if is_3d:
        builders = {
            "Translation": build_translation_3d,
            "Scaling": build_scaling_3d,
            "Rotation X (object center)": lambda: build_rotation_axis_3d("x"),
            "Rotation Y (object center)": lambda: build_rotation_axis_3d("y"),
            "Rotation Z (object center)": lambda: build_rotation_axis_3d("z"),
            "Rotation - Arbitrary axis": build_rotation_arbitrary_3d,
        }
    else:
        builders = {
            "Translation": build_translation,
            "Scaling": build_scaling,
            "Rotation - World center": build_rotation_world,
            "Rotation - Object center": build_rotation_center,
            "Rotation - Arbitrary point": build_rotation_point,
        }

    def add_transform():
        try:
            matrix, desc = builders[transform_type.get()]()
        except (ValueError, KeyError):
            messagebox.showerror("Invalid input",
                "Please enter valid numbers.", parent=dialog)
            return
        pending.append(matrix)
        pending_listbox.insert(tk.END, desc)

    def remove_transform():
        sel = pending_listbox.curselection()
        if sel:
            pending.pop(sel[0])
            pending_listbox.delete(sel[0])

    def apply_transforms():
        if pending:
            if is_3d:
                # Objetos 3D: compõe e aplica matrizes 4x4
                final_matrix = t3d.compose_matrices(pending)
                t3d.apply_transform_3d(obj, final_matrix)
            else:
                final_matrix = compose_matrices(pending)
                apply_transform(obj, final_matrix)
            redraw()
        dialog.destroy()

    btn_frame = tk.Frame(input_frame)
    btn_frame.pack(fill=tk.X, pady=10)
    tk.Button(btn_frame, text="Add", command=add_transform).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Remove", command=remove_transform).pack(side=tk.LEFT, padx=2)

    bottom_frame = tk.Frame(dialog)
    bottom_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Button(bottom_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    tk.Button(bottom_frame, text="Apply", command=apply_transforms).pack(side=tk.RIGHT)

tk.Button(panel, text="Transform", command=open_transform_dialog).pack(fill=tk.X, pady=2)

# ── OBJ import/export ────────────────────────────────────

def do_save_obj():
    filepath = filedialog.asksaveasfilename(
        defaultextension=".obj",
        filetypes=[("Wavefront OBJ", "*.obj")],
        title="Save world as .obj")
    if filepath:
        try:
            save_obj(filepath, display_file)
            messagebox.showinfo("Saved", f"World saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

def do_load_obj():
    filepath = filedialog.askopenfilename(
        filetypes=[("Wavefront OBJ", "*.obj")],
        title="Load world from .obj")
    if filepath:
        try:
            objects = load_obj(filepath)
            for obj in objects:
                if not display_file.has_name(obj.name):
                    display_file.add(obj)
                    object_listbox.insert(tk.END, str(obj))
            redraw()
        except Exception as e:
            messagebox.showerror("Error", str(e))

def do_load_obj_3d():
    filepath = filedialog.askopenfilename(
        filetypes=[("Wavefront OBJ", "*.obj")],
        title="Load 3D wireframe from .obj")
    if filepath:
        try:
            objects = load_obj_3d(filepath)
            if not objects:
                messagebox.showinfo("Nothing loaded",
                    "Nenhum objeto 3D (faces/linhas) encontrado no arquivo.")
                return
            for obj in objects:
                base = obj.name or "object3d"
                name = base
                k = 1
                while display_file.has_name(name):
                    name = f"{base}_{k}"
                    k += 1
                obj.name = name
                display_file.add(obj)
                object_listbox.insert(tk.END, str(obj))
            redraw()
        except Exception as e:
            messagebox.showerror("Error", str(e))

obj_frame = tk.Frame(panel, bg="lightgray")
obj_frame.pack(fill=tk.X, pady=5)
tk.Button(obj_frame, text="Save .obj", command=do_save_obj).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
tk.Button(obj_frame, text="Load .obj", command=do_load_obj).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
tk.Button(panel, text="Load 3D .obj (wireframe)",
          command=do_load_obj_3d).pack(fill=tk.X, pady=2)

# Forçar o layout do Tkinter antes do primeiro redraw
root.update_idletasks()
redraw()

root.mainloop()
