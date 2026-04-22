# Sistema Gráfico Interativo - INE5420

Sistema gráfico interativo 2D desenvolvido em Python 3 com Tkinter para a disciplina INE5420 (UFSC).

## Como rodar

```bash
python3 main.py
```

## Estrutura do projeto

```
main.py        → Interface gráfica (Tkinter) e conexão entre componentes
model.py       → Classes dos objetos gráficos, Window e DisplayFile
transform.py   → Matrizes homogêneas, transformações 2D, SCN e viewport
clipping.py    → Algoritmos de clipping (ponto, retas, polígonos)
obj_io.py      → Leitura e escrita de arquivos Wavefront .obj
```

## Arquitetura

### model.py

Hierarquia de classes:

```
GraphicObject (classe base)
├── Point       → coordenada única (x, y)
├── Line        → dois pontos
├── Wireframe   → lista de pontos conectados (polígono, com atributo filled)
├── Curve2D     → curva(s) de Bézier encadeadas com continuidade G(0)
└── Window      → retângulo da window (drawable=False)
```

- **GraphicObject**: classe base com `name`, `coordinates`, `drawable`, `color`, `normalized_coords` e `center()`. Define a interface `object_type`, `draw_segments()` e `draw_segments_scn()` que cada subclasse implementa.
- **Curve2D**: curva formada por uma ou mais curvas cúbicas de Bézier encadeadas com continuidade G(0). Usa a matriz de Bézier `M_B` e as blending functions (polinômios de Bernstein) para calcular cada ponto na curva. Aceita `3k + 1` pontos de controle (com k ≥ 1), onde cada grupo de 4 pontos forma uma curva e o último ponto é compartilhado com o primeiro da próxima. A discretização usa `STEPS = 100` amostras por curva.
- **Window**: primeiro elemento do display file, não é desenhada. Encapsula `pan()`, `zoom()`, `rotate()` e `reset()`. Possui vetor view-up (`vup`) e ângulo acumulado para rotação.
- **DisplayFile**: gerencia a coleção de objetos. A window é sempre o primeiro elemento e não pode ser removida. Método `update_scn()` recalcula coordenadas normalizadas de todos os objetos.

### transform.py

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

Pipeline SCN (Sistema de Coordenadas Normalizado):
- `scn_matrix(window)`: gera a matriz que transforma coordenadas do mundo para SCN, implementando o algoritmo "Gerar Descrição em SCN" (translada centro da window para origem → rotaciona por -ângulo → escalona para [-1, 1])
- `scn_to_viewport(x_scn, y_scn, viewport)`: mapeia coordenadas SCN [-1, 1] para pixels do viewport

### obj_io.py

- `save_obj(filepath, display_file)`: salva todos os objetos do display file em formato Wavefront .obj, com cores em arquivo .mtl associado
- `load_obj(filepath)`: carrega objetos de um arquivo .obj e retorna lista de GraphicObjects

### clipping.py

Algoritmos de clipping que operam em coordenadas SCN (normalizadas). A janela de clipping é ligeiramente menor que [-1, 1] para deixar uma margem visível ao redor da viewport (constante `MARGIN = 0.05`).

Clipagem de pontos:
- `clip_point(x, y)`: teste simples de pertinência `Xw_min <= X <= Xw_max` e `Yw_min <= Y <= Yw_max`

Clipagem de retas (duas técnicas, selecionáveis por radio button):
- `cohen_sutherland(x1, y1, x2, y2)`: usa region codes de 4 bits (LEFT=1, RIGHT=2, BOTTOM=4, TOP=8) para classificar rapidamente a reta como totalmente visível, invisível ou parcialmente visível. No caso parcial, calcula intersecções iterativamente com as bordas da janela usando coeficiente angular
- `liang_barsky(x1, y1, x2, y2)`: usa representação paramétrica da reta com parâmetros p_k e q_k. Calcula ζ1 (max dos r_k para p<0, transição fora→dentro) e ζ2 (min dos r_k para p>0, transição dentro→fora). Rejeita se ζ1 > ζ2

Clipagem de polígonos:
- `sutherland_hodgman(polygon)`: processa todos os vértices do polígono sequencialmente contra cada aresta da janela (LEFT, RIGHT, BOTTOM, TOP). Para cada par de vértices adjacentes, aplica 4 regras: out→in salva intersecção + vértice, in→in salva vértice, in→out salva intersecção, out→out não salva nada

Clipagem de curvas:
- `clip_curve(curve_points)`: aplica point clipping em cada amostra da curva discretizada. Como uma curva pode sair e voltar a entrar na janela várias vezes, retorna uma lista de sub-trechos (cada um é uma lista contígua de pontos visíveis). Segue a sugestão do slide 5.6 ("verifico se o fim do próximo segmento t/k está dentro do window usando clipping de pontos")

