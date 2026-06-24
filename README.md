# Sistema Gráfico Interativo - INE5420

Sistema gráfico interativo 2D e 3D desenvolvido em Python 3 com Tkinter para a disciplina INE5420 (UFSC).

## Como rodar

```bash
python3 main.py
```

## Estrutura do projeto

```
main.py        → Interface gráfica (Tkinter) e conexão entre componentes
model.py       → Classes dos objetos gráficos, Window e DisplayFile
transform.py   → Matrizes homogêneas 3x3, transformações 2D, SCN e viewport
transform3d.py → Matrizes 4x4, transformações 3D e projeções paralela ortogonal e perspectiva
clipping.py    → Algoritmos de clipping (ponto, retas, polígonos)
obj_io.py      → Leitura e escrita de .obj 2D (load_obj) e leitura de modelos de arame 3D (load_obj_3d)
```

## Arquitetura

### model.py

Hierarquia de classes:

```
GraphicObject (classe base)
├── Point         → coordenada única (x, y)
├── Line          → dois pontos
├── Wireframe     → lista de pontos conectados (polígono, com atributo filled)
├── Curve2D       → curva(s) de Bézier encadeadas com continuidade G(0)
├── BSpline       → curva B-Spline uniforme cúbica via Forward Differences
├── Point3D       → coordenada única no espaço 3D (x, y, z)
├── Object3D      → modelo de arame 3D (lista de segmentos de reta)
├── BezierSurface → superfície bicúbica de Bézier 3D (lista de retalhos 4x4)
├── BSplineSurface→ superfície bicúbica B-Spline 3D (matriz n×m, Forward Differences)
└── Window        → câmera 3D (VRP/VPN/VUP), drawable=False
```

- **GraphicObject**: classe base com `name`, `coordinates`, `drawable`, `color`, `normalized_coords` e `center()`. Define a interface `object_type`, `draw_segments()` e `draw_segments_scn()` que cada subclasse implementa.
- **Point3D**: ponto no espaço 3D, capaz das 3 transformações básicas (translação, escalonamento, rotação) via matrizes 4×4. É o bloco de construção dos segmentos de um `Object3D`.
- **Object3D**: objeto 3D em modelo de arame — uma lista de pontos de controle 3D (`coordinates`) e uma lista de segmentos de reta (`segments`), onde cada segmento é um par de índices ligando dois pontos. Capaz das 3 operações básicas e da rotação em torno de um eixo arbitrário.
- **BezierSurface**: superfície bicúbica de Bézier 3D — uma lista de retalhos (*patches*), cada um com 16 pontos de controle 3D numa matriz de geometria 4x4, achatados em `coordinates` (16 por retalho). Avalia a função de suavização bicúbica `P(s,t) = S · M_B · G · M_B^T · T^T` (Eq. 5.27) para `x`, `y` e `z`, discretizando `s` e `t` em `STEPS = 10` subdivisões e gerando a malha como iso-curvas em ambas as direções. A malha é avaliada em **coordenadas de view** (3D) e projetada segmento a segmento, de modo que funciona tanto na projeção paralela quanto na perspectiva. É um objeto 3D pleno: sofre as transformações 4x4 e é carregado de `.obj` pela diretiva `surf`. Retalhos que compartilham pontos de controle de borda formam uma superfície composta contínua.
- **BSplineSurface**: superfície bicúbica B-Spline 3D desenhada por **Diferenças Adiante** (Forward Differences). Recebe uma matriz n×m de pontos de controle (4 ≤ n, m ≤ 20) e **subdivide automaticamente** em (n−3)×(m−3) retalhos — cada um uma janela deslizante 4×4 sobre a matriz, com base uniforme `M_BS` e continuidade C(2). Cada retalho é desenhado pré-calculando a matriz de diferenças `DD = E(δs) · C · E(δt)^T` (com `C = M_BS · G · M_BS^T`) e gerando toda a grade de pontos **apenas com somas**. Diferente do algoritmo de Foley & van Dam, percorre cada iso-curva em t sobre uma cópia da primeira linha de `DD`, preservando a matriz para o avanço em s. Avaliada em coordenadas de view e projetada como as demais superfícies; objeto 3D pleno, carregado de `.obj` pela diretiva `bsurf`.
- **Curve2D**: curva formada por uma ou mais curvas cúbicas de Bézier encadeadas com continuidade G(0). Usa a matriz de Bézier `M_B` e as blending functions (polinômios de Bernstein) para calcular cada ponto na curva. Aceita `3k + 1` pontos de controle (com k ≥ 1), onde cada grupo de 4 pontos forma uma curva e o último ponto é compartilhado com o primeiro da próxima. A discretização usa `STEPS = 100` amostras por curva.
- **BSpline**: curva B-Spline uniforme cúbica. Aceita **qualquer número de pontos de controle ≥ 4**; com `n` pontos gera `n − 3` segmentos, cada um definido por 4 pontos de controle consecutivos numa janela deslizante (`P_i .. P_{i+3}`). Cada segmento é avaliado pela técnica de **Forward Differences** (diferenças adiantadas): os coeficientes do polinômio cúbico vêm de `C = M_BS · G` (matriz base B-Spline `M_BS` com fator 1/6), e os pontos são gerados apenas com somas a partir dos incrementos iniciais `Δ`, `Δ²`, `Δ³` — sem reavaliar potências de `t`. A continuidade entre segmentos é C(2). Discretização de `STEPS = 100` passos por segmento.
- **Window**: primeiro elemento do display file, não é desenhada. A partir do Trabalho 1.7 é uma **câmera 3D**, definida por VRP (View Reference Point), VPN (View Plane Normal), VUP (View Up) e tamanho da janela no plano de projeção. Encapsula a navegação 3D: `pan()`, `move_forward()`, `zoom()`, `rotate()`/`roll()`, `pitch()`, `yaw()` e `reset()`.
- **DisplayFile**: gerencia a coleção de objetos. A window é sempre o primeiro elemento e não pode ser removida. Método `project()` recalcula as coordenadas normalizadas (SCN) de todos os objetos aplicando a projeção da window — paralela ortogonal ou perspectiva, conforme `window.projection_mode`.

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

