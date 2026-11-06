"""Árbol de sintaxis abstracta (AST) de PixelLang.

Como en el laboratorio 6, los nodos son clases propias, no las que genera ANTLR,
y un visitor recorre el árbol sintáctico para construirlos. El AST conserva lo
que necesita la generación de código: personajes, atributos, estados,
transiciones, acciones y expresiones. Los paréntesis, las llaves y los puntos y
coma desaparecen; la precedencia queda en la forma del árbol.

El AST se construye después del análisis semántico, cuando el programa ya no
tiene errores, por eso los nodos no guardan la línea ni la columna.
"""
from dataclasses import dataclass

import frontend  # noqa: F401  agrega src/generado al path de Python
from PixelLangVisitor import PixelLangVisitor


@dataclass(frozen=True)
class Programa: personajes: tuple; simulaciones: tuple
@dataclass(frozen=True)
class Personaje: nombre: str; atributos: tuple; eventos: tuple; estados: tuple
@dataclass(frozen=True)
class Atributo: nombre: str; tipo: str; valor: object
@dataclass(frozen=True)
class Estado: nombre: str; modificador: object; al_entrar: object; transiciones: tuple
@dataclass(frozen=True)
class Transicion: evento: str; guarda: object; destino: str
@dataclass(frozen=True)
class Simulacion: personaje: str; eventos: tuple
@dataclass(frozen=True)
class Bloque: sentencias: tuple
@dataclass(frozen=True)
class Asignacion: nombre: str; expresion: object
@dataclass(frozen=True)
class Seleccion: condicion: object; entonces: object; sino: object
@dataclass(frozen=True)
class Numero: valor: object
@dataclass(frozen=True)
class Logico: valor: bool
@dataclass(frozen=True)
class Variable: nombre: str
@dataclass(frozen=True)
class Unaria: op: str; operando: object
@dataclass(frozen=True)
class Binaria: op: str; izquierda: object; derecha: object


class ConstructorAST(PixelLangVisitor):
    def visitPrograma(self, ctx):
        return Programa(tuple(self.visit(p) for p in ctx.personaje()),
                        tuple(self.visit(s) for s in ctx.simulacion()))

    def visitPersonaje(self, ctx):
        return Personaje(ctx.ID().getText(),
                         tuple(self.visit(a) for a in ctx.atributo()),
                         tuple(ev.getText() for ev in ctx.eventos().ID()),
                         tuple(self.visit(e) for e in ctx.estado()))

    def visitAtributo(self, ctx):
        tipo = "logico" if ctx.tipo().LOGICO() else ctx.tipo().getText()
        return Atributo(ctx.ID().getText(), tipo, self.visit(ctx.expr()))

    def visitEstado(self, ctx):
        modificador = ctx.modificador().getText() if ctx.modificador() else None
        al_entrar = self.visit(ctx.alEntrar().bloque()) if ctx.alEntrar() else None
        return Estado(ctx.ID().getText(), modificador, al_entrar,
                      tuple(self.visit(t) for t in ctx.transicion()))

    def visitTransicion(self, ctx):
        guarda = self.visit(ctx.guarda().expr()) if ctx.guarda() else None
        return Transicion(ctx.ID(0).getText(), guarda, ctx.ID(1).getText())

    def visitSimulacion(self, ctx):
        return Simulacion(ctx.ID(0).getText(), tuple(ev.getText() for ev in ctx.ID()[1:]))

    def visitBloque(self, ctx):
        return Bloque(tuple(self.visit(s) for s in ctx.sentencia()))

    def visitAsignacion(self, ctx):
        return Asignacion(ctx.ID().getText(), self.visit(ctx.expr()))

    def visitSeleccion(self, ctx):
        sino = self.visit(ctx.bloque(1)) if ctx.SINO() else None
        return Seleccion(self.visit(ctx.expr()), self.visit(ctx.bloque(0)), sino)

    # Expresiones -----------------------------------------------------------

    def binarias(self, ctx, operandos):
        izquierda = self.visit(operandos[0])
        # Procesar los operadores de izquierda a derecha, como visitExpr y
        # visitTerm del laboratorio 6
        for i in range(1, len(operandos)):
            op = ctx.getChild(2 * i - 1).getText()
            derecha = self.visit(operandos[i])
            izquierda = Binaria(op, izquierda, derecha)
        return izquierda

    def visitExpr(self, ctx):
        return self.binarias(ctx, ctx.conj())

    def visitConj(self, ctx):
        return self.binarias(ctx, ctx.rel())

    def visitRel(self, ctx):
        return self.binarias(ctx, ctx.arit())

    def visitArit(self, ctx):
        return self.binarias(ctx, ctx.term())

    def visitTerm(self, ctx):
        return self.binarias(ctx, ctx.unario())

    def visitNegacion(self, ctx):
        return Unaria("!", self.visit(ctx.unario()))

    def visitNegativo(self, ctx):
        return Unaria("-", self.visit(ctx.unario()))

    def visitPrimario(self, ctx):
        return self.visit(ctx.factor())

    def visitParentesis(self, ctx):
        return self.visit(ctx.expr())

    def visitNumEntero(self, ctx):
        return Numero(int(ctx.NUM_ENTERO().getText()))

    def visitNumReal(self, ctx):
        return Numero(float(ctx.NUM_REAL().getText()))

    def visitValorLogico(self, ctx):
        return Logico(ctx.VERDADERO() is not None)

    def visitVariable(self, ctx):
        return Variable(ctx.ID().getText())