### main.py

- Cria a window (600x600) e o display file
- Painel esquerdo: lista de objetos, controles de pan/zoom/rotação/reset, campo de step (%)
- Radio buttons para seleção do algoritmo de clipagem de retas (Cohen-Sutherland / Liang-Barsky)
- Canvas de 800x800 com viewport interna menor (margem de 5%) e moldura vermelha para visualização do clipping
- Dialog para adicionar objetos (Point, Line, Wireframe, Curve) com abas, seleção de cor, opção de preenchimento para wireframes e entrada livre de pontos de controle para curvas
- Remoção de objetos selecionados na lista
- Validação de nomes duplicados
- Dialog de transformações com lista de operações pendentes
- Botões de importação/exportação de arquivos .obj

## Pipeline de visualização

```
Coordenadas do mundo → scn_matrix(window) → Coordenadas SCN [-1,1] → Clipping (em SCN) → scn_to_viewport → Pixels
```

A cada redraw, as coordenadas normalizadas (SCN) de todos os objetos são recalculadas com base na posição, zoom e rotação da window. As coordenadas do mundo nunca são alteradas pela navegação da window. A transformada de viewport é aplicada apenas aos objetos resultantes do clipping.

## Clipping

O clipping é realizado em coordenadas SCN, após a normalização e antes da transformação de viewport. A janela de clipping é definida como `[-0.90, -0.90, 0.90, 0.90]` (margem de 5% em cada lado), de modo que a viewport é menor que o canvas — a moldura vermelha ao redor torna erros de clipping imediatamente visíveis.

Técnicas implementadas:
- **Pontos**: teste de pertinência no retângulo de clipping
- **Retas**: Cohen-Sutherland e Liang-Barsky (intercambiáveis via radio button no painel)
- **Polígonos preenchidos**: Sutherland-Hodgman (processa os vértices contra cada aresta da janela, fechando o polígono na borda de clipping)
- **Wireframes (não preenchidos)**: cada aresta é clipada individualmente como linha (usando o algoritmo selecionado no radio button), evitando arestas falsas ao longo da borda de clipping
- **Curvas**: point clipping em cada amostra discretizada (conforme slide 5.6)

## Polígonos preenchidos

O usuário escolhe se um polígono (wireframe) é em modelo de arame ou preenchido no momento da criação, via checkbox "Filled" na aba Wireframe do diálogo de adição. Polígonos preenchidos usam `canvas.create_polygon()` do Tkinter com preenchimento sólido na cor do objeto. O clipping de Sutherland-Hodgman é aplicado normalmente — o polígono clipado resultante é então desenhado preenchido.
## Transformações 2D

O usuário seleciona um objeto na lista, clica em "Transform" e pode adicionar múltiplas transformações a uma lista pendente. Ao clicar "Apply", todas são compostas em uma única matriz e aplicadas de uma vez.

Transformações disponíveis:
- **Translation**: desloca o objeto por (dx, dy), relativo à orientação da window
- **Scaling**: escalonamento natural em torno do centro do objeto
- **Rotation - World center**: rotação em torno da origem (0, 0)
- **Rotation - Object center**: rotação em torno do centro geométrico do objeto
- **Rotation - Arbitrary point**: rotação em torno de um ponto (px, py) qualquer

## Rotação da window

A window pode ser rotacionada pelo campo de ângulo e botões de rotação no painel. O pan (Up/Down/Left/Right) respeita a rotação — "Up" sempre move na direção que aparenta ser "cima" na tela, independente do ângulo da window.

## Wavefront .obj

- **Save .obj**: exporta todos os objetos do mundo para um arquivo `.obj` com arquivo `.mtl` associado para cores (formato RGB)
- **Load .obj**: importa objetos de um arquivo `.obj`, lendo cores do `.mtl` se presente

## Configurações

| Parâmetro | Valor |
|---|---|
| Window inicial | [-300, -300, 300, 300] (600x600) |
| Viewport (canvas) | 800x800 |
| Step padrão | 10% |
| Ângulo de rotação padrão | 15° |
| Aspect ratio | 1:1 (window e viewport) |

## Entrada de coordenadas

- Ponto: `x, y` (ex: `100, 200`)
- Linha: `(x1,y1),(x2,y2)` (ex: `(0,0),(100,100)`)
- Wireframe: `(x1,y1),(x2,y2),(x3,y3),...` (ex: `(0,0),(100,0),(100,100),(0,100)`)
- Curva: `(x1,y1),(x2,y2),...` com 4, 7, 10, 13, ... pontos (ex: 4 pontos `(0,0),(50,150),(100,150),(150,0)`; 7 pontos encadeiam duas curvas com G(0)).
