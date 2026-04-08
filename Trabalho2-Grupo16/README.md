# Sistema Gráfico Interativo - INE5420

Sistema gráfico interativo 2D desenvolvido em Python 3 com Tkinter para a disciplina INE5420.

## Como rodar

```bash
python3 main.py
```

## Estrutura do projeto

```
main.py        → Interface gráfica (Tkinter) e conexão entre componentes
model.py       → Classes dos objetos gráficos, Window e DisplayFile
transform.py   → Transformadas: viewport, matrizes homogêneas e transformações 2D
```

## Arquitetura

### model.py

Hierarquia de classes:

```
GraphicObject (classe base)
├── Point       → coordenada única (x, y)
├── Line        → dois pontos
├── Wireframe   → lista de pontos conectados (polígono)
└── Window      → retângulo da window (drawable=False)
```

- **GraphicObject**: classe base com `name`, `coordinates`, `drawable`, `color` e `center()`. Define a interface `object_type` e `draw_segments()` que cada subclasse implementa.
- **Window**: primeiro elemento do display file, nao é desenhada. Encapsula `pan()`, `zoom()` e `reset()`.
- **DisplayFile**: gerencia a coleção de objetos. A window é sempre o primeiro elemento e não pode ser removida.

### transform.py

Transformada de viewport:
- `window_to_viewport()`: mapeia coordenadas do mundo para a tela, com escala uniforme e inversão do eixo Y

Matrizes de transformação em coordenadas homogêneas (3x3):
- `translation_matrix(dx, dy)`
- `scaling_matrix(sx, sy)`
- `rotation_matrix(angle_degrees)`

Operações com matrizes:
- `multiply_matrices(m1, m2)`: multiplica duas matrizes 3x3
- `compose_matrices(matrices)`: compõe uma lista de matrizes em uma só

Transformações compostas:
- `natural_scaling_matrix(sx, sy, obj)`: escalonamento em torno do centro do objeto
- `rotation_around_center_matrix(angle, obj)`: rotação em torno do centro do objeto
- `rotation_around_point_matrix(angle, px, py)`: rotação em torno de ponto arbitrário

Aplicação:
- `apply_transform(obj, matrix)`: aplica qualquer matriz 3x3 nas coordenadas de um objeto

### main.py

- Cria a window (600x600) e o display file
- Painel esquerdo: lista de objetos, controles de pan/zoom/reset, campo de step (%)
- Canvas (viewport) de 800x800 com borda vermelha
- Dialog para adicionar objetos (Point, Line, Wireframe) com abas e seleção de cor
- Remoção de objetos selecionados na lista
- Validação de nomes duplicados
- Dialog de transformações com lista de operações pendentes

## Transformações 2D

O usuário seleciona um objeto na lista, clica em "Transform" e pode adicionar múltiplas transformações a uma lista pendente. Ao clicar "Apply", todas são compostas em uma única matriz e aplicadas de uma vez.

Transformações disponíveis:
- **Translation**: desloca o objeto por (dx, dy)
- **Scaling**: escalonamento natural em torno do centro do objeto
- **Rotation - World center**: rotação em torno da origem (0, 0)
- **Rotation - Object center**: rotação em torno do centro geométrico do objeto
- **Rotation - Arbitrary point**: rotação em torno de um ponto (px, py) qualquer

## Configurações

| Parâmetro | Valor |
|---|---|
| Window inicial | [-300, -300, 300, 300] (600x600) |
| Viewport (canvas) | 800x800 |
| Step padrão | 10% |
| Aspect ratio | 1:1 (window e viewport) |

## Entrada de coordenadas

- Ponto: `x, y` (ex: `100, 200`)
- Linha: `(x1,y1),(x2,y2)` (ex: `(0,0),(100,100)`)
- Wireframe: `(x1,y1),(x2,y2),(x3,y3),...` (ex: `(0,0),(100,0),(100,100),(0,100)`)
