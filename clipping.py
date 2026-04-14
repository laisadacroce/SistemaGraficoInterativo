# ── Clipping algorithms ─────────────────────────────────
# Todos os algoritmos operam em coordenadas SCN (normalizadas),
# onde a janela de clipping é ligeiramente menor que [-1, 1]
# para deixar uma margem visível ao redor da viewport.

MARGIN = 0.05  # 5% de margem em cada lado

CLIP_MIN = -1 + 2 * MARGIN   # ≈ -0.90
CLIP_MAX =  1 - 2 * MARGIN   # ≈  0.90


# ── Region codes para Cohen-Sutherland ──────────────────
# Convenção: RC[4]=esquerda, RC[3]=direita, RC[2]=abaixo, RC[1]=acima
# Representados como bits: left=1, right=2, bottom=4, top=8

INSIDE = 0   # 0000
LEFT   = 1   # 0001
RIGHT  = 2   # 0010
BOTTOM = 4   # 0100
TOP    = 8   # 1000


def _region_code(x, y):
    """Atribui um region code de 4 bits a um ponto, comparando suas
    coordenadas com os limites da janela de clipping.

    Conforme slide 'Algoritmo Geral para Recorte de Linhas de C-S':
    P1: Associar códigos aos pontos extremos c/regra:
      se x < x_min  então RC[4] <- 1 senão RC[4] <- 0
      se x > x_max  então RC[3] <- 1 senão RC[3] <- 0
      se y < y_min   então RC[2] <- 1 senão RC[2] <- 0
      se y > y_max   então RC[1] <- 1 senão RC[1] <- 0"""
    code = INSIDE
    if x < CLIP_MIN:
        code |= LEFT
    elif x > CLIP_MAX:
        code |= RIGHT
    if y < CLIP_MIN:
        code |= BOTTOM
    elif y > CLIP_MAX:
        code |= TOP
    return code


# ── Clipagem de Pontos ──────────────────────────────────

def clip_point(x, y):
    """Retorna True se o ponto está dentro da janela de clipping.
    Realiza a comparação de intervalos:
      Xw_min <= X <= Xw_max  e  Yw_min <= Y <= Yw_max"""
    return CLIP_MIN <= x <= CLIP_MAX and CLIP_MIN <= y <= CLIP_MAX


# ── Cohen-Sutherland ────────────────────────────────────

def cohen_sutherland(x1, y1, x2, y2):
    """Clipa um segmento de reta usando Cohen-Sutherland.

    Conforme slides 'Algoritmo Geral para Recorte de Linhas de C-S':
    P2: Verificar se a linha é totalmente visível, invisível ou parcialmente:
      - Completamente contida: RC_inicio = RC_fim = [0000]
      - Completamente fora:    RC_inicio & RC_fim <> [0000]
      - Parcialmente:          RC_inicio <> RC_fim e RC_inicio & RC_fim = [0000]

    P3: Se parcialmente visível, calcular intersecções:
      Esquerda: y = m * (x_E - x1) + y1       (m diferente de 0)
      Direita:  y = m * (x_D - x1) + y1
      Topo:     x = x1 + 1/m * (y_T - y1)
      Fundo:    x = x1 + 1/m * (y_F - y1)

    Retorna (x1, y1, x2, y2) clipados ou None se completamente fora."""
    code1 = _region_code(x1, y1)
    code2 = _region_code(x2, y2)

    while True:
        # Completamente visível — ambos os códigos são 0000
        if code1 == 0 and code2 == 0:
            return (x1, y1, x2, y2)

        # Completamente invisível — AND lógico diferente de 0000
        if code1 & code2 != 0:
            return None

        # Parcialmente visível — calcular intersecções
        code_out = code1 if code1 != 0 else code2

        # Coeficiente angular m = (y2 - y1) / (x2 - x1)
        if x2 != x1:
            m = (y2 - y1) / (x2 - x1)
        else:
            m = float('inf')

        # Calcular intersecção com a borda correspondente
        if code_out & TOP:
            # Topo: x = x1 + 1/m * (y_T - y1)
            xi = x1 + (1 / m) * (CLIP_MAX - y1) if m != 0 else x1
            yi = CLIP_MAX
        elif code_out & BOTTOM:
            # Fundo: x = x1 + 1/m * (y_F - y1)
            xi = x1 + (1 / m) * (CLIP_MIN - y1) if m != 0 else x1
            yi = CLIP_MIN
        elif code_out & RIGHT:
            # Direita: y = m * (x_D - x1) + y1
            xi = CLIP_MAX
            yi = y1 + m * (CLIP_MAX - x1)
        elif code_out & LEFT:
            # Esquerda: y = m * (x_E - x1) + y1
            xi = CLIP_MIN
            yi = y1 + m * (CLIP_MIN - x1)

        # Substituir o ponto que estava fora e recalcular seu código
        if code_out == code1:
            x1, y1 = xi, yi
            code1 = _region_code(x1, y1)
        else:
            x2, y2 = xi, yi
            code2 = _region_code(x2, y2)


# ── Liang-Barsky ────────────────────────────────────────

