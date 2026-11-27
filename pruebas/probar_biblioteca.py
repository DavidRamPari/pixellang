"""Prueba de la biblioteca nativa (hito 3).

Compila ejemplos/caballero.pxl, guarda el objeto con emit_object, lo enlaza como
biblioteca nativa (DLL en Windows, .so en Linux) y la carga con ctypes, como la cargará
Unity: la traza que da la biblioteca tiene que ser igual a la de la máquina de TAC. La
biblioteca no necesita Python ni llvmlite para ejecutarse. Después hace lo mismo con
ejemplos/juego.pxl, el programa del minijuego de Unity, que tiene dos personajes.

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
                         trazas_llvm, INDICE_INVALIDO, INSTANCIAS)
from biblioteca_nativa import enlazar                                   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

carpeta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "build")


def compilar(nombre):
    """AST, TAC con sus trazas y LLVM de un programa de la carpeta ejemplos."""
    arbol, _, errores = analizar(open(os.path.join(RAIZ, "ejemplos", nombre), encoding="utf-8").read())
    sem = AnalizadorSemantico()
    sem.analizar(arbol)
    assert not errores and not sem.errores
    programa = construir_ast(arbol)
    trazas_tac = trazas(programa, GeneradorTAC(sem.tabla_global).generar(programa))
    generador = GeneradorLLVM(programa)
    generador.generar()
    return programa, trazas_tac, generador


programa, esperado, generador = compilar("caballero.pxl")
prefijo = emitir(generador, os.path.join(carpeta, "pixellang"), esperado)
biblioteca = enlazar(prefijo)
print(f"Biblioteca: {os.path.basename(biblioteca)} ({os.path.getsize(biblioteca)} bytes), "
      f"exporta {', '.join(generador.exportadas)}")

with InterfazPixelLang(biblioteca=biblioteca) as interfaz:
    obtenido = trazas_llvm(programa, interfaz)
    assert obtenido == esperado, (obtenido, esperado)
    f = interfaz.funciones
    assert f["pl_iniciar"](-1) == INDICE_INVALIDO and f["pl_evento"](0, 999) == INDICE_INVALIDO
    assert f["pl_estado"](INSTANCIAS) == -1
    # Se puede volver a iniciar al personaje y seguir enviándole eventos (saltar: Saltando)
    assert f["pl_iniciar"](0) == 0 and f["pl_evento"](0, 0) == 0 and f["pl_estado"](0) == 1
pasos = sum(len(p) for _, p in obtenido)
print(f"Traza de la biblioteca: {pasos} pasos, iguales a los de la máquina de TAC")

mapa = json.load(open(f"{prefijo}.json", encoding="utf-8"))
assert [p["nombre"] for p in mapa["personajes"]] == ["Caballero"]
assert len(mapa["simulaciones"][0]["pasos"]) == pasos
print(f"Mapa de la interfaz: {os.path.basename(str(prefijo))}.json con {pasos} pasos esperados")


# Dos personajes en una biblioteca: cada uno tiene su propio estado y sus atributos, y se
# elige con el primer parámetro de la interfaz (0 el caballero, 1 el slime)
programa, esperado, generador = compilar("juego.pxl")
prefijo = emitir(generador, os.path.join(carpeta, "juego"), esperado)
biblioteca = enlazar(prefijo)
with InterfazPixelLang(biblioteca=biblioteca) as interfaz:
    obtenido = trazas_llvm(programa, interfaz)
    assert obtenido == esperado, (obtenido, esperado)
    f = interfaz.funciones
    assert f["pl_iniciar"](0) == 0 and f["pl_iniciar"](1) == 0
    assert f["pl_evento"](1, 0) == 0                      # ver_jugador solo cambia al slime
    assert f["pl_estado"](1) == 1 and f["pl_estado"](0) == 0
    # Un segundo slime (instancia 1 + 2·1 = 3) tiene su propia ficha
    assert f["pl_iniciar"](3) == 0 and f["pl_evento"](3, 2) == 0      # recibir_golpe
    assert (f["pl_entero"](3, 0), f["pl_entero"](1, 0)) == (20, 30)
    assert f["pl_estado"](3) == 2 and f["pl_estado"](1) == 1
    assert f["pl_iniciar"](2 * INSTANCIAS) == INDICE_INVALIDO
mapa = json.load(open(f"{prefijo}.json", encoding="utf-8"))
caballero, slime = mapa["personajes"]
assert (caballero["nombre"], slime["nombre"]) == ("Caballero", "Slime")
assert (caballero["inicial"], slime["inicial"]) == ("Reposo", "Patrulla")
assert len(caballero["transiciones"]) == 10 and len(slime["transiciones"]) == 7
assert {"origen": "Aturdido", "evento": "fin_aturdimiento", "guarda": "vida <= 0",
        "destino": "Aplastado"} in slime["transiciones"]
pasos = [len(p) for _, p in obtenido]
print(f"Dos personajes (juego.pxl): {pasos[0]} y {pasos[1]} pasos iguales a los de la máquina "
      f"de TAC; el mapa trae δ con {len(caballero['transiciones'])} y "
      f"{len(slime['transiciones'])} transiciones")
assert mapa["instancias_por_personaje"] == INSTANCIAS
print(f"Instancias: {INSTANCIAS} por personaje; dos slimes, cada uno con su ficha")
print("fallos: 0")
