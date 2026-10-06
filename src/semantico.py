"""Análisis semántico de PixelLang.

Como en los laboratorios 4 y 5, un visitor recorre el árbol sintáctico que
genera ANTLR: al visitar una declaración inserta el símbolo en la tabla y al
visitar un uso lo busca. Los errores se acumulan para reportarlos juntos.
"""
from collections import deque
from dataclasses import dataclass

from antlr4 import ParserRuleContext
from antlr4.tree.Tree import TerminalNode

import frontend  # noqa: F401  agrega src/generado al path de Python
from PixelLangVisitor import PixelLangVisitor

ERRORES = {
    "E01": "Transición hacia un estado no declarado",
    "E02": "Evento no declarado",
    "E03": "Transiciones no deterministas",
    "E04": "Estado inicial ausente o repetido",
    "E05": "Estado inalcanzable",
    "E06": "Nombre declarado dos veces o usado para dos cosas",
    "E07": "Atributo no declarado",
    "E08": "Tipos incompatibles",
    "E09": "Estado final con transiciones de salida",
    "E10": "Simulación de un personaje no declarado",
}

NUMERICOS = ("entero", "real")


def tipo_aritmetico(tipos):
    """Si algún operando es real, el resultado es real; si no, es entero."""
    return "real" if "real" in tipos else "entero"


def se_puede_asignar(destino, origen):
    """Un entero se puede asignar a un real, pero un real no a un entero."""
    if "error" in (destino, origen):
        return True
    return destino == origen or (destino == "real" and origen == "entero")


def posicion(nodo):
    """Línea y columna de un token, de una hoja del árbol o de una regla."""
    if isinstance(nodo, TerminalNode):
        nodo = nodo.getSymbol()
    elif isinstance(nodo, ParserRuleContext):
        nodo = nodo.start
    return nodo.line, nodo.column


@dataclass
class Simbolo:
    nombre: str
    categoria: str               # personaje, atributo, evento o estado
    linea: int
    columna: int
    tipo: str = None             # tipo de un atributo
    modificador: str = None      # inicial o final, en un estado
    ambito: "TablaSimbolos" = None   # en un personaje, la tabla de su ámbito


class TablaSimbolos:
    """Tabla de símbolos de un ámbito.

    PixelLang tiene dos niveles de ámbito: el global, con los personajes, y el
    de cada personaje, con sus atributos, eventos y estados. Cada categoría se
    guarda aparte, pero dentro de un ámbito un nombre identifica una sola cosa.
    """

    def __init__(self, nombre, categorias, padre=None):
        self.nombre = nombre
        self.padre = padre
        self.espacios = {c: {} for c in categorias}

    def declarar(self, simbolo):
        """Inserta el símbolo y devuelve el símbolo con el que choca, o None."""
        espacio = self.espacios[simbolo.categoria]
        if simbolo.nombre in espacio:
            return espacio[simbolo.nombre]
        previo = self.buscar_local(simbolo.nombre)
        espacio[simbolo.nombre] = simbolo
        return previo

    def buscar_local(self, nombre, categoria=None):
        categorias = [categoria] if categoria else list(self.espacios)
        for c in categorias:
            if nombre in self.espacios.get(c, {}):
                return self.espacios[c][nombre]
        return None

    def buscar(self, nombre, categoria=None):
        """Busca en este ámbito y, si no lo encuentra, en los ámbitos externos."""
        simbolo = self.buscar_local(nombre, categoria)
        if simbolo is None and self.padre is not None:
            return self.padre.buscar(nombre, categoria)
        return simbolo

    def simbolos(self, categoria=None):
        categorias = [categoria] if categoria else list(self.espacios)
        return [s for c in categorias for s in self.espacios[c].values()]

    def mostrar(self):
        return [(s.nombre, s.categoria, s.tipo or s.modificador or "", s.linea, s.columna)
                for s in self.simbolos()]