### transform3d.py

Transformações 3D em coordenadas homogêneas — matrizes 4×4, mesma convenção de vetores-linha do `transform.py` (`p' = p · M`).

Matrizes básicas: `translation_matrix`, `scaling_matrix`, `rotation_x/y/z_matrix`.

Transformações compostas:
- `rotation_around_axis_matrix(angle, point, direction)`: rotação em torno de um eixo arbitrário (transladar eixo para a origem → alinhar com Z → rotacionar em Z → desfazer)
- `rotation_around_center_matrix(angle, axis, obj)`: rotação no eixo X/Y/Z em torno do centro do objeto
- `natural_scaling_matrix(sx, sy, sz, obj)`: escalonamento em torno do centro do objeto
- `apply_transform_3d(obj, matrix)`: aplica uma matriz 4×4 a todas as coordenadas 3D de um objeto

Projeção:
- `view_matrix(window)`: matriz que leva um ponto do mundo para as coordenadas de view (VRP na origem, VPN alinhado a +Z) — base comum das duas projeções
- `align_to_z_matrix(n, up)`: matriz que rotaciona um vetor para o eixo +Z (constrói uma base ortonormal)
- `project_view_point(p, window)`: projeta um ponto (em coordenadas de view) para o SCN 2D, conforme o modo da window; devolve `None` se o ponto está atrás do COP
- `project_view_segment(a, b, window)`: projeta um segmento de reta para o SCN 2D, fazendo o clipping de near-plane antes da divisão perspectiva

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

Clipagem de curvas (Bézier e B-Spline):
- `clip_curve(curve_points)`: aplica point clipping em cada amostra da curva discretizada. Como uma curva pode sair e voltar a entrar na janela várias vezes, retorna uma lista de sub-trechos (cada um é uma lista contígua de pontos visíveis). Segue a sugestão do slide 5.6 ("verifico se o fim do próximo segmento t/k está dentro do window usando clipping de pontos"). É usado tanto para curvas de Bézier quanto para B-Splines

### main.py

- Cria a window (600x600) e o display file
- Painel esquerdo: lista de objetos, controles de pan/zoom/rotação/reset, campo de step (%)
- Painel "Camera 3D": navegação da câmera no espaço 3D (Forward/Back, Pitch, Yaw)
- Painel "Projection": radio buttons Parallel/Perspective, campo "COP dist" e botões "Wide angle"/"Telephoto" para variar o centro de projeção
- Radio buttons para seleção do algoritmo de clipagem de retas (Cohen-Sutherland / Liang-Barsky)
- Canvas de 800x800 com viewport interna menor (margem de 5%) e moldura vermelha para visualização do clipping
- Dialog para adicionar objetos (Point, Line, Wireframe, Curve, B-Spline, 3D Object, Surface e B-Spline Surf) com abas, seleção de cor, opção de preenchimento para wireframes e entrada livre de pontos de controle para curvas e superfícies
- Remoção de objetos selecionados na lista
- Validação de nomes duplicados
- Dialog de transformações com lista de operações pendentes (transformações 2D e 3D, conforme o objeto)
- Botões de importação/exportação de .obj 2D e de carga de modelos de arame 3D ("Load 3D .obj")

