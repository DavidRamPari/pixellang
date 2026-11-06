"""Intérprete de referencia: ejecuta los bloques simular recorriendo el AST, sin
pasar por el código de tres direcciones.

Es una segunda implementación de la semántica de PixelLang, escrita aparte de la
máquina de TAC, para la prueba diferencial: con el mismo programa las dos deben
dar la misma traza. Si no coinciden, hay un error en la traducción a TAC o en la
máquina.
"""
from ast_pixellang import Asignacion, Logico, Numero, Unaria, Variable


class ErrorReferencia(Exception):
    pass


def evaluar(nodo, memoria):
    if isinstance(nodo, (Numero, Logico)):
        return nodo.valor
    if isinstance(nodo, Variable):
        return memoria[nodo.nombre]
    if isinstance(nodo, Unaria):
        valor = evaluar(nodo.operando, memoria)
        return (not valor) if nodo.op == "!" else -valor
    if nodo.op == "&&":   # cortocircuito: si la izquierda es falsa, no se evalúa la derecha
        return evaluar(nodo.izquierda, memoria) and evaluar(nodo.derecha, memoria)
    if nodo.op == "||":
        return evaluar(nodo.izquierda, memoria) or evaluar(nodo.derecha, memoria)
    a, b = evaluar(nodo.izquierda, memoria), evaluar(nodo.derecha, memoria)
    if isinstance(a, float) or isinstance(b, float):   # entero con real: promoción a real
        a, b = float(a), float(b)
    if nodo.op == "+": return a + b
    if nodo.op == "-": return a - b
    if nodo.op == "*": return a * b
    if nodo.op == "/":
        if b == 0:
            raise ErrorReferencia("división entre cero")
        if isinstance(a, int):
            return -(-a // b) if (a < 0) != (b < 0) else a // b   # hacia cero
        return a / b
    return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b,
            "==": a == b, "!=": a != b}[nodo.op]


def simular_referencia(programa):
    """Devuelve, por simulación, (personaje, pasos) con el mismo formato que
    maquina_tac.trazas: (evento, estado, valores) o (evento, None, mensaje)."""
    personajes = {pj.nombre: pj for pj in programa.personajes}
    resultado = []
    for sim in programa.simulaciones:
        pj = personajes[sim.personaje]
        tipos = {a.nombre: a.tipo for a in pj.atributos}
        estados = {e.nombre: e for e in pj.estados}
        memoria, pasos = {}, []

        def asignar(nombre, valor):
            memoria[nombre] = float(valor) if tipos[nombre] == "real" else valor

        def ejecutar(bloque):
            for s in bloque.sentencias:
                if isinstance(s, Asignacion):
                    asignar(s.nombre, evaluar(s.expresion, memoria))
                elif evaluar(s.condicion, memoria):
                    ejecutar(s.entonces)
                elif s.sino:
                    ejecutar(s.sino)

        def entrar(nombre):
            memoria["estado"] = nombre
            if estados[nombre].al_entrar:
                ejecutar(estados[nombre].al_entrar)

        def anotar(evento):
            pasos.append((evento, memoria["estado"], [memoria[a.nombre] for a in pj.atributos]))

        evento = "inicio"
        try:
            for a in pj.atributos:
                asignar(a.nombre, evaluar(a.valor, memoria))
            entrar(next(e.nombre for e in pj.estados if e.modificador == "inicial"))
            anotar(evento)
            for evento in sim.eventos:
                # la primera transición con el evento cuya guarda se cumple; si no
                # hay ninguna (o el estado es final), el personaje se queda
                for t in estados[memoria["estado"]].transiciones:
                    if t.evento == evento and (t.guarda is None or evaluar(t.guarda, memoria)):
                        entrar(t.destino)
                        break
                anotar(evento)
        except (ErrorReferencia, OverflowError) as e:
            pasos.append((evento, None, str(e)))
        resultado.append((sim.personaje, pasos))
    return resultado
