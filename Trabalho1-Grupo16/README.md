# Sistema Grafico Interativo - INE5420

Sistema grafico interativo 2D desenvolvido em Python 3 com Tkinter para a disciplina INE5420 (UFSC).

## Como rodar

```bash
python3 main.py
```

## Estrutura do projeto

```
main.py        → Interface grafica (Tkinter) e conexao entre componentes
model.py       → Classes dos objetos graficos, Window e DisplayFile
transform.py   → Transformada de viewport (window → viewport)
```

## Arquitetura

### model.py

Hierarquia de classes:

```
GraphicObject (classe base)
├── Point       → coordenada unica (x, y)
├── Line        → dois pontos
├── Wireframe   → lista de pontos conectados (poligono)
└── Window      → retangulo da window (drawable=False)
```

- **GraphicObject**: classe base com `name`, `coordinates`, `drawable`. Define a interface `object_type` e `draw_segments()` que cada subclasse implementa.
- **Window**: primeiro elemento do display file, nao e desenhada. Encapsula `pan()`, `zoom()` e `reset()`.
- **DisplayFile**: gerencia a colecao de objetos. A window e sempre o primeiro elemento e nao pode ser removida.

### transform.py

Funcao `window_to_viewport(x_w, y_w, window, viewport)`:
- Mapeia coordenadas do mundo (window) para coordenadas da tela (viewport)
- Usa escala uniforme (`min(sx, sy)`) para nao distorcer objetos
- Centraliza o resultado quando window e viewport tem tamanhos diferentes
- Inverte o eixo Y (mundo: Y pra cima, tela: Y pra baixo)

### main.py

- Cria a window (600x600) e o display file
- Painel esquerdo: lista de objetos, controles de pan/zoom/reset, campo de step (%)
- Canvas (viewport) de 800x800 com borda vermelha
- Dialogo para adicionar objetos (Point, Line, Wireframe) com abas
- Remocao de objetos selecionados na lista
- Validacao de nomes duplicados

## Configuracoes

| Parametro | Valor |
|---|---|
| Window inicial | [-300, -300, 300, 300] (600x600) |
| Viewport (canvas) | 800x800 |
| Step padrao | 10% |
| Aspect ratio | 1:1 (window e viewport) |

## Entrada de coordenadas

- Ponto: `x, y` (ex: `100, 200`)
- Linha: `(x1,y1),(x2,y2)` (ex: `(0,0),(100,100)`)
- Wireframe: `(x1,y1),(x2,y2),(x3,y3),...` (ex: `(0,0),(100,0),(100,100),(0,100)`)
