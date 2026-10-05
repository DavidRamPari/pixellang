import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "generado"))

from antlr4 import InputStream, CommonTokenStream, Token, Lexer
from antlr4.error.ErrorListener import ErrorListener
from PixelLangLexer import PixelLangLexer
from PixelLangParser import PixelLangParser


class RecolectorErrores(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errores = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        tipo = "léxico" if isinstance(recognizer, Lexer) else "sintáctico"
        self.errores.append((tipo, line, column, msg))


def tokens(texto):
    lexer = PixelLangLexer(InputStream(texto))
    errores = RecolectorErrores()
    lexer.removeErrorListeners()
    lexer.addErrorListener(errores)
    flujo = CommonTokenStream(lexer)
    flujo.fill()
    salida = []
    for t in flujo.tokens:
        if t.type == Token.EOF:
            continue
        salida.append((PixelLangLexer.symbolicNames[t.type], t.text, t.line))
    return salida, errores.errores


def analizar(texto, regla="programa"):
    lexer = PixelLangLexer(InputStream(texto))
    errores = RecolectorErrores()
    lexer.removeErrorListeners()
    lexer.addErrorListener(errores)
    flujo = CommonTokenStream(lexer)
    parser = PixelLangParser(flujo)
    parser.removeErrorListeners()
    parser.addErrorListener(errores)
    arbol = getattr(parser, regla)()
    if regla != "programa" and flujo.LT(1).type != Token.EOF:
        t = flujo.LT(1)
        errores.errores.append(("sintáctico", t.line, t.column,
                                f"sobra entrada a partir de '{t.text}'"))
    return arbol, parser, errores.errores


def arbol_indentado(arbol, parser):
    from antlr4.tree.Tree import TerminalNode

    def etiqueta(nodo):
        if isinstance(nodo, TerminalNode):
            tipo = nodo.getSymbol().type
            nombre = "EOF" if tipo == Token.EOF else PixelLangLexer.symbolicNames[tipo]
            return nombre if tipo == Token.EOF else f'{nombre} → "{nodo.getText()}"'
        return parser.ruleNames[nodo.getRuleIndex()]

    def hijos(nodo):
        return [] if isinstance(nodo, TerminalNode) else list(nodo.getChildren())

    lineas = [etiqueta(arbol)]

    def recorrer(nodo, prefijo):
        hs = hijos(nodo)
        for i, h in enumerate(hs):
            ultimo = i == len(hs) - 1
            lineas.append(prefijo + ("└── " if ultimo else "├── ") + etiqueta(h))
            recorrer(h, prefijo + ("    " if ultimo else "│   "))

    recorrer(arbol, "")
    return lineas


def formatear(encabezado, mensaje, ancho=78):
    import textwrap
    return [encabezado] + textwrap.wrap(mensaje, ancho, initial_indent="  ",
                                        subsequent_indent="  ")
