import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "src"))
sys.path.insert(0, os.path.join(AQUI, "..", "pruebas"))
from lark import Lark, Tree, Token
from bnf import PRODUCCIONES, TERMINALES, TOKEN_A_TERMINAL, NO_TERMINALES, DUENO
from frontend import tokens as lexear

def lark_grammar():
    lit = {t: f'T{i}' for i, t in enumerate(TERMINALES)}
    lineas = []
    for cab, alts in PRODUCCIONES.items():
        cuerpos = []
        for a in alts:
            cuerpos.append(" ".join(s if s in NO_TERMINALES else lit[s] for s in a) if a else "")
        lineas.append(f"{cab}: " + "\n    | ".join(cuerpos))
    for t, nombre in lit.items():
        lineas.append(f'{nombre}: "{t}"')
    lineas.append("%ignore \" \"")
    return "\n".join(lineas), {v: k for k, v in lit.items()}

GRAM, NOMBRE_A_TERM = lark_grammar()
PARSER = Lark(GRAM, start=list(PRODUCCIONES), parser="earley", lexer="basic",
              ambiguity="explicit", keep_all_tokens=True, maybe_placeholders=False)

def cadena_tokens(fuente):
    lista, errores = lexear(fuente)
    assert not errores, errores
    return [TOKEN_A_TERMINAL.get(n, lex) for n, lex, _ in lista]

def tiene_ambiguedad(t):
    if isinstance(t, Tree):
        return t.data == "_ambig" or any(tiene_ambiguedad(c) for c in t.children)
    return False

def derivacion(fuente, inicio):
    toks = cadena_tokens(fuente)
    arbol = PARSER.parse(" ".join(toks), start=inicio)
    assert not tiene_ambiguedad(arbol), "ambigua"
    forma = [arbol]
    pasos = []
    while True:
        idx = next((i for i, x in enumerate(forma) if isinstance(x, Tree)), None)
        simbolos = [("N", x.data) if isinstance(x, Tree) else ("T", NOMBRE_A_TERM[x.type])
                    for x in forma]
        if idx is None:
            pasos.append((simbolos, None))
            break
        nodo = forma[idx]
        cuerpo = [("N", c.data) if isinstance(c, Tree) else ("T", NOMBRE_A_TERM[c.type])
                  for c in nodo.children]
        pasos.append((simbolos, (nodo.data, cuerpo)))
        forma = forma[:idx] + list(nodo.children) + forma[idx + 1:]
    assert [s for _, s in pasos[-1][0]] == toks
    for _, prod in pasos[:-1]:
        cab, cuerpo = prod
        assert [s for _, s in cuerpo] in PRODUCCIONES[cab], prod
    return toks, pasos

def hojas(nodo):
    if isinstance(nodo, Tree):
        return [h for c in nodo.children for h in hojas(c)]
    return [("T", NOMBRE_A_TERM[nodo.type])]


def derivacion_resumida(fuente, inicio, clave):
    toks = cadena_tokens(fuente)
    arbol = PARSER.parse(" ".join(toks), start=inicio)
    assert not tiene_ambiguedad(arbol), "ambigua"
    forma = [arbol]
    pasos = []
    simb = lambda x: ("N", x.data) if isinstance(x, Tree) else ("T", NOMBRE_A_TERM[x.type])
    while True:
        idx = next((i for i, x in enumerate(forma) if isinstance(x, Tree)), None)
        actual = [simb(x) for x in forma]
        if idx is None:
            pasos.append((actual, None))
            break
        nodo = forma[idx]
        if DUENO[nodo.data] != clave:
            cadena = hojas(nodo)
            pasos.append((actual, ("*", nodo.data, cadena)))
            forma = forma[:idx] + list(_tokens_de(nodo)) + forma[idx + 1:]
        else:
            cuerpo = [simb(c) for c in nodo.children]
            pasos.append((actual, ("=", nodo.data, cuerpo)))
            forma = forma[:idx] + list(nodo.children) + forma[idx + 1:]
    assert [s for _, s in pasos[-1][0]] == toks
    return toks, pasos


def _tokens_de(nodo):
    if isinstance(nodo, Tree):
        for c in nodo.children:
            yield from _tokens_de(c)
    else:
        yield nodo


if __name__ == "__main__":
    from construcciones import CONSTRUCCIONES
    from frontend import analizar
    total = 0
    for clave, nombre, regla, inicio, ejemplos, elegidos in CONSTRUCCIONES:
        for i, ej in enumerate(ejemplos):
            toks, pasos = derivacion(ej, inicio)
            marca = "*" if i in elegidos else " "
            print(f"{marca} {clave}.{i+1} pasos={len(pasos)-1:3d}  {' '.join(toks)[:90]}")
            total += 1
    print("ejemplos validados con la GLC:", total)