def construir_ast(arbol):
    return ConstructorAST().visit(arbol)


# Listado del AST con ├── y └──, como el de la opción --arbol ------------------

def etiqueta(nodo):
    if isinstance(nodo, str): return nodo
    if isinstance(nodo, Programa): return "Programa"
    if isinstance(nodo, Personaje): return f'Personaje("{nodo.nombre}")'
    if isinstance(nodo, Atributo): return f'Atributo("{nodo.nombre}", {nodo.tipo})'
    if isinstance(nodo, Estado):
        return f'Estado("{nodo.nombre}"' + (f", {nodo.modificador})" if nodo.modificador else ")")
    if isinstance(nodo, Transicion): return f'Transicion("{nodo.evento}" -> "{nodo.destino}")'
    if isinstance(nodo, Simulacion): return f'Simulacion("{nodo.personaje}")'
    if isinstance(nodo, Bloque): return "Bloque"
    if isinstance(nodo, Asignacion): return f'Asignacion("{nodo.nombre}")'
    if isinstance(nodo, Seleccion): return "Seleccion"
    if isinstance(nodo, Numero): return f"Numero({nodo.valor})"
    if isinstance(nodo, Logico): return "Logico(verdadero)" if nodo.valor else "Logico(falso)"
    if isinstance(nodo, Variable): return f'Variable("{nodo.nombre}")'
    if isinstance(nodo, Unaria): return f'Unaria("{nodo.op}")'
    if isinstance(nodo, Binaria): return f'Binaria("{nodo.op}")'
    raise TypeError(f"Nodo no soportado: {type(nodo).__name__}")


def hijos(nodo):
    if isinstance(nodo, Programa): return list(nodo.personajes) + list(nodo.simulaciones)
    if isinstance(nodo, Personaje):
        eventos = "Eventos(" + ", ".join(nodo.eventos) + ")"
        return list(nodo.atributos) + [eventos] + list(nodo.estados)
    if isinstance(nodo, Atributo): return [nodo.valor]
    if isinstance(nodo, Estado):
        return ([nodo.al_entrar] if nodo.al_entrar else []) + list(nodo.transiciones)
    if isinstance(nodo, Transicion): return [nodo.guarda] if nodo.guarda else []
    if isinstance(nodo, Simulacion): return ["Eventos(" + ", ".join(nodo.eventos) + ")"]
    if isinstance(nodo, Bloque): return list(nodo.sentencias)
    if isinstance(nodo, Asignacion): return [nodo.expresion]
    if isinstance(nodo, Seleccion):
        return [nodo.condicion, nodo.entonces] + ([nodo.sino] if nodo.sino else [])
    if isinstance(nodo, Unaria): return [nodo.operando]
    if isinstance(nodo, Binaria): return [nodo.izquierda, nodo.derecha]
    return []


def ast_indentado(nodo):
    lineas = [etiqueta(nodo)]

    def recorrer(n, prefijo):
        hs = hijos(n)
        for i, h in enumerate(hs):
            ultimo = i == len(hs) - 1
            lineas.append(prefijo + ("└── " if ultimo else "├── ") + etiqueta(h))
            recorrer(h, prefijo + ("    " if ultimo else "│   "))

    recorrer(nodo, "")
    return lineas
