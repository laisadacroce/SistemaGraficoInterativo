display_file = []

class ObjetoGrafico:
    def __init__(self, nome, tipo, coordenadas):
        self.nome = nome
        self.tipo = tipo
        self.coordenadas = coordenadas

    def __str__(self):
        return f"{self.tipo.capitalize()}[{self.nome}]"