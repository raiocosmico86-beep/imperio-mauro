import random

class Personagem:
    def __init__(self, nome):
        self.nome = nome
        self.hp_max = 100
        self.hp = 100
        self.ataque = 12
        self.defesa = 5
        self.nivel = 1
        self.xp = 0
        self.xp_proximo = 50
        self.pocoes = 3
        self.ouro = 0

    def esta_vivo(self):
        return self.hp > 0

    def atacar(self, inimigo):
        dano = max(1, self.ataque + random.randint(-3, 5) - inimigo.defesa)
        inimigo.hp -= dano
        return dano

    def curar(self):
        if self.pocoes <= 0:
            return None
        self.pocoes -= 1
        cura = random.randint(20, 35)
        self.hp = min(self.hp_max, self.hp + cura)
        return cura

    def ganhar_xp(self, quantidade):
        self.xp += quantidade
        subiu = False
        while self.xp >= self.xp_proximo:
            self.xp -= self.xp_proximo
            self.nivel += 1
            self.xp_proximo = int(self.xp_proximo * 1.5)
            self.hp_max += 20
            self.hp = self.hp_max
            self.ataque += 4
            self.defesa += 2
            subiu = True
        return subiu

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data):
        p = cls(data["nome"])
        p.__dict__.update(data)
        return p


class Inimigo:
    TIPOS = [
        {"nome": "Goblin",      "hp": 40,  "ataque": 8,  "defesa": 2, "xp": 25, "ouro": 10},
        {"nome": "Lobo Selvagem","hp": 55, "ataque": 11, "defesa": 3, "xp": 35, "ouro": 15},
        {"nome": "Esqueleto",   "hp": 70,  "ataque": 14, "defesa": 6, "xp": 50, "ouro": 25},
        {"nome": "Orc",         "hp": 90,  "ataque": 17, "defesa": 8, "xp": 70, "ouro": 40},
        {"nome": "Dragão",      "hp": 150, "ataque": 25, "defesa": 12,"xp": 150,"ouro": 100},
    ]

    def __init__(self, nivel_jogador=1):
        base = random.choice(self.TIPOS)
        escala = 1 + (nivel_jogador - 1) * 0.2
        self.nome = base["nome"]
        self.hp_max = int(base["hp"] * escala)
        self.hp = self.hp_max
        self.ataque = int(base["ataque"] * escala)
        self.defesa = int(base["defesa"] * escala)
        self.xp = int(base["xp"] * escala)
        self.ouro = int(base["ouro"] * escala)

    def esta_vivo(self):
        return self.hp > 0

    def atacar(self, jogador):
        dano = max(1, self.ataque + random.randint(-3, 3) - jogador.defesa)
        jogador.hp -= dano
        return dano

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data):
        i = cls.__new__(cls)
        i.__dict__.update(data)
        return i
