import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from model import DisplayFile, Window, Point, Line, Wireframe
from transform import (window_to_viewport, apply_transform, compose_matrices,
                        translation_matrix, natural_scaling_matrix,
                        rotation_matrix, rotation_around_center_matrix,
                        rotation_around_point_matrix)

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

tk.Button(window_frame, text="Reset", command=reset).pack(pady=5)

# ── Canvas (viewport) ────────────────────────────────────
canvas = tk.Canvas(root, width=800, height=800, bg="white",
                   highlightthickness=2, highlightbackground="red")
canvas.pack(side=tk.LEFT, padx=10, pady=10)

def redraw():
    canvas.delete("all")

    win = window.bounds()
    vp = (0, 0, canvas.winfo_width(), canvas.winfo_height())

    for obj in display_file.drawable_objects():
        color = obj.color
        if obj.object_type == "point":
            x, y = obj.coordinates[0]
            sx, sy = window_to_viewport(x, y, win, vp)
            canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill=color, outline=color)
        else:
            for p1, p2 in obj.draw_segments():
                x1, y1 = window_to_viewport(p1[0], p1[1], win, vp)
                x2, y2 = window_to_viewport(p2[0], p2[1], win, vp)
                canvas.create_line(x1, y1, x2, y2, fill=color)

# ── Add object dialog ────────────────────────────────────

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

        if display_file.has_name(name):
            messagebox.showwarning("Duplicate name",
                f"An object named '{name}' already exists.", parent=dialog)
            return

        tab = notebook.index(notebook.select())
        color = color_var.get()

        try:
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

    dialog = tk.Toplevel(root)
    dialog.title(f"Transform: {obj}")
    dialog.grab_set()

    # Pending transformations: list of (matrix, description)
    pending = []

    # ── Left side: transformation input ──
    input_frame = tk.Frame(dialog)
    input_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

    tk.Label(input_frame, text="Transformation:").pack(anchor="w")
    transform_type = ttk.Combobox(input_frame, state="readonly", values=[
        "Translation",
        "Scaling",
        "Rotation - World center",
        "Rotation - Object center",
        "Rotation - Arbitrary point",
    ])
    transform_type.set("Translation")
    transform_type.pack(fill=tk.X, pady=5)

    # Dynamic parameter fields
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
        elif choice == "Scaling":
            labels = [("Sx:", "sx"), ("Sy:", "sy")]
        elif choice in ("Rotation - World center", "Rotation - Object center"):
            labels = [("Angle:", "angle")]
        elif choice == "Rotation - Arbitrary point":
            labels = [("Angle:", "angle"), ("Px:", "px"), ("Py:", "py")]
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
        return translation_matrix(dx, dy), f"Translate ({dx}, {dy})"

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

    builders = {
        "Translation": build_translation,
        "Scaling": build_scaling,
        "Rotation - World center": build_rotation_world,
        "Rotation - Object center": build_rotation_center,
        "Rotation - Arbitrary point": build_rotation_point,
    }

    # ── Actions ──
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

root.mainloop()
