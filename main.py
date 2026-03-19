import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Sistema Gráfico Interativo - INE5420")

# ── Painel esquerdo ──────────────────────────────────────
panel = tk.Frame(root, width=200, bg="lightgray")
panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

# Seção: lista de objetos
tk.Label(panel, text="Objetos", bg="lightgray", anchor="w").pack(fill=tk.X)
listbox = tk.Listbox(panel, height=6)
listbox.pack(fill=tk.X, pady=(0, 10))

# Seção: Window
window_frame = tk.LabelFrame(panel, text="Window", bg="lightgray")
window_frame.pack(fill=tk.X, pady=5)

# Passo
passo_frame = tk.Frame(window_frame, bg="lightgray")
passo_frame.pack(fill=tk.X, padx=5, pady=2)
tk.Label(passo_frame, text="Passo:", bg="lightgray").pack(side=tk.LEFT)
passo_entry = tk.Entry(passo_frame, width=5)
passo_entry.insert(0, "10")
passo_entry.pack(side=tk.LEFT)
tk.Label(passo_frame, text="%", bg="lightgray").pack(side=tk.LEFT)

# Botões de pan
tk.Button(window_frame, text="Up").pack(pady=1)

lr_frame = tk.Frame(window_frame, bg="lightgray")
lr_frame.pack()
tk.Button(lr_frame, text="Left").pack(side=tk.LEFT, padx=2)
tk.Button(lr_frame, text="Right").pack(side=tk.LEFT, padx=2)

tk.Button(window_frame, text="Down").pack(pady=1)

# Botões de zoom
zoom_frame = tk.Frame(window_frame, bg="lightgray")
zoom_frame.pack(pady=5)
tk.Label(zoom_frame, text="Zoom", bg="lightgray").pack(side=tk.LEFT, padx=5)
tk.Button(zoom_frame, text="+", width=3).pack(side=tk.LEFT, padx=2)
tk.Button(zoom_frame, text="-", width=3).pack(side=tk.LEFT, padx=2)

# ── Canvas (viewport) ────────────────────────────────────
canvas = tk.Canvas(root, width=700, height=600, bg="white",
                   highlightthickness=2, highlightbackground="red")
canvas.pack(side=tk.LEFT, padx=10, pady=10)

def abrir_janela_objeto():
    top = tk.Toplevel(root)
    top.title("Incluir Objeto")
    top.grab_set()  # bloqueia a janela principal enquanto essa está aberta

    # Campo Nome
    nome_frame = tk.Frame(top)
    nome_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Label(nome_frame, text="Nome").pack(side=tk.LEFT)
    nome_entry = tk.Entry(nome_frame)
    nome_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # Abas de tipo
    notebook = ttk.Notebook(top)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    aba_ponto     = tk.Frame(notebook)
    aba_reta      = tk.Frame(notebook)
    aba_wireframe = tk.Frame(notebook)

    notebook.add(aba_ponto,     text="Ponto")
    notebook.add(aba_reta,      text="Reta")
    notebook.add(aba_wireframe, text="Wireframe")

    # Aba Ponto
    tk.Label(aba_ponto, text="Coordenadas:").pack(pady=5)
    tk.Label(aba_ponto, text="(x, y)").pack()
    ponto_entry = tk.Entry(aba_ponto, width=30)
    ponto_entry.pack(pady=5)

    # Aba Reta
    tk.Label(aba_reta, text="Coordenadas:").pack(pady=5)
    tk.Label(aba_reta, text="(x1,y1),(x2,y2)").pack()
    reta_entry = tk.Entry(aba_reta, width=30)
    reta_entry.pack(pady=5)

    # Aba Wireframe
    tk.Label(aba_wireframe, text="Coordenadas:").pack(pady=5)
    tk.Label(aba_wireframe, text="(x1,y1),(x2,y2),(x3,y3),...").pack()
    wire_entry = tk.Entry(aba_wireframe, width=30)
    wire_entry.pack(pady=5)

    # Botões OK / Cancel
    btn_frame = tk.Frame(top)
    btn_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Button(btn_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=5)
    tk.Button(btn_frame, text="OK").pack(side=tk.RIGHT)

tk.Button(panel, text="Adicionar Objeto", command=abrir_janela_objeto).pack(fill=tk.X, pady=2)

root.mainloop()