def liang_barsky(x1, y1, x2, y2):
    """Clipa um segmento de reta usando Liang-Barsky.

    Conforme slides 'Liang-Barsky Line Clipping':
    Representação paramétrica da reta:
      x = x1 + u * Δx,  y = y1 + u * Δy,  0 <= u <= 1

    Parâmetros p e q:
      p1 = -Δx,  q1 = x1 - xw_min
      p2 =  Δx,  q2 = xw_max - x1
      p3 = -Δy,  q3 = y1 - yw_min
      p4 =  Δy,  q4 = yw_max - y1

    Condições:
      p_k = 0: paralela a um dos limites (q_k < 0 → fora, q_k >= 0 → dentro)
      p_k < 0: a linha vem de fora para dentro  → r_k contribui para ζ1
      p_k > 0: a linha vem de dentro para fora  → r_k contribui para ζ2

    Definição dos parâmetros ζ:
      ζ1 = max(0, r_k's para p_k < 0)   — de fora para dentro
      ζ2 = min(1, r_k's para p_k > 0)   — de dentro para fora
      Se ζ1 > ζ2, a linha está completamente fora.

    Retorna (x1, y1, x2, y2) clipados ou None se completamente fora."""
    dx = x2 - x1
    dy = y2 - y1

    p = [-dx, dx, -dy, dy]
    q = [x1 - CLIP_MIN, CLIP_MAX - x1, y1 - CLIP_MIN, CLIP_MAX - y1]

    zeta1 = 0.0  # ζ1: limite inferior (fora para dentro)
    zeta2 = 1.0  # ζ2: limite superior (dentro para fora)

    for k in range(4):
        if p[k] == 0:
            # Linha paralela a este limite
            if q[k] < 0:
                return None  # fora dos limites
            # Se q[k] >= 0, está dentro — continuar
        else:
            r = q[k] / p[k]
            if p[k] < 0:
                # Fora para dentro: ζ1 = max(0, r_k's)
                zeta1 = max(zeta1, r)
            else:
                # Dentro para fora: ζ2 = min(1, r_k's)
                zeta2 = min(zeta2, r)

    # Se ζ1 > ζ2, a linha está completamente fora
    if zeta1 > zeta2:
        return None

    # Substituir na equação paramétrica: x = x1 + ζ * Δx
    x1c = x1 + zeta1 * dx
    y1c = y1 + zeta1 * dy
    x2c = x1 + zeta2 * dx
    y2c = y1 + zeta2 * dy
    return (x1c, y1c, x2c, y2c)


# ── Sutherland-Hodgman (polígonos) ──────────────────────

def sutherland_hodgman(polygon):
    """Clipa um polígono usando Sutherland-Hodgman.

    Conforme slides 'Clipping de Polígonos de Sutherland-Hodgman':
    Processa as bordas do polígono como um todo contra cada aresta do window.
    Todos os vértices são processados contra cada uma das 4 arestas.

    Para cada par de vértices adjacentes, 4 casos:
      out → in:  salva intersecção + vértice atual
      in  → in:  salva vértice atual
      in  → out: salva intersecção
      out → out: salva nada

    Lista de vértices intermediários:
    Cada vez que clipamos contra uma borda, regeneramos o polígono.
    Este novo polígono é clipado contra a próxima borda.

    polygon: lista de tuplas (x, y) dos vértices em SCN.
    Retorna lista de (x, y) do polígono clipado, ou lista vazia."""

    def _inside(point, edge_type, edge_val):
        """Verifica se um ponto está do lado 'dentro' de uma aresta."""
        x, y = point
        if edge_type == 'LEFT':
            return x >= edge_val
        elif edge_type == 'RIGHT':
            return x <= edge_val
        elif edge_type == 'BOTTOM':
            return y >= edge_val
        elif edge_type == 'TOP':
            return y <= edge_val

    def _intersect(p1, p2, edge_type, edge_val):
        """Calcula o ponto de intersecção de um segmento (p1→p2) com uma aresta."""
        x1, y1 = p1
        x2, y2 = p2

        if x1 == x2:
            m = None  # linha vertical
        else:
            m = (y2 - y1) / (x2 - x1)

        if edge_type in ('LEFT', 'RIGHT'):
            x = edge_val
            y = m * (x - x1) + y1 if m is not None else y1
            return (x, y)
        else:  # BOTTOM ou TOP
            y = edge_val
            x = (y - y1) / m + x1 if m is not None and m != 0 else x1
            return (x, y)

    # Processar sequencialmente contra cada aresta: LEFT, RIGHT, BOTTOM, TOP
    edges = [
        ('LEFT',   CLIP_MIN),
        ('RIGHT',  CLIP_MAX),
        ('BOTTOM', CLIP_MIN),
        ('TOP',    CLIP_MAX),
    ]

    output = list(polygon)

    for edge_type, edge_val in edges:
        if not output:
            break
        inp = output
        output = []
        prev = inp[-1]

        for curr in inp:
            curr_in = _inside(curr, edge_type, edge_val)
            prev_in = _inside(prev, edge_type, edge_val)

            if curr_in:
                if prev_in:
                    # in → in: salva vértice atual
                    output.append(curr)
                else:
                    # out → in: salva intersecção + vértice atual
                    output.append(_intersect(prev, curr, edge_type, edge_val))
                    output.append(curr)
            elif prev_in:
                # in → out: salva intersecção
                output.append(_intersect(prev, curr, edge_type, edge_val))
            # out → out: salva nada

            prev = curr

    return output