## Pipeline de visualização

```
Mundo 3D (x,y,z) → Projeção (Paralela Ortogonal ou Perspectiva) → SCN 2D [-1,1] → Clipping (em SCN) → scn_to_viewport → Pixels
```

A cada redraw, as coordenadas normalizadas (SCN) de todos os objetos são recalculadas com base na câmera 3D (VRP/VPN/VUP), no tamanho da window e no modo de projeção (paralela ou perspectiva). Objetos 2D são tratados como pontos 3D com `z = 0`. As coordenadas do mundo nunca são alteradas pela navegação da window. A transformada de viewport é aplicada apenas aos objetos resultantes do clipping.

## 3D — Pontos, Objetos e Projeção Paralela Ortogonal

A partir do Trabalho 1.7 o sistema é 3D. Objetos 2D continuam funcionando como caso particular (`z = 0`) e, com a câmera na configuração inicial (VRP na origem, VPN = +Z, VUP = +Y), a visualização é idêntica ao sistema 2D anterior.

**Point3D e Object3D**: o `Point3D` realiza as 3 transformações básicas; o `Object3D` é um modelo de arame (lista de segmentos de reta, cada um um par de Pontos3D) capaz das 3 operações básicas e da rotação em torno de um eixo arbitrário. No diálogo "Add Object", a aba **3D Object** recebe os vértices `(x,y,z),...` e os segmentos como pares de índices `(i,j),...` (com um cubo pré-preenchido como exemplo).

**Navegação 3D da window**: o painel "Camera 3D" adiciona movimento ao longo do VPN (Forward/Back), inclinação (Pitch) e giro lateral (Yaw). Os controles existentes de Pan/Zoom/Rotate passam a operar a câmera no espaço 3D (Rotate = roll em torno do VPN).

**Projeção Paralela Ortogonal** (`parallel_projection_matrix`): implementa o algoritmo visto em aula —
1. Transladar o VRP (primeiro ponto / origem da câmera) para a origem do mundo.
2. Alinhar o VPN com o eixo Z. **Ao final desta etapa o VPN é (0, 0, 1)**, paralelo ao eixo Z — o VUP orienta o eixo Y.
3. Projetar ortogonalmente sobre o plano XY (descartar a coordenada z).
4. Normalizar para o SCN [-1, 1] pelo tamanho da window.

Os segmentos dos objetos 3D, já projetados, são clipados individualmente como retas (Cohen-Sutherland ou Liang-Barsky).

> Limitação: objetos 3D (Point3D/Object3D) não são exportados para `.obj`. A leitura de modelos de arame 3D é feita por `load_obj_3d` (botão "Load 3D .obj").

## Projeção em Perspectiva

Além da projeção paralela ortogonal, a window suporta **projeção em perspectiva**, selecionável pelo painel "Projection" (radio buttons Parallel/Perspective).

O **Centro de Projeção (COP)** é virtual e fica **atrás do plano de projeção**, em `z = -d` nas coordenadas de view, onde `d = cop_distance`. Após a matriz de view (VRP na origem, VPN em +Z), o plano de projeção é `z = 0`. Um ponto `(x, y, z)` projeta-se sobre esse plano pela reta que o liga ao COP — por semelhança de triângulos:

```
x_p = x · d / (z + d)        y_p = y · d / (z + d)
```

**Variação do COP** (botões "Wide angle" / "Telephoto" e campo "COP dist"):
- COP **próximo** do plano (d pequeno) → forte distorção, efeito **grande angular**;
- COP **distante** (d grande) → pouca distorção, efeito **teleobjetiva**;
- quando `d → ∞`, a perspectiva tende à projeção paralela.

**Clipping 2D**: a perspectiva projeta cada segmento de reta dos objetos 3D para o SCN 2D, e o clipping é feito **em 2D** com os algoritmos existentes (Cohen-Sutherland / Liang-Barsky). Antes da divisão perspectiva, os segmentos passam por um clipping de *near-plane* (em coordenadas de view) para descartar a parte que está atrás do COP — sem ele, pontos atrás do COP gerariam projeções inválidas.

