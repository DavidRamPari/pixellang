"""Prueba de la biblioteca nativa (hito 3).

Compila ejemplos/caballero.pxl, guarda el objeto con emit_object, lo enlaza como
biblioteca nativa (DLL en Windows, .so en Linux) y la carga con ctypes, como la cargará
Unity: la traza que da la biblioteca tiene que ser igual a la de la máquina de TAC. La
biblioteca no necesita Python ni llvmlite para ejecutarse.

Uso: python pruebas/probar_biblioteca.py [carpeta de salida, por defecto build]
"""
import json
import os
import sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(RAIZ, "src"))
from frontend import analizar                                           # noqa: E402
from semantico import AnalizadorSemantico                               # noqa: E402
from ast_pixellang import construir_ast                                 # noqa: E402
from codigo_intermedio import GeneradorTAC                              # noqa: E402
from maquina_tac import trazas                                          # noqa: E402
from codigo_llvm import (GeneradorLLVM, InterfazPixelLang, emitir,      # noqa: E402
                         trazas_llvm, INDICE_INVALIDO)
from biblioteca_nativa import enlazar                                   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

carpeta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "build")
fuente = open(os.path.join(RAIZ, "ejemplos", "caballero.pxl"), encoding="utf-8").read()
arbol, _, errores = analizar(fuente)
sem = AnalizadorSemantico()
sem.analizar(arbol)
assert not errores and not sem.errores
programa = construir_ast(arbol)
codigo = GeneradorTAC(sem.tabla_global).generar(programa)
esperado = trazas(programa, codigo)

generador = GeneradorLLVM(programa)
generador.generar()
prefijo = emitir(generador, os.path.join(carpeta, "pixellang"), esperado)
biblioteca = enlazar(prefijo)
print(f"Biblioteca: {os.path.basename(biblioteca)} ({os.path.getsize(biblioteca)} bytes), "
      f"exporta {', '.join(generador.exportadas)}")

with InterfazPixelLang(biblioteca=biblioteca) as interfaz:
    obtenido = trazas_llvm(programa, interfaz)
    assert obtenido == esperado, (obtenido, esperado)
    f = interfaz.funciones
    assert f["pl_iniciar"](-1) == INDICE_INVALIDO and f["pl_evento"](0, 999) == INDICE_INVALIDO
    assert f["pl_estado"](5) == -1
    # Se puede volver a iniciar al personaje y seguir enviándole eventos (saltar: Saltando)
    assert f["pl_iniciar"](0) == 0 and f["pl_evento"](0, 0) == 0 and f["pl_estado"](0) == 1
pasos = sum(len(p) for _, p in obtenido)
print(f"Traza de la biblioteca: {pasos} pasos, iguales a los de la máquina de TAC")

mapa = json.load(open(f"{prefijo}.json", encoding="utf-8"))
assert [p["nombre"] for p in mapa["personajes"]] == ["Caballero"]
assert len(mapa["simulaciones"][0]["pasos"]) == pasos
print(f"Mapa de la interfaz: {os.path.basename(str(prefijo))}.json con {pasos} pasos esperados")
print("fallos: 0")
