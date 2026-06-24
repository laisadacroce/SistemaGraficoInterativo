"""Wavefront .obj file reader/writer for the SGI display file.

Supports points (p), lines (l), wireframes (f) and Bézier curves
(custom `curv` directive) with colors stored in an associated .mtl
material library file."""

import os
from model import (Point, Line, Wireframe, Curve2D, BSpline, Point3D,
                   Object3D, BezierSurface, BSplineSurface)


def save_obj(filepath, display_file):
    """Saves all drawable objects from the display file to a .obj file.

    Also generates an associated .mtl file for object colors."""
    base = os.path.splitext(filepath)[0]
    mtl_filename = os.path.basename(base) + ".mtl"
    mtl_path = base + ".mtl"

    vertices = {}  # (x, y) -> index (1-based)
    materials = {}  # obj_name -> hex color

    # Collect all unique vertices
    for obj in display_file.drawable_objects():
        # Objetos 3D (Point3D/Object3D) não são exportados para .obj 2D
        if obj.object_type in ("object3d", "point3d"):
            continue
        for x, y in obj.coordinates:
            if (x, y) not in vertices:
                vertices[(x, y)] = len(vertices) + 1
        materials[obj.name.replace(" ", "_")] = obj.color

    # Write .obj file
    with open(filepath, "w") as f:
        f.write("# SGI - Sistema Grafico Interativo\n")
        f.write(f"mtllib {mtl_filename}\n\n")

        # Write all vertices
        for (x, y) in vertices:
            f.write(f"v {x} {y} 0.0\n")
        f.write("\n")

        # Write each object
        for obj in display_file.drawable_objects():
            # Objetos 3D não são exportados para .obj 2D (ver acima)
            if obj.object_type in ("object3d", "point3d"):
                continue
            safe_name = obj.name.replace(" ", "_")
            f.write(f"o {safe_name}\n")
            f.write(f"usemtl {safe_name}\n")

            indices = [vertices[(x, y)] for x, y in obj.coordinates]

            if obj.object_type == "point":
                f.write(f"p {indices[0]}\n")
            elif obj.object_type == "line":
                f.write(f"l {indices[0]} {indices[1]}\n")
            elif obj.object_type == "wireframe":
                f.write(f"f {' '.join(str(i) for i in indices)}\n")
            elif obj.object_type == "curve":
                # Bézier curve — save control points under custom `curv`
                # directive so we can reconstruct it on load.
                f.write(f"curv {' '.join(str(i) for i in indices)}\n")
            elif obj.object_type == "bspline":
                # B-Spline — save control points under custom `bspl`
                # directive so we can reconstruct it on load.
                f.write(f"bspl {' '.join(str(i) for i in indices)}\n")
            f.write("\n")

    # Write .mtl file
    _write_mtl(mtl_path, materials)


def load_obj(filepath):
    """Loads objects from a .obj file and returns a list of GraphicObjects.

    Reads the associated .mtl file for colors if present."""
    vertices = {}  # index (1-based) -> (x, y)
    objects = []
    materials = {}

    current_name = None
    current_color = "#000000"

    dir_path = os.path.dirname(filepath)

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            keyword = parts[0]

            if keyword == "mtllib":
                # Join all parts after 'mtllib' to handle filenames with spaces
                mtl_name = " ".join(parts[1:])
                mtl_path = os.path.join(dir_path, mtl_name)
                if os.path.exists(mtl_path):
                    materials = _read_mtl(mtl_path)

            elif keyword == "v":
                idx = len(vertices) + 1
                vertices[idx] = (float(parts[1]), float(parts[2]))

            elif keyword == "o":
                current_name = parts[1]

            elif keyword == "usemtl":
                mat_name = parts[1]
                if mat_name in materials:
                    current_color = materials[mat_name]

            elif keyword == "p":
                # Point
                idx = int(parts[1])
                x, y = vertices[idx]
                obj = Point(current_name or "point", x, y)
                obj.color = current_color
                objects.append(obj)

            elif keyword == "l":
                # Line (2 vertices) or open polyline
                indices = [int(p) for p in parts[1:]]
                if len(indices) == 2:
                    p1 = Point("", *vertices[indices[0]])
                    p2 = Point("", *vertices[indices[1]])
                    obj = Line(current_name or "line", p1, p2)
                else:
                    points = [Point("", *vertices[i]) for i in indices]
                    obj = Wireframe(current_name or "wireframe", points)
                obj.color = current_color
                objects.append(obj)

            elif keyword == "f":
                # Face / wireframe
                indices = [int(p.split("/")[0]) for p in parts[1:]]
                points = [Point("", *vertices[i]) for i in indices]
                obj = Wireframe(current_name or "wireframe", points)
                obj.color = current_color
                objects.append(obj)

            elif keyword == "curv":
                # Bézier curve — custom directive with control point indices
                indices = [int(p) for p in parts[1:]]
                if Curve2D.valid_point_count(len(indices)):
                    points = [Point("", *vertices[i]) for i in indices]
                    obj = Curve2D(current_name or "curve", points)
                    obj.color = current_color
                    objects.append(obj)

            elif keyword == "bspl":
                # B-Spline — custom directive with control point indices
                indices = [int(p) for p in parts[1:]]
                if BSpline.valid_point_count(len(indices)):
                    points = [Point("", *vertices[i]) for i in indices]
                    obj = BSpline(current_name or "bspline", points)
                    obj.color = current_color
                    objects.append(obj)

    return objects