Para montar uma cena: adicione objetos 3D pela aba "3D Object" e/ou carregue modelos de arame com "Load 3D .obj". O arquivo de exemplo `models/paralelepipedo.obj` traz um paralelepípedo (200×100×300) pronto para visualizar em perspectiva.

## Superfícies Bicúbicas de Bézier (Trabalho 1.9)

Superfícies 3D representadas por suas **matrizes de geometria**. Cada superfície é uma lista de retalhos (*patches*); cada retalho é uma matriz 4x4 de 16 pontos de controle 3D. A superfície é desenhada avaliando a **função de suavização para superfícies bicúbicas**:

```
P(s,t) = S · M_B · G · M_B^T · T^T      S = [s³ s² s 1]   T = [t³ t² t 1]
```

para cada coordenada (`x`, `y`, `z`), com `s` e `t` discretizados em `STEPS = 10` subdivisões. Os pontos amostrados são ligados numa **malha de iso-curvas** nas direções `s` e `t`.

**Integração com o pipeline 3D**: a malha é avaliada em **coordenadas de view** (3D) — válido porque a matriz de view é afim — e cada segmento é então projetado (paralela ortogonal ou perspectiva) e clipado em 2D, exatamente como as arestas de um `Object3D`. Assim a superfície aparece corretamente em ambas as projeções, incluindo o clipping de *near-plane* da perspectiva. As superfícies também sofrem as transformações 3D (matrizes 4x4).

**Superfície composta**: retalhos adjacentes que compartilham os pontos de controle de borda formam uma superfície composta contínua (continuidade G(0) por construção). O arquivo de exemplo `models/superficie_bezier.obj` traz uma superfície composta por **3 retalhos**, carregável pelo botão "Load 3D .obj (wireframe)".

### Entrada de dados (aba *Surface*)

No mesmo padrão dos demais objetos, com as **linhas da matriz de geometria separadas por `;`** e 4 pontos `(x,y,z)` por linha. Cada grupo de 4 linhas (4x4 = 16 pontos) forma um retalho; basta repetir para entrar com mais retalhos:

```
(x11,y11,z11),(x12,y12,z12),(x13,y13,z13),(x14,y14,z14);
(x21,y21,z21),(x22,y22,z22),(x23,y23,z23),(x24,y24,z24);
(x31,y31,z31),(x32,y32,z32),(x33,y33,z33),(x34,y34,z34);
(x41,y41,z41),(x42,y42,z42),(x43,y43,z43),(x44,y44,z44)
```

### Superfícies no .obj

Cada retalho é gravado como uma linha **`surf`** com os 16 índices dos pontos de controle (diretiva customizada, análoga à `curv`/`bspl`). Vários `surf` sob o mesmo objeto `o` compõem uma superfície de múltiplos retalhos. Os vértices são lidos em 3D (`v x y z`) por `load_obj_3d`. Como o clipping é em 2D, a superfície é projetada antes de recortada.

## Superfícies B-Spline por Diferenças Adiante (Trabalho 1.10)

Superfícies bicúbicas **B-Spline** desenhadas pelo **Método das Diferenças Adiante** (Forward Differences). Valem todos os requisitos das superfícies de Bézier (Trabalho 1.9).

**Entrada flexível**: o usuário entra com uma **matriz de pontos de controle de qualquer dimensão entre 4x4 e 20x20**. O SGI **subdivide automaticamente** em (n−3)×(m−3) retalhos — cada um uma janela deslizante 4×4 sobre a matriz, exatamente como a curva B-Spline desliza uma janela de 4 pontos. Os retalhos têm continuidade C(2) por construção.

**Forward Differences (2D)**: cada retalho é uma superfície bicúbica B-Spline `P(s,t) = S · M_BS · G · M_BS^T · T^T`. Em vez de avaliar esse polinômio a cada passo, pré-calcula-se **uma única vez** a matriz de diferenças:

```
C  = M_BS · G · M_BS^T            (coeficientes do retalho, por coordenada)
DD = E(δs) · C · E(δt)^T          (matriz de diferenças adiante 2D)
```

onde `E(δ)` converte os coeficientes de um cúbico nas suas diferenças adiante iniciais `[f, Δf, Δ²f, Δ³f]`. Toda a grade de pontos do retalho é então gerada **apenas com somas** (varredura em s atualizando as linhas de `DD`; varredura em t gerando cada iso-curva).

**Correção do algoritmo de Foley & van Dam**: o pseudocódigo do livro tem dois erros — ao desenhar cada iso-curva ele corrompe a matriz `DD` necessária para o avanço na outra direção. Aqui, cada iso-curva em t é percorrida sobre uma **cópia** da primeira linha de `DD`, deixando `DD` intacta para o avanço em s. Assim nenhuma varredura destrói as diferenças da outra.

