"""Máquina que ejecuta el código de tres direcciones de PixelLang.

Sirve para validar el código intermedio antes de tener el back end con LLVM:
cada bloque simular se ejecuta sobre el TAC y se muestra el estado del personaje
y sus atributos después de cada evento. Cada personaje tiene su propia memoria,
porque dos personajes pueden tener atributos con el mismo nombre. Los enteros son
de 32 bits, como el tipo i32 de LLVM: un resultado fuera de ese rango es un error
de ejecución, igual que una división entre cero.
"""
from codigo_intermedio import formatear_tac

MINIMO, MAXIMO = -2 ** 31, 2 ** 31 - 1    # rango de un entero de 32 bits


class ErrorEjecucion(Exception):
    pass


def entero_32(valor):
    """Comprueba que un entero quepa en 32 bits; los reales y los lógicos pasan igual."""
    if type(valor) is int and not MINIMO <= valor <= MAXIMO:
        raise ErrorEjecucion("desbordamiento de entero")
    return valor


def dividir(a, b):
    if b == 0:
        raise ErrorEjecucion("división entre cero")
    if isinstance(a, int) and isinstance(b, int):
        cociente = abs(a) // abs(b)   # la división entera se trunca hacia cero, como sdiv
        return cociente if (a >= 0) == (b >= 0) else -cociente
    return a / b


OPERACIONES = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": dividir,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class MaquinaTAC:
    def __init__(self, codigo, estados):
        self.codigo = codigo
        self.estados = estados             # personaje -> nombres de sus estados
        self.etiquetas = {i.resultado: k for k, i in enumerate(codigo) if i.op == "label"}
        self.memorias = {p: {} for p in estados}

    def valor(self, arg, personaje):
        if arg in ("verdadero", "falso"):
            return arg == "verdadero"
        if arg[0].isdigit():
            return float(arg) if "." in arg else entero_32(int(arg))
        if arg in self.estados[personaje]:   # los nombres de estado son constantes
            return arg
        return self.memorias[personaje][arg]

    def ejecutar(self, procedimiento):
        personaje = procedimiento.split(".")[0]
        memoria = self.memorias[personaje]
        k = self.etiquetas[procedimiento] + 1
        while True:
            i = self.codigo[k]
            k += 1
            if i.op == "return":
                return
            if i.op == "call":
                self.ejecutar(i.arg1)
                continue
            try:
                if i.op == "goto":
                    k = self.etiquetas[i.resultado]
                elif i.op == "if":
                    if self.valor(i.arg1, personaje):
                        k = self.etiquetas[i.resultado]
                elif i.op == "ifFalse":
                    if not self.valor(i.arg1, personaje):
                        k = self.etiquetas[i.resultado]
                elif i.op != "label":
                    memoria[i.resultado] = entero_32(self.calcular(i, personaje))
            except ErrorEjecucion as e:
                raise ErrorEjecucion(f"{e} en {procedimiento}: {formatear_tac(i)}")

    def calcular(self, i, personaje):
        """El valor que una instrucción guarda en su resultado."""
        a = self.valor(i.arg1, personaje)
        if i.op == "copy": return a
        if i.op == "minus": return -a
        if i.op == "!": return not a
        if i.op == "intToFloat": return float(a)
        return OPERACIONES[i.op](a, self.valor(i.arg2, personaje))


def mostrar(valor):
    if isinstance(valor, bool):
        return "verdadero" if valor else "falso"
    if isinstance(valor, float):
        texto = f"{valor:.6f}".rstrip("0")
        return texto + "0" if texto.endswith(".") else texto
    return str(valor)


def trazas(programa, codigo):
    """Ejecuta cada procedimiento simular_N. Devuelve, por simulación, el nombre
    del personaje y la lista de pasos (evento, estado, valores de los atributos).
    Si ocurre un error de ejecución, el último paso es (evento, None, mensaje)."""
    estados = {pj.nombre: {e.nombre for e in pj.estados} for pj in programa.personajes}
    atributos = {pj.nombre: [a.nombre for a in pj.atributos] for pj in programa.personajes}
    maquina = MaquinaTAC(codigo, estados)
    resultado = []
    for k, sim in enumerate(programa.simulaciones, 1):
        p = sim.personaje
        maquina.memorias[p] = {}           # cada simulación empieza desde cero
        pasos = []
        inicio = maquina.etiquetas[f"simular_{k}"] + 1
        for i in codigo[inicio:]:
            if i.op != "call":
                break
            evento = i.arg1.split(".cuando_", 1)[1] if ".cuando_" in i.arg1 else "inicio"
            try:
                maquina.ejecutar(i.arg1)
            except ErrorEjecucion as e:
                pasos.append((evento, None, str(e)))
                break
            memoria = maquina.memorias[p]
            pasos.append((evento, memoria["estado"], [memoria[a] for a in atributos[p]]))
        resultado.append((p, pasos))
    return resultado


def simular(programa, codigo):
    """La traza de trazas() como texto: una línea por evento."""
    atributos = {pj.nombre: [a.nombre for a in pj.atributos] for pj in programa.personajes}
    lineas = []
    for p, pasos in trazas(programa, codigo):
        if lineas:
            lineas.append("")
        lineas.append(f"simular {p}")
        for evento, estado, valores in pasos:
            if estado is None:
                lineas.append(f"  {evento:<17} error de ejecución: {valores}")
                continue
            texto = " ".join(f"{a}={mostrar(v)}" for a, v in zip(atributos[p], valores))
            lineas.append(f"  {evento:<17} -> {estado:<12} {texto}".rstrip())
    return lineas