def load_obj_3d(filepath):
    """Carrega objetos 3D em modelo de arame (Object3D) de um arquivo
    Wavefront .obj.

    Lê os vértices `v x y z` em 3D. Cada grupo `o` vira um Object3D;
    as arestas (segmentos de reta) vêm das faces `f` — cada face é um
    polígono fechado — e das linhas `l`. Lê cores do `.mtl` associado.

    Superfícies bicúbicas de Bézier são lidas da diretiva customizada
    `surf` (16 índices de pontos de controle por retalho, análoga à
    `curv`/`bspl` das curvas); vários `surf` sob o mesmo `o` compõem uma
    superfície de múltiplos retalhos (Trabalho 1.9).

    Superfícies bicúbicas B-Spline (Trabalho 1.10) são lidas da diretiva
    `bsurf <linhas> <colunas> <i1> <i2> ...`, com a matriz n×m de pontos
    de controle (índices em ordem linha-a-linha); a subdivisão em
    retalhos 4×4 é automática.

    Usado para carregar modelos como paralelepípedos e superfícies e
    mostrá-los em perspectiva."""
    global_verts = {}   # índice (1-based) -> (x, y, z)
    materials = {}
    groups = []         # lista de grupos {name, color, edges, patches}
    current = None
    dir_path = os.path.dirname(filepath)

    def new_group(name):
        g = {"name": name, "color": "#000000", "edges": [],
             "patches": [], "bspline_grids": []}
        groups.append(g)
        return g

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            keyword = parts[0]

            if keyword == "mtllib":
                mtl_path = os.path.join(dir_path, " ".join(parts[1:]))
                if os.path.exists(mtl_path):
                    materials = _read_mtl(mtl_path)

            elif keyword == "v":
                idx = len(global_verts) + 1
                z = float(parts[3]) if len(parts) > 3 else 0.0
                global_verts[idx] = (float(parts[1]), float(parts[2]), z)

            elif keyword == "o":
                current = new_group(parts[1])

            elif keyword == "usemtl":
                if current is None:
                    current = new_group("object3d")
                if parts[1] in materials:
                    current["color"] = materials[parts[1]]

            elif keyword in ("f", "l"):
                if current is None:
                    current = new_group("object3d")
                # índices podem vir na forma i/j/k — usa só o primeiro
                idxs = [int(p.split("/")[0]) for p in parts[1:]]
                # arestas entre vértices consecutivos
                for k in range(len(idxs) - 1):
                    current["edges"].append((idxs[k], idxs[k + 1]))
                # face: fecha o polígono ligando o último ao primeiro
                if keyword == "f" and len(idxs) > 2:
                    current["edges"].append((idxs[-1], idxs[0]))

            elif keyword == "surf":
                # Retalho de superfície bicúbica de Bézier — 16 índices
                # de pontos de controle (3D).
                if current is None:
                    current = new_group("surface")
                idxs = [int(p.split("/")[0]) for p in parts[1:]]
                if BezierSurface.valid_patch(idxs):
                    current["patches"].append([global_verts[i] for i in idxs])

            elif keyword == "bsurf":
                # Superfície bicúbica B-Spline (Trabalho 1.10):
                #   bsurf <linhas> <colunas> <i1> <i2> ... <i(linhas*colunas)>
                # Matriz n×m de pontos de controle em ordem linha-a-linha.
                if current is None:
                    current = new_group("bsurface")
                rows = int(parts[1])
                cols = int(parts[2])
                idxs = [int(p.split("/")[0]) for p in parts[3:]]
                if (BSplineSurface.valid_dims(rows, cols)
                        and len(idxs) == rows * cols):
                    grid = [[global_verts[idxs[r * cols + c]] for c in range(cols)]
                            for r in range(rows)]
                    current["bspline_grids"].append(grid)

    # Constrói os objetos de cada grupo. Grupos com retalhos `surf`
    # viram BezierSurface; grupos com arestas viram Object3D (com os
    # índices globais remapeados para locais, guardando só os vértices
    # usados).
    objects = []
    for g in groups:
        if g["patches"]:
            obj = BezierSurface(g["name"] or "surface", g["patches"])
            obj.color = g["color"]
            objects.append(obj)
        for grid in g["bspline_grids"]:
            obj = BSplineSurface(g["name"] or "bsurface", grid)
            obj.color = g["color"]
            objects.append(obj)
        if g["edges"]:
            local = []
            remap = {}
            for a, b in g["edges"]:
                for gi in (a, b):
                    if gi not in remap:
                        remap[gi] = len(local)
                        local.append(global_verts[gi])
            points = [Point3D("", x, y, z) for (x, y, z) in local]
            segments = [(remap[a], remap[b]) for a, b in g["edges"]]
            obj = Object3D(g["name"], points, segments)
            obj.color = g["color"]
            objects.append(obj)

    return objects


def _hex_to_rgb_floats(hex_color):
    """Converts '#RRGGBB' to (r, g, b) floats in [0, 1]."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return r, g, b


def _rgb_floats_to_hex(r, g, b):
    """Converts (r, g, b) floats in [0, 1] to '#RRGGBB'."""
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _write_mtl(mtl_path, materials):
    """Writes a .mtl material library file."""
    with open(mtl_path, "w") as f:
        f.write("# SGI Material Library\n\n")
        for name, hex_color in materials.items():
            r, g, b = _hex_to_rgb_floats(hex_color)
            f.write(f"newmtl {name}\n")
            f.write(f"Kd {r:.4f} {g:.4f} {b:.4f}\n\n")


def _read_mtl(mtl_path):
    """Reads a .mtl file and returns {material_name: '#RRGGBB'}."""
    materials = {}
    current = None
    with open(mtl_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("newmtl"):
                current = line.split()[1]
            elif line.startswith("Kd") and current:
                parts = line.split()
                r, g, b = float(parts[1]), float(parts[2]), float(parts[3])
                materials[current] = _rgb_floats_to_hex(r, g, b)
    return materials
