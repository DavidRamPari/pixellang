"""Prueba diferencial del código intermedio.

Genera programas válidos al azar y, para cada uno, comprueba que:
1. pase el análisis léxico, sintáctico y semántico sin errores;
2. el TAC esté bien formado (verificar_tac: temporales definidos antes de usarse,
   saltos y llamadas a etiquetas que existen, procedimientos que terminan en return);
3. la traza de cada simulación ejecutada sobre el TAC sea igual a la del
   intérprete de referencia, que recorre el AST sin pasar por el TAC.

Uso: python pruebas/probar_generados.py [cantidad] [semilla]
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from frontend import analizar                               # noqa: E402
from semantico import AnalizadorSemantico                   # noqa: E402
from ast_pixellang import construir_ast                     # noqa: E402
from codigo_intermedio import GeneradorTAC, verificar_tac   # noqa: E402
from maquina_tac import trazas                              # noqa: E402
from generador import generar_programa                      # noqa: E402
from referencia import simular_referencia                   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def comparable(resultado):
    """Las dos implementaciones redactan distinto el mensaje de error; se compara
    solo en qué paso ocurre."""
    return [(p, [(ev, est, val if est is not None else "error") for ev, est, val in pasos])
            for p, pasos in resultado]


cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else 500
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 2026)
fallos, simulaciones, pasos, con_error = 0, 0, 0, 0
for n in range(1, cantidad + 1):
    fuente = generar_programa(rng)
    arbol, _, errores = analizar(fuente)
    sem = AnalizadorSemantico()
    if not errores:
        sem.analizar(arbol)
    problema = None
    if errores or sem.errores:
        problema = f"el programa no pasa el análisis: {(errores or sem.errores)[0]}"
    else:
        programa = construir_ast(arbol)
        generador = GeneradorTAC(sem.tabla_global)
        codigo = generador.generar(programa)
        mal_formado = verificar_tac(codigo, generador.temporales)
        if mal_formado:
            problema = f"TAC mal formado: {mal_formado[0]}"
        else:
            tac, ref = trazas(programa, codigo), simular_referencia(programa)
            if comparable(tac) != comparable(ref):
                problema = "la traza del TAC no coincide con la del intérprete de referencia"
            simulaciones += len(tac)
            pasos += sum(len(p) for _, p in tac)
            con_error += sum(1 for _, p in tac if p and p[-1][1] is None)
    if problema:
        fallos += 1
        print(f"Programa {n}: {problema}")
        print(fuente)

print(f"{cantidad} programas generados, {simulaciones} simulaciones y {pasos} eventos "
      f"comparados ({con_error} simulaciones terminan en un error de ejecución)")
print("fallos:", fallos)