**Entrada de dados (aba *B-Spline Surf*)**: mesmo padrão, linhas da matriz separadas por `;`, pontos `(x,y,z)` por linha — qualquer matriz de 4x4 a 20x20:

```
(x11,y11,z11),(x12,y12,z12),...,(x1m,y1m,z1m);
(x21,y21,z21),(x22,y22,z22),...,(x2m,y2m,z2m);
...
(xn1,yn1,zn1),(xn2,yn2,zn2),...,(xnm,ynm,znm)
```

**No .obj**: diretiva customizada `bsurf <linhas> <colunas> <i1> <i2> ...` com os índices da matriz n×m em ordem linha-a-linha (a subdivisão é automática na carga). O arquivo de exemplo `models/superficie_bspline.obj` traz uma matriz 6×6 (9 retalhos). Carregue com o botão "Load 3D .obj (wireframe)".

## Clipping

O clipping é realizado em coordenadas SCN, após a normalização e antes da transformação de viewport. A janela de clipping é definida como `[-0.90, -0.90, 0.90, 0.90]` (margem de 5% em cada lado), de modo que a viewport é menor que o canvas — a moldura vermelha ao redor torna erros de clipping imediatamente visíveis.

Técnicas implementadas:
- **Pontos**: teste de pertinência no retângulo de clipping
- **Retas**: Cohen-Sutherland e Liang-Barsky (intercambiáveis via radio button no painel)
- **Polígonos preenchidos**: Sutherland-Hodgman (processa os vértices contra cada aresta da janela, fechando o polígono na borda de clipping)
- **Wireframes (não preenchidos)**: cada aresta é clipada individualmente como linha (usando o algoritmo selecionado no radio button), evitando arestas falsas ao longo da borda de clipping
- **Curvas**: point clipping em cada amostra discretizada (conforme slide 5.6)
- **Superfícies e objetos 3D**: cada segmento de reta (aresta do `Object3D` ou da malha da superfície) é projetado para o SCN 2D e clipado individualmente como linha. O clipping permanece **em 2D**

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
- Curva (Bézier): `(x1,y1),(x2,y2),...` com 4, 7, 10, 13, ... pontos (ex: 4 pontos `(0,0),(50,150),(100,150),(150,0)`; 7 pontos encadeiam duas curvas com G(0)).
- B-Spline: `(x1,y1),(x2,y2),...` com qualquer quantidade de pontos ≥ 4 (ex: `(0,0),(50,150),(100,150),(150,0),(200,-50)` → 5 pontos geram 2 segmentos).
- 3D Object: vértices `(x1,y1,z1),(x2,y2,z2),...` e arestas como pares de índices `(i,j),(i,j),...`.
- Superfície (bicúbica de Bézier): linhas da matriz separadas por `;`, 4 pontos `(x,y,z)` por linha, cada 4 linhas = 1 retalho (ver seção *Superfícies Bicúbicas de Bézier*).
- Superfície B-Spline: matriz n×m de qualquer dimensão entre 4x4 e 20x20, linhas separadas por `;`, pontos `(x,y,z)` por linha — subdivisão automática (ver seção *Superfícies B-Spline por Diferenças Adiante*).

## B-Spline com Forward Differences

A classe `BSpline` implementa uma curva B-Spline uniforme cúbica, avaliada pela técnica de **Forward Differences** (Trabalho 1.6):

1. Para cada grupo de 4 pontos de controle consecutivos (janela deslizante), os coeficientes do polinômio cúbico `P(t) = a t³ + b t² + c t + d` são obtidos por `C = M_BS · G`, onde `M_BS` é a matriz base da B-Spline uniforme (com fator 1/6) e `G` é a geometria dos 4 pontos.
2. Em vez de reavaliar `P(t)` (com potências de `t`) a cada passo, calculam-se **uma única vez** os incrementos iniciais `Δ = P(δ) − P(0)`, `Δ²` e `Δ³` (com `δ = 1/STEPS`).
3. Cada ponto seguinte é gerado **apenas com somas**: `f += Δ`, `Δ += Δ²`, `Δ² += Δ³`.

O usuário pode entrar com **qualquer número de pontos de controle (mínimo 4)**; `n` pontos produzem `n − 3` segmentos encadeados com continuidade C(2). O clipping reaproveita `clip_curve` (point clipping por amostra).
