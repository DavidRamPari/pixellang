import glob
import os
import random
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "src"))
from bnf import PRODUCCIONES, NO_TERMINALES
from derivar import PARSER, cadena_tokens
from frontend import analizar, tokens as lexear
from lark.exceptions import LarkError

LEXEMA = {"id": "x", "num": "7", "dec": "1.5"}
REGLA_ANTLR = {"programa": "programa", "decl_atr": "atributo", "decl_evs": "eventos",
               "decl_est": "estado", "transicion": "transicion",
               "sentencia": "sentencia", "expr": "expr"}

INF = float("inf")
ALTURA = {n: INF for n in NO_TERMINALES}
cambio = True
while cambio:
    cambio = False
    for cab, alts in PRODUCCIONES.items():
        for a in alts:
            h = 1 + max([ALTURA.get(s, 0) if s in NO_TERMINALES else 0 for s in a] or [0])
            if h < ALTURA[cab]:
                ALTURA[cab] = h
                cambio = True

def altura_alt(a):
    return max([ALTURA[s] if s in NO_TERMINALES else 0 for s in a] or [0])

def generar(simbolo, prof):
    if simbolo not in NO_TERMINALES:
        return [simbolo]
    alts = PRODUCCIONES[simbolo]
    if prof > 7:
        alts = sorted(alts, key=altura_alt)[:1]
    out = []
    for s in random.choice(alts):
        out += generar(s, prof + 1)
    return out

random.seed(7)
fallos = 0
n = 0
for inicio, regla in REGLA_ANTLR.items():
    for _ in range(150):
        toks = generar(inicio, 0)
        fuente = " ".join(LEXEMA.get(t, t) for t in toks)
        _, _, errores = analizar(fuente, regla)
        n += 1
        if errores:
            fallos += 1
            print("ANTLR rechaza lo que la GLC genera:", fuente[:100], errores[:1])
print(f"positivas: {n} cadenas generadas por la GLC, rechazadas por ANTLR: {fallos}")

for ruta in sorted(glob.glob(os.path.join(AQUI, "..", "pruebas", "sintactico", "*.pxl"))):
    fuente = open(ruta, encoding="utf-8").read()
    _, _, err_antlr = analizar(fuente)
    try:
        PARSER.parse(" ".join(cadena_tokens(fuente)), start="programa")
        glc = "acepta"
    except LarkError:
        glc = "rechaza"
    print(f"{ruta.split('/')[-1]:<36} ANTLR {'rechaza' if err_antlr else 'acepta'}  GLC {glc}")
