# Rasterização, Z-buffer e Iluminação de Phong — Trabalhos 2.1, 2.2 e 2.3

Extensão do SGI (INE5420) com um pipeline de rasterização por software:
framebuffer próprio, Z-buffer e iluminação de Phong por pixel. Tudo é
construído por cima do SGI existente (2D, curvas, clipping, objetos 3D em
arame, projeções paralela e perspectiva), **sem quebrar** nada do que já
funcionava — o modo de desenho vetorial continua idêntico ao anterior.

## Como rodar

```bash
python3 main.py
```

Requer `numpy` (usado nos buffers e no cálculo de iluminação vetorizado).

## Arquivos novos

```
framebuffer.py → Framebuffer de software: clear, draw_pixel, draw_line
                 (Bresenham), draw_trapezoid, draw_polygon (por trapézios),
                 draw_pixel_depth, draw_triangle (Z-buffer),
                 draw_triangle_phong, to_photoimage
phong.py       → LuzPontual, MaterialPhong, calcular_phong (escalar) e
                 calcular_phong_lote (vetorizado, usado por pixel)
sphere.py      → get_sphere_triangles: esfera UV procedural com normais
                 por vértice (modelo de teste da iluminação)
render.py      → Laço de desenho da cena (extraído de main.py). Escolhe
                 entre desenho vetorial e rasterização pelo framebuffer.
```

`model.py` ganhou a classe `Object3DPhong` (triângulos + normais por
vértice). `main.py` ganhou a seção **Rasterization/Shading** no painel.

## Trabalho 2.1 — Rasterização (framebuffer)

`Framebuffer` guarda a cor RGB (numpy, linha-major) e desenha "na unha":

- `clear` — limpa a cor e **reseta o Z-buffer para +infinito**;
- `draw_pixel` — pixel com recorte trivial;
- `draw_line` — reta por **Bresenham** (aritmética inteira);
- `draw_trapezoid` — trapézio com topo/base horizontais, por scanline;
- `draw_polygon` — preenchimento por varredura, **decompondo em
  trapézios** (usa `draw_trapezoid`); suporta convexos e côncavos simples;
- `to_photoimage` — empacota o buffer em PPM e devolve um `tk.PhotoImage`.

**Integração:** no modo framebuffer, os polígonos 2D preenchidos passam a
ser rasterizados por `draw_polygon` (não mais pelo `create_polygon` do
tkinter), e os objetos 3D em arame por `draw_line`. A imagem é exibida no
canvas e respeita a mesma região de clipping (borda vermelha).

## Trabalho 2.2 — Z-buffer

- buffer de profundidade (float, +infinito no `clear`);
- `draw_pixel_depth` — só escreve se `z < z_buffer` (checagem de
  profundidade), atualizando o buffer;
- `draw_triangle(v0, v1, v2)` com `v = (x_vp, y_vp, z_view)` — rasteriza o
  triângulo por coordenadas baricêntricas (vetorizado em numpy),
  interpola Z linearmente e resolve a oclusão pelo teste de profundidade.

A oclusão fica correta independentemente da ordem de desenho dos
triângulos.

## Trabalho 2.3 — Iluminação de Phong

Modelo de Phong, por canal, com clamping em [0, 1]:

```
I = ka·Ia + kd·(L·N)·Id + ks·(R·V)^n·Is
```

- `LuzPontual` — posição no mundo + intensidade RGB;
- `MaterialPhong` — coeficientes ka/kd/ks e expoente n (shininess);
- `draw_triangle_phong` — rasteriza o triângulo interpolando **a normal**
  (e a posição no mundo, e o Z) **por pixel**, calculando Phong em cada
  pixel. Interpolar a normal (não a cor) é o que torna isto Phong shading
  de verdade — não Gouraud.

O cálculo por pixel é vetorizado (`calcular_phong_lote`) para não travar a
interface ao mover a câmera.

## Como usar na interface

Seção **Rasterization/Shading** (modo de renderização, mutuamente
exclusivo — cada estágio exige o anterior):

- **Vector** — desenho vetorial clássico (sem framebuffer);
- **Framebuffer (wireframe)** — 3D rasterizado como arame (2.1);
- **Z-buffer (solid)** — triângulos sólidos com profundidade (2.2);
- **Phong shading** — iluminação por pixel (2.3).

**Load Sphere** carrega uma esfera de teste à frente da câmera, com a luz
já posicionada para iluminar a face visível, e entra no modo Phong.

Parâmetros (editar + **Enter** redesenha):

- **Light X Y Z** — posição da luz no mundo;
- **Ambient (Ka)**, **Diffuse (Kd)**, **Specular (Ks)** — coeficientes do
  material, de 0 a 1;
- **Shininess (n)** — expoente do brilho especular, de 1 a ~256
  (baixo = brilho grande e mole; alto = pequeno e nítido).

A luz é fixa no mundo; ao girar a câmera, a difusa fica presa ao objeto e o
brilho especular acompanha o observador.

## Limitações conhecidas

- A rasterização de triângulos **não recorta contra o plano near**:
  escalar um sólido a ponto de ele atravessar a câmera produz artefatos
  (o caminho de arame recorta; o de triângulos ainda não).
- A rotação de um `Object3DPhong` transforma os vértices mas ainda **não
  as normais** — invisível numa esfera (simétrica), relevante para sólidos
  assimétricos.

Ambas estão previstas para a etapa de estender o sombreamento a todos os
objetos 3D.
