import tkinter as tk
from tkinter import ttk
from model import display_file, Point, Line, Wireframe
from transform import window_to_viewport

window = [-300, -300, 300, 300]  # (x_min, y_min, x_max, y_max)

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

# Pan / Zoom functions
def pan(dx, dy):
    step = float(step_entry.get()) / 100
    width = window[2] - window[0]
    height = window[3] - window[1]
    window[0] += dx * width * step
    window[1] += dy * height * step
    window[2] += dx * width * step
    window[3] += dy * height * step
    redraw()

def zoom(factor):
    step = float(step_entry.get()) / 100
    width = window[2] - window[0]
    height = window[3] - window[1]
    cx = (window[0] + window[2]) / 2
    cy = (window[1] + window[3]) / 2
    new_width = width * (1 - factor * step)
    new_height = height * (1 - factor * step)
    window[0] = cx - new_width / 2
    window[1] = cy - new_height / 2
    window[2] = cx + new_width / 2
    window[3] = cy + new_height / 2
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

# ── Canvas (viewport) ────────────────────────────────────
canvas = tk.Canvas(root, width=700, height=600, bg="white",
                   highlightthickness=2, highlightbackground="red")
canvas.pack(side=tk.LEFT, padx=10, pady=10)

def redraw():
    canvas.delete("all")

    vp = (0, 0, canvas.winfo_width(), canvas.winfo_height())

    for obj in display_file:
        if obj.object_type == "point":
            x, y = obj.coordinates[0]
            sx, sy = window_to_viewport(x, y, window, vp)
            canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="black")
        else:
            for p1, p2 in obj.draw_segments():
                x1, y1 = window_to_viewport(p1[0], p1[1], window, vp)
                x2, y2 = window_to_viewport(p2[0], p2[1], window, vp)
                canvas.create_line(x1, y1, x2, y2, fill="black")

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

    # Type tabs
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    point_tab     = tk.Frame(notebook)
    line_tab      = tk.Frame(notebook)
    wireframe_tab = tk.Frame(notebook)

    notebook.add(point_tab,     text="Point")
    notebook.add(line_tab,      text="Line")
    notebook.add(wireframe_tab, text="Wireframe")

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

    def on_ok():
        name = name_entry.get().strip()
        if not name:
            return
        
        tab = notebook.index(notebook.select())

        if tab == 0: # Point
            coords = list(eval(point_entry.get()))
            obj = Point(name, coords[0], coords[1])

        elif tab == 1: # Line
            coords = list(eval(line_entry.get()))
            p1 = Point("", coords[0][0], coords[0][1])
            p2 = Point("", coords[1][0], coords[1][1])
            obj = Line(name, p1, p2)
        
        elif tab == 2: # Wireframe
            coords = list(eval(wireframe_entry.get()))
            points = [Point("", c[0], c[1]) for c in coords]
            obj = Wireframe(name, points)

        display_file.append(obj)
        object_listbox.insert(tk.END, str(obj))
        redraw()
        dialog.destroy()

    # OK / Cancel buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    tk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT)

tk.Button(panel, text="Add Object", command=open_add_object_dialog).pack(fill=tk.X, pady=2)

root.mainloop()
