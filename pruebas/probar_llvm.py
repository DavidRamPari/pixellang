"""Pruebas de la generación de código con LLVM (hito 3).

Cada programa se compila a LLVM IR, se verifica con verify() y se ejecuta con JIT. Se
revisa la forma del código (los bloques de la semana 11 y del laboratorio 8) y que la
ejecución dé la misma traza que la máquina de TAC del hito 2, también en los casos
límite de los enteros de 32 bits y de la división.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from frontend import analizar                                       # noqa: E402
from semantico import AnalizadorSemantico                           # noqa: E402
from ast_pixellang import construir_ast                             # noqa: E402
from codigo_intermedio import GeneradorTAC, verificar_tac           # noqa: E402
from maquina_tac import trazas                                      # noqa: E402
from codigo_llvm import (GeneradorLLVM, InterfazPixelLang, ir,      # noqa: E402
                         simular_llvm, trazas_llvm, INDICE_INVALIDO, INSTANCIAS)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def compilar(fuente):
    arbol, _, errores = analizar(fuente)
    assert not errores, errores
    sem = AnalizadorSemantico()
    sem.analizar(arbol)
    assert not sem.errores, sem.errores
    programa = construir_ast(arbol)
    generador_tac = GeneradorTAC(sem.tabla_global)
    codigo = generador_tac.generar(programa)
    assert verificar_tac(codigo, generador_tac.temporales) == []
    generador = GeneradorLLVM(programa)
    generador.generar()                 # incluye verify()
    return programa, codigo, generador


def comparable(resultado):
    """Igual que en la prueba diferencial: los mensajes de error se redactan distinto en
    cada implementación, así que solo se compara el paso donde ocurren."""
    return [(p, [(ev, est, ["nan" if isinstance(v, float) and math.isnan(v) else v for v in val]
                  if est is not None else "error") for ev, est, val in pasos])
            for p, pasos in resultado]


def ejecutar(fuente):
    """Traza con JIT, comprobada contra la de la máquina de TAC."""
    programa, codigo, generador = compilar(fuente)
    with InterfazPixelLang(generador) as interfaz:
        nativa = trazas_llvm(programa, interfaz)
    assert comparable(nativa) == comparable(trazas(programa, codigo)), (nativa, fuente)
    return nativa


def bloques(generador, procedimiento):
    return [b.name for b in generador.funciones[procedimiento].blocks]


def personaje(atributos, estados="inicial estado S { cuando e -> S; }"):
    return f"personaje P {{ {atributos} eventos e; {estados} }} simular P: e;"


def valores_iniciales(atributos):
    """Valores de los atributos después de iniciar (o el error, si lo hubo)."""
    _, pasos = ejecutar(personaje(atributos))[0]
    evento, estado, valores = pasos[0]
    return valores


# 1. Expresiones: el mismo ejemplo del laboratorio 6, en i64 con comprobación de rango
programa, _, generador = compilar(personaje(
    "a: entero = 1; b: entero = 2; c: entero = 3; d: entero = 4; z: entero = a * (b + c) - d / 2;"))
texto = str(generador.funciones["P.iniciar"])
assert texto.count("sext i32") == 8 and texto.count("trunc i64") == 4
assert "sdiv i64" in texto and "error_division" in bloques(generador, "P.iniciar")
assert valores_iniciales("a: entero = 1; b: entero = 2; c: entero = 3; d: entero = 4; "
                         "z: entero = a * (b + c) - d / 2;")[-1] == 3
# Tipos mixtos: el intToFloat del TAC es sitofp
programa, _, generador = compilar(personaje("a: entero = 1; b: real = 2.5; r: real = (a + b) * 2;"))
assert str(generador.funciones["P.iniciar"]).count("sitofp i32") == 2
assert valores_iniciales("a: entero = 1; b: real = 2.5; r: real = (a + b) * 2;")[-1] == 7.0
assert valores_iniciales("x: real = 7;") == [7.0]
print("Expresiones y tipos: OK")

# 2. si/sino con if_then, if_else e if_end, como gen_if del laboratorio 8
fuente = personaje("v: logico = verdadero; x: entero = 0;",
                   "inicial estado S { cuando e -> T; } "
                   "estado T { al_entrar { si !v { x = 1; } sino { x = 2; } } cuando e -> S; }")
programa, _, generador = compilar(fuente)
assert bloques(generador, "P.al_entrar_T") == ["entry", "if_then", "if_else", "if_end"]
assert ejecutar(fuente)[0][1][1][2] == [True, 2]
# Un si sin sino deja if_else solo con el salto a if_end
programa, _, generador = compilar(personaje(
    "x: entero = 0;", "inicial estado S { al_entrar { si x > 0 { x = 1; } } cuando e -> S; }"))
if_else = generador.funciones["P.al_entrar_S"].blocks[2]
assert if_else.name == "if_else" and [i.opname for i in if_else.instructions] == ["br"]
print("si/sino: OK")

# 3. Cortocircuito: el lado derecho tiene su propio bloque y phi reúne el resultado
programa, _, generador = compilar(personaje(
    "a: entero = 1; b: entero = 2; c: entero = 3; x: entero = 0;",
    "inicial estado S { al_entrar { si a < b && c != 0 { x = 10; } } cuando e -> S; }"))
assert bloques(generador, "P.al_entrar_S")[:3] == ["entry", "and_rhs", "and_end"]
assert "phi i1 [0, %\"entry\"]" in str(generador.funciones["P.al_entrar_S"]).replace("  ", " ")
# Si el lado izquierdo decide, el derecho no se evalúa: no hay división entre cero
assert valores_iniciales("v: logico = falso && 1 / 0 > 0;") == [False]
assert valores_iniciales("v: logico = verdadero || 1 / 0 > 0;") == [True]
assert valores_iniciales("v: logico = verdadero && 1 / 0 > 0;") == "división entre cero"
assert valores_iniciales("a: logico = verdadero; b: logico = !a; c: logico = a != b;") == [
    True, False, True]
print("Cortocircuito: OK")

# 4. Función de transición: en_E, tomar, siguiente y otro_estado, en el orden del TAC
fuente = personaje(
    "a: entero = 1; b: entero = 2; x: entero = 0;",
    "inicial estado S { cuando e si a == 0 || b > 10 -> T; } "
    "estado T { al_entrar { x = 7; } cuando e -> S; }")
programa, _, generador = compilar(fuente)
assert bloques(generador, "P.cuando_e") == [
    "entry", "en_S", "or_rhs", "or_end", "tomar", "siguiente", "otro_estado",
    "en_T", "otro_estado.1"]
assert ejecutar(fuente)[0][1][1][1] == "S"      # ninguna guarda se cumple: se queda en S
print("Función de transición: OK")

# 5. Casos límite: enteros de 32 bits, división y promoción numérica
casos = {
    "x: entero = 2147483647 + 1;": "desbordamiento de entero",
    "x: entero = 2147483648;": "desbordamiento de entero",
    "x: entero = 50000 * 50000;": "desbordamiento de entero",
    "x: entero = -2147483647 - 1;": [-2147483648],
    "x: entero = -(-2147483647 - 1);": "desbordamiento de entero",
    "x: entero = (-2147483647 - 1) / -1;": "desbordamiento de entero",
    "x: entero = -7 / 2;": [-3],
    "x: entero = 7 / 0;": "división entre cero",
    "x: real = 1.0 / 0.0;": "división entre cero",
    "x: real = 7 / 2 + 0.5;": [3.5],
    "t1: entero = 4; t2: entero = t1 * 2;": [4, 8],
    "x: real = 0.1 + 0.2;": [0.1 + 0.2],
}
for atributos, esperado in casos.items():
    assert valores_iniciales(atributos) == esperado, (atributos, valores_iniciales(atributos))
print(f"Casos límite ({len(casos)}): OK")

# 6. Los ejemplos del repositorio dan la misma traza que la máquina de TAC
ejemplos = os.path.join(os.path.dirname(__file__), "..", "ejemplos")
for nombre in ("caballero.pxl", "slime.pxl", "juego.pxl"):
    ejecutar(open(os.path.join(ejemplos, nombre), encoding="utf-8").read())
programa, _, generador = compilar(open(os.path.join(ejemplos, "caballero.pxl"), encoding="utf-8").read())
with InterfazPixelLang(generador) as interfaz:
    traza = simular_llvm(programa, interfaz)
    assert traza[10] == "  atacar            -> Atacando     vida=25 daño_golpe=25 velocidad=1.0 y=0.0"
    assert traza[-1] == "  fin_aturdimiento  -> Derrotado    vida=0 daño_golpe=25 velocidad=0.0 y=0.0"
    # La interfaz rechaza índices que no existen sin tocar la memoria del personaje
    f = interfaz.funciones
    assert f["pl_iniciar"](INSTANCIAS) == INDICE_INVALIDO and f["pl_evento"](0, 99) == INDICE_INVALIDO
    assert f["pl_estado"](INSTANCIAS) == -1 and f["pl_estado"](-1) == -1 and f["pl_error"](0) == 0
    assert f["pl_entero"](0, 2) == 0           # velocidad es real, no entero
# En un estado final los eventos se ignoran; un error detiene la simulación
ejecutar("personaje Puerta { eventos abrir, cerrar; inicial estado Cerrada { cuando abrir -> Abierta; } "
         "final estado Abierta { } } simular Puerta: cerrar, abrir, cerrar, abrir;")
traza = ejecutar(personaje("a: entero = 0; b: entero = 1;",
                           "inicial estado S { cuando e -> T; } "
                           "estado T { al_entrar { b = b / a; } cuando e -> S; }") + " simular P: e, e;")
assert traza[1][1][-1][1] is None and len(traza[1][1]) == 2
print("Ejemplos e interfaz: OK")

# 7. Instancias: cada una tiene su propia ficha. La instancia n del personaje p es p + P·n,
# con P el número de personajes (en juego.pxl, el caballero es 0 y el slime, 1)
juego, _, generador_juego = compilar(open(os.path.join(ejemplos, "juego.pxl"), encoding="utf-8").read())
with InterfazPixelLang(generador_juego) as interfaz:
    f = interfaz.funciones
    total = len(juego.personajes)
    slimes = [1 + total * n for n in range(3)]
    assert all(f["pl_iniciar"](i) == 0 for i in slimes) and f["pl_iniciar"](0) == 0
    golpe = juego.personajes[1].eventos.index("recibir_golpe")
    assert f["pl_evento"](slimes[1], golpe) == 0          # solo el segundo slime recibe el golpe
    assert [f["pl_entero"](i, 0) for i in slimes] == [30, 20, 30]
    assert [f["pl_estado"](i) for i in slimes] == [0, 2, 0]      # Patrulla, Aturdido, Patrulla
    assert f["pl_estado"](0) == 0 and f["pl_entero"](0, 0) == 100   # el caballero no cambia
    assert f["pl_iniciar"](total * INSTANCIAS - 1) == 0           # la última instancia existe
    assert f["pl_iniciar"](total * INSTANCIAS) == INDICE_INVALIDO  # la siguiente no
    assert f["pl_estado"](3 + total * 5) == -1                    # una instancia sin iniciar
print(f"Instancias ({INSTANCIAS} por personaje): OK")

# 7. Grafo de flujo de control (semana 13) de la función de transición fin_aturdimiento
f = generador.funciones["Caballero.cuando_fin_aturdimiento"]
sucesores = {b.name: [op.name for op in b.terminator.operands if isinstance(op, ir.Block)]
             for b in f.blocks}
predecesores = {b: [a for a in sucesores if b in sucesores[a]] for b in sucesores}
print("CFG de Caballero.cuando_fin_aturdimiento")
for b in f.blocks:
    print(f"  {b.name:<12} {b.terminator.opname.split()[0]:<4} "
          f"sucesores: {', '.join(sucesores[b.name]) or '-':<26} "
          f"predecesores: {', '.join(predecesores[b.name]) or '-'}")
assert sucesores == {"entry": ["en_Aturdido", "otro_estado"], "en_Aturdido": ["tomar", "siguiente"],
                     "tomar": [], "siguiente": [], "otro_estado": []}
print("CFG: OK")