class AnalizadorSemantico(PixelLangVisitor):
    def __init__(self):
        self.tabla_global = TablaSimbolos("global", ("personaje",))
        self.tabla = None            # ámbito del personaje que se está visitando
        self.estado = None           # estado cuyas transiciones se visitan
        self.sin_guarda = {}
        self.transiciones = []
        self.inicial = None
        self.errores = []
        self.advertencias = []

    def error(self, pos, codigo, mensaje):
        self.errores.append((*pos, codigo, mensaje))

    def advertir(self, pos, mensaje):
        self.advertencias.append((*pos, mensaje))

    def analizar(self, arbol):
        self.visit(arbol)
        self.errores.sort(key=lambda e: e[0])
        self.advertencias.sort(key=lambda a: a[0])
        return self.errores

    # Declaraciones ---------------------------------------------------------

    def visitPrograma(self, ctx):
        for pj in ctx.personaje():
            self.visit(pj)
        for sim in ctx.simulacion():
            self.visit(sim)

    def visitPersonaje(self, ctx):
        nombre = ctx.ID().getText()
        tabla = TablaSimbolos(nombre, ("atributo", "evento", "estado"), self.tabla_global)
        previo = self.tabla_global.declarar(
            Simbolo(nombre, "personaje", *posicion(ctx.ID()), ambito=tabla))
        if previo:
            self.error(posicion(ctx.ID()), "E06",
                       f"el personaje '{nombre}' ya fue declarado en la línea {previo.linea}")
            return

        self.tabla, self.transiciones, self.inicial = tabla, [], None   # entra al ámbito
        for atr in ctx.atributo():
            self.visit(atr)
        self.visit(ctx.eventos())
        # Primero se registran todos los estados, porque una transición puede
        # ir hacia un estado que se declara más abajo.
        for est in ctx.estado():
            self.declarar_estado(est)
        self.revisar_inicial(ctx)
        for est in ctx.estado():
            self.visit(est)
        self.revisar_alcanzables()
        self.tabla = None                                               # sale del ámbito

    def declarar(self, simbolo):
        previo = self.tabla.declarar(simbolo)
        if previo is None:
            return
        if previo.categoria == simbolo.categoria:
            mensaje = (f"el {simbolo.categoria} '{simbolo.nombre}' ya fue declarado "
                       f"en la línea {previo.linea}")
        else:
            mensaje = (f"'{simbolo.nombre}' ya es el nombre de un {previo.categoria} "
                       f"(línea {previo.linea}); un nombre no puede usarse para dos "
                       f"cosas distintas")
        self.error((simbolo.linea, simbolo.columna), "E06", mensaje)

    def visitAtributo(self, ctx):
        nombre = ctx.ID().getText()
        tipo = "logico" if ctx.tipo().LOGICO() else ctx.tipo().getText()
        tipo_valor = self.visit(ctx.expr())
        if not se_puede_asignar(tipo, tipo_valor):
            self.error(posicion(ctx), "E08",
                       f"el atributo '{nombre}' es {tipo} y se inicializa con un valor {tipo_valor}")
        self.declarar(Simbolo(nombre, "atributo", *posicion(ctx.ID()), tipo=tipo))

    def visitEventos(self, ctx):
        for ev in ctx.ID():
            self.declarar(Simbolo(ev.getText(), "evento", *posicion(ev)))

    def declarar_estado(self, ctx):
        modificador = ctx.modificador().getText() if ctx.modificador() else None
        self.declarar(Simbolo(ctx.ID().getText(), "estado", *posicion(ctx.ID()),
                              modificador=modificador))

    def revisar_inicial(self, ctx):
        iniciales = [s for s in self.tabla.simbolos("estado") if s.modificador == "inicial"]
        if not iniciales:
            self.error(posicion(ctx.ID()), "E04",
                       f"el personaje '{self.tabla.nombre}' no tiene estado inicial")
        elif len(iniciales) > 1:
            lista = ", ".join(f"'{s.nombre}'" for s in iniciales)
            self.error((iniciales[1].linea, iniciales[1].columna), "E04",
                       f"el personaje '{self.tabla.nombre}' tiene más de un estado inicial: {lista}")
        else:
            self.inicial = iniciales[0].nombre

    # Estados, transiciones y acciones --------------------------------------

    def visitEstado(self, ctx):
        self.estado = ctx.ID().getText()
        self.sin_guarda = {}
        if ctx.alEntrar():
            self.visit(ctx.alEntrar())
        for tr in ctx.transicion():
            self.visit(tr)
        modificador = ctx.modificador().getText() if ctx.modificador() else None
        if modificador == "final" and ctx.transicion():
            self.error(posicion(ctx.ID()), "E09",
                       f"'{self.estado}' es un estado final y no puede tener transiciones")
        if modificador != "final" and not ctx.transicion():
            self.advertir(posicion(ctx.ID()),
                          f"'{self.estado}' no tiene transiciones de salida y no es final: "
                          f"el personaje quedaría atrapado ahí")

    def visitTransicion(self, ctx):
        evento, destino = ctx.ID(0).getText(), ctx.ID(1).getText()
        linea = ctx.start.line
        if self.tabla.buscar(evento, "evento") is None:
            self.error(posicion(ctx.ID(0)), "E02",
                       f"el evento '{evento}' no está declarado en '{self.tabla.nombre}'")
        if self.tabla.buscar(destino, "estado") is None:
            self.error(posicion(ctx.ID(1)), "E01",
                       f"la transición de '{self.estado}' con '{evento}' va hacia "
                       f"'{destino}', que no es un estado declarado")
        if ctx.guarda():
            t = self.visit(ctx.guarda().expr())
            if t not in ("logico", "error"):
                self.error(posicion(ctx.guarda().expr()), "E08",
                           f"la guarda de la transición debe ser logico, no {t}")
        if evento in self.sin_guarda:
            self.error(posicion(ctx), "E03",
                       f"en '{self.estado}', la transición con '{evento}' de la línea "
                       f"{linea} nunca se toma: la de la línea {self.sin_guarda[evento]} "
                       f"responde al mismo evento sin guarda")
        elif not ctx.guarda():
            self.sin_guarda[evento] = linea
        self.transiciones.append((self.estado, destino))

    def revisar_alcanzables(self):
        if self.inicial is None:
            return
        vecinos = {}
        for origen, destino in self.transiciones:
            vecinos.setdefault(origen, []).append(destino)
        visitados = {self.inicial}
        cola = deque([self.inicial])
        while cola:
            q = cola.popleft()
            for r in vecinos.get(q, []):
                if self.tabla.buscar_local(r, "estado") and r not in visitados:
                    visitados.add(r)
                    cola.append(r)
        for s in self.tabla.simbolos("estado"):
            if s.nombre not in visitados:
                self.error((s.linea, s.columna), "E05",
                           f"el estado '{s.nombre}' no es alcanzable desde '{self.inicial}'")

    def visitAsignacion(self, ctx):
        nombre = ctx.ID().getText()
        tipo_valor = self.visit(ctx.expr())
        simbolo = self.tabla.buscar(nombre, "atributo")
        if simbolo is None:
            self.error(posicion(ctx.ID()), "E07",
                       f"'{nombre}' no es un atributo de '{self.tabla.nombre}'")
            return
        if not se_puede_asignar(simbolo.tipo, tipo_valor):
            self.error(posicion(ctx), "E08",
                       f"no se puede asignar un valor {tipo_valor} al atributo "
                       f"'{nombre}', que es {simbolo.tipo}")

    def visitSeleccion(self, ctx):
        t = self.visit(ctx.expr())
        if t not in ("logico", "error"):
            self.error(posicion(ctx.expr()), "E08",
                       f"la condición de 'si' debe ser logico, no {t}")
        for b in ctx.bloque():
            self.visit(b)

    def visitSimulacion(self, ctx):
        nombre = ctx.ID(0).getText()
        personaje = self.tabla_global.buscar(nombre, "personaje")
        if personaje is None:
            self.error(posicion(ctx.ID(0)), "E10", f"no existe un personaje llamado '{nombre}'")
            return
        for ev in ctx.ID()[1:]:
            if personaje.ambito.buscar(ev.getText(), "evento") is None:
                self.error(posicion(ev), "E02",
                           f"el evento '{ev.getText()}' no está declarado en '{nombre}'")

    # Expresiones: cada visita devuelve el tipo de la subexpresión -------------

    def visitExpr(self, ctx):
        tipos = [self.visit(c) for c in ctx.conj()]
        return tipos[0] if len(tipos) == 1 else self.logico(ctx, "||", tipos)

    def visitConj(self, ctx):
        tipos = [self.visit(r) for r in ctx.rel()]
        return tipos[0] if len(tipos) == 1 else self.logico(ctx, "&&", tipos)

    def logico(self, ctx, op, tipos):
        if "error" in tipos:
            return "logico"
        for t in tipos:
            if t != "logico":
                self.error(posicion(ctx), "E08",
                           f"el operador '{op}' necesita valores logico y recibió {t}")
                break
        return "logico"

    def visitRel(self, ctx):
        tipos = [self.visit(a) for a in ctx.arit()]
        if len(tipos) == 1:
            return tipos[0]
        op = ctx.opRel().getText()
        a, b = tipos
        if "error" in tipos:
            return "logico"
        if op in ("==", "!="):
            valido = (a in NUMERICOS and b in NUMERICOS) or a == b
        else:
            valido = a in NUMERICOS and b in NUMERICOS
        if not valido:
            self.error(posicion(ctx), "E08", f"no se puede comparar {a} con {b} usando '{op}'")
        return "logico"

    def visitArit(self, ctx):
        return self.aritmetica(ctx, ctx.term())

    def visitTerm(self, ctx):
        return self.aritmetica(ctx, ctx.unario())

    def aritmetica(self, ctx, operandos):
        tipos = [self.visit(o) for o in operandos]
        if len(tipos) == 1:
            return tipos[0]
        if "error" in tipos:
            return "error"
        operadores = [c.getText() for c in ctx.getChildren() if isinstance(c, TerminalNode)]
        malos = [t for t in tipos if t not in NUMERICOS]
        if malos:
            self.error(posicion(ctx), "E08",
                       f"el operador '{operadores[0]}' necesita números y recibió {malos[0]}")
            return "error"
        return tipo_aritmetico(tipos)

    def visitUnario(self, ctx):
        if ctx.factor():
            return self.visit(ctx.factor())
        t = self.visit(ctx.unario())
        op = ctx.getChild(0).getText()
        if t == "error":
            return t
        if op == "!" and t != "logico":
            self.error(posicion(ctx), "E08", f"'!' necesita un valor logico, no {t}")
            return "error"
        if op == "-" and t not in NUMERICOS:
            self.error(posicion(ctx), "E08", f"'-' necesita un número, no {t}")
            return "error"
        return t

    def visitFactor(self, ctx):
        if ctx.expr():
            return self.visit(ctx.expr())
        if ctx.NUM_ENTERO():
            return "entero"
        if ctx.NUM_REAL():
            return "real"
        if ctx.VERDADERO() or ctx.FALSO():
            return "logico"
        nombre = ctx.ID().getText()
        simbolo = self.tabla.buscar(nombre, "atributo")
        if simbolo is None:
            self.error(posicion(ctx.ID()), "E07",
                       f"'{nombre}' no es un atributo de '{self.tabla.nombre}'")
            return "error"
        return simbolo.tipo
