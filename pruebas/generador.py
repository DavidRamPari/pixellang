"""Generador de programas PixelLang válidos al azar, para la prueba diferencial
de probar_generados.py.

Cada programa respeta las reglas del analizador semántico: tipos compatibles,
todos los estados alcanzables desde el inicial, por cada estado y evento las
transiciones con guarda primero y a lo más una sin guarda al final, estados
finales sin transiciones y nombres distintos. Las expresiones combinan todos los
operadores, enteros con reales, cadenas sin paréntesis (a - b - c) y divisiones
que pueden ser entre cero.
"""
ARITMETICOS = ["+", "-", "*", "/"]
RELACIONALES = ["<", ">", "<=", ">=", "==", "!="]


class Generador:
    def __init__(self, rng):
        self.rng = rng
        self.atributos = []      # (nombre, tipo) de los atributos ya declarados

    def hoja(self, tipo):
        nombres = [a for a, t in self.atributos if t == tipo]
        if nombres and self.rng.random() < 0.6:
            return self.rng.choice(nombres)
        if tipo == "entero":
            return str(self.rng.randint(0, 9))
        if tipo == "real":
            return self.rng.choice(["0.0", "0.5", "1.0", "2.5", "3.75", "10.0"])
        return self.rng.choice(["verdadero", "falso"])

    @staticmethod
    def par(texto):
        """Pone entre paréntesis todo lo que no sea un nombre o un literal."""
        simple = texto.replace("_", "").replace(".", "").isalnum()
        return texto if simple else f"({texto})"

    def numerica(self, nivel):
        return self.expr(self.rng.choice(["entero", "real"]), nivel)

    def expr(self, tipo, nivel):
        r = self.rng.random()
        if nivel == 0 or r < 0.3:
            return self.hoja(tipo)
        if tipo == "logico":
            if r < 0.45:
                return "!" + self.par(self.expr("logico", nivel - 1))
            if r < 0.7:
                return (f"{self.par(self.numerica(nivel - 1))} {self.rng.choice(RELACIONALES)} "
                        f"{self.par(self.numerica(nivel - 1))}")
            if r < 0.78:
                return (f"{self.par(self.expr('logico', nivel - 1))} {self.rng.choice(['==', '!='])} "
                        f"{self.par(self.expr('logico', nivel - 1))}")
            partes = [self.par(self.expr("logico", nivel - 1)) for _ in range(self.rng.randint(2, 3))]
            texto = partes[0]
            for p in partes[1:]:          # && y || mezclados prueban la precedencia
                texto += f" {self.rng.choice(['&&', '||'])} {p}"
            return texto
        if r < 0.4:
            return "-" + self.par(self.expr(tipo, nivel - 1))
        if tipo == "entero" and r < 0.55:   # cadena de la misma precedencia: a - b - c
            grupo = self.rng.choice([["+", "-"], ["*", "/"]])
            texto = self.par(self.expr("entero", nivel - 1))
            for _ in range(self.rng.randint(1, 3)):
                texto += f" {self.rng.choice(grupo)} {self.par(self.expr('entero', nivel - 1))}"
            return texto
        # en un real basta con que un operando sea real; el otro puede ser entero
        izquierda = self.expr(tipo, nivel - 1)
        derecha = self.expr("entero" if tipo == "real" and self.rng.random() < 0.4 else tipo, nivel - 1)
        if self.rng.random() < 0.5:
            izquierda, derecha = derecha, izquierda
        return f"{self.par(izquierda)} {self.rng.choice(ARITMETICOS)} {self.par(derecha)}"

    def valor_para(self, tipo):
        if tipo == "real" and self.rng.random() < 0.3:
            return self.expr("entero", 2)  # un entero se puede asignar a un real
        return self.expr(tipo, 2)

    def bloque(self, nivel, sangria):
        texto = ""
        for _ in range(self.rng.randint(0, 3)):
            if nivel > 0 and self.rng.random() < 0.3:
                texto += f"{sangria}si {self.expr('logico', 2)} {{\n"
                texto += self.bloque(nivel - 1, sangria + "    ") + f"{sangria}}}"
                if self.rng.random() < 0.5:
                    texto += " sino {\n" + self.bloque(nivel - 1, sangria + "    ") + f"{sangria}}}"
                texto += "\n"
            else:
                nombre, tipo = self.rng.choice(self.atributos)
                texto += f"{sangria}{nombre} = {self.valor_para(tipo)};\n"
        return texto

    def personaje(self, nombre):
        self.atributos = []
        texto = f"personaje {nombre} {{\n"
        for k in range(self.rng.randint(1, 5)):
            tipo = self.rng.choice(["entero", "entero", "real", "logico"])
            # algunos atributos se llaman como los temporales del TAC (t1, t2...)
            atributo = f"a{k}" if self.rng.random() < 0.8 else f"t{k + 1}"
            texto += f"    {atributo}: {tipo} = {self.valor_para(tipo)};\n"
            self.atributos.append((atributo, tipo))
        eventos = [f"e{k}" for k in range(self.rng.randint(1, 4))]
        texto += f"    eventos {', '.join(eventos)};\n"
        estados = [f"S{k}" for k in range(self.rng.randint(1, 5))]
        final = estados[-1] if len(estados) > 1 and self.rng.random() < 0.5 else None
        for k, s in enumerate(estados):
            modificador = "inicial " if k == 0 else ("final " if s == final else "")
            texto += f"    {modificador}estado {s} {{\n"
            if self.rng.random() < 0.7:
                texto += "        al_entrar {\n" + self.bloque(2, " " * 12) + "        }\n"
            if s != final:
                texto += self.transiciones(eventos, estados, k)
            texto += "    }\n"
        return texto + "}\n", eventos

    def transiciones(self, eventos, estados, k):
        por_evento = {}
        if k + 1 < len(estados):         # una cadena S0 -> S1 -> ... hace alcanzables a todos
            por_evento.setdefault(self.rng.choice(eventos), [[], []])[1].append(estados[k + 1])
        for ev in self.rng.sample(eventos, self.rng.randint(0, len(eventos))):
            listas = por_evento.setdefault(ev, [[], []])
            listas[0].extend(self.rng.choice(estados) for _ in range(self.rng.randint(0, 2)))
            if self.rng.random() < 0.5:
                listas[1].append(self.rng.choice(estados))
        texto = ""
        for ev, (con_guarda, sin_guarda) in por_evento.items():
            for destino in con_guarda:
                texto += f"        cuando {ev} si {self.expr('logico', 2)} -> {destino};\n"
            if sin_guarda:               # E03: una sola sin guarda y al final
                texto += f"        cuando {ev} -> {sin_guarda[0]};\n"
        return texto


def generar_programa(rng):
    gen = Generador(rng)
    texto, simulaciones = "", ""
    for k in range(rng.randint(1, 2)):
        nombre = f"P{k}"
        personaje, eventos = gen.personaje(nombre)
        texto += personaje
        for _ in range(rng.randint(1, 2)):
            secuencia = ", ".join(rng.choice(eventos) for _ in range(rng.randint(1, 12)))
            simulaciones += f"simular {nombre}: {secuencia};\n"
    return texto + simulaciones
