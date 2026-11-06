"""Pruebas del código de tres direcciones, de los cuádruplos y triples y de la
simulación sobre el TAC. Los resultados esperados siguen los ejemplos del
laboratorio 6 y de la semana 10."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from frontend import analizar                                                  # noqa: E402
from semantico import AnalizadorSemantico                                      # noqa: E402
from ast_pixellang import construir_ast                                        # noqa: E402
from codigo_intermedio import (GeneradorTAC, formatear_tac, es_procedimiento,  # noqa: E402
                               cuadruplos, a_triples, verificar_tac)
from maquina_tac import simular                                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def compilar(fuente):
    arbol, _, errores = analizar(fuente)
    assert not errores, errores
    sem = AnalizadorSemantico()
    sem.analizar(arbol)
    assert not sem.errores, sem.errores
    programa = construir_ast(arbol)
    generador = GeneradorTAC(sem.tabla_global)
    codigo = generador.generar(programa)
    assert verificar_tac(codigo, generador.temporales) == []
    return programa, codigo


def procedimiento(codigo, nombre):
    """Instrucciones de un procedimiento, desde su etiqueta hasta la del siguiente."""
    k = next(k for k, i in enumerate(codigo) if i.op == "label" and i.resultado == nombre)
    lineas = []
    for i in codigo[k + 1:]:
        if i.op == "label" and es_procedimiento(i.resultado):
            break
        lineas.append(formatear_tac(i))
    return lineas


def personaje(atributos, estados="inicial estado S { cuando e -> S; }"):
    return f"personaje P {{ {atributos} eventos e; {estados} }}"


# 1. Expresiones: el mismo TAC del laboratorio 6 para z = a * (b + c) - d / 2
_, codigo = compilar(personaje("a: entero = 1; b: entero = 2; c: entero = 3; d: entero = 4; "
                               "z: entero = a * (b + c) - d / 2;"))
assert procedimiento(codigo, "P.iniciar") == [
    "a = 1", "b = 2", "c = 3", "d = 4",
    "t1 = b + c", "t2 = a * t1", "t3 = d / 2", "t4 = t2 - t3", "z = t4",
    "call P.al_entrar_S, 0", "return"]
# Cuádruplos y triples de esas instrucciones, como en el laboratorio 6
assert cuadruplos(codigo)[5:10] == [("+", "b", "c", "t1"), ("*", "a", "t1", "t2"),
                                    ("/", "d", "2", "t3"), ("-", "t2", "t3", "t4"),
                                    ("copy", "t4", None, "z")]
assert a_triples(codigo)[5:10] == [("+", "b", "c"), ("*", "a", "(5)"), ("/", "d", "2"),
                                   ("-", "(6)", "(7)"), ("copy", "(8)", "z")]
print("Expresiones, cuádruplos y triples: OK")

# 2. Tipos mixtos (semana 10): el entero se convierte con intToFloat antes de operar
_, codigo = compilar(personaje("a: entero = 1; b: real = 2.5; r: real = (a + b) * 2;"))
assert procedimiento(codigo, "P.iniciar")[2:7] == [
    "t1 = intToFloat(a)", "t2 = t1 + b", "t3 = intToFloat(2)", "t4 = t2 * t3", "r = t4"]
_, codigo = compilar(personaje("x: real = 7;"))
assert procedimiento(codigo, "P.iniciar")[:2] == ["t1 = intToFloat(7)", "x = t1"]
# Negación aritmética: un operando, no una resta
_, codigo = compilar(personaje("a: entero = 1; r: entero = -(a + 3);"))
assert procedimiento(codigo, "P.iniciar")[1:4] == ["t1 = a + 3", "t2 = -t1", "r = t2"]
print("Conversiones y operadores unarios: OK")

# 3. Cortocircuito de && en un si: c != 0 solo se evalúa si a < b
_, codigo = compilar(personaje(
    "a: entero = 1; b: entero = 2; c: entero = 3; x: entero = 0;",
    "inicial estado S { al_entrar { si a < b && c != 0 { x = 10; } } cuando e -> S; }"))
assert procedimiento(codigo, "P.al_entrar_S") == [
    "estado = S",
    "t1 = a < b", "if t1 goto L3", "goto L2",
    "L3:", "t2 = c != 0", "if t2 goto L1", "goto L2",
    "L1:", "x = 10",
    "L2:", "return"]
# Cortocircuito de || en una guarda: si a == 0, b > 10 no se evalúa
_, codigo = compilar(personaje(
    "a: entero = 1; b: entero = 2; x: entero = 0;",
    "inicial estado S { cuando e si a == 0 || b > 10 -> T; } "
    "estado T { al_entrar { x = 7; } cuando e -> S; }"))
assert procedimiento(codigo, "P.cuando_e") == [
    "t1 = estado == S", "ifFalse t1 goto L1",
    "t2 = a == 0", "if t2 goto L2", "goto L4",
    "L4:", "t3 = b > 10", "if t3 goto L2", "goto L3",
    "L2:", "call P.al_entrar_T, 0", "return",
    "L3:", "return",
    "L1:", "t4 = estado == T", "ifFalse t4 goto L5", "call P.al_entrar_S, 0", "return",
    "L5:", "return"]
# ! intercambia los destinos; si/sino salta al sino o sigue al entonces
_, codigo = compilar(personaje(
    "v: logico = verdadero; x: entero = 0;",
    "inicial estado S { al_entrar { si !v { x = 1; } sino { x = 2; } } cuando e -> S; }"))
assert procedimiento(codigo, "P.al_entrar_S") == [
    "estado = S", "if v goto L2", "goto L1",
    "L1:", "x = 1", "goto L3",
    "L2:", "x = 2",
    "L3:", "return"]
# Un && usado como valor deja verdadero o falso en un temporal
_, codigo = compilar(personaje("a: entero = 1; b: entero = 2; v: logico = a < b && b > 0;"))
assert procedimiento(codigo, "P.iniciar")[2:15] == [
    "t1 = a < b", "if t1 goto L4", "goto L2",
    "L4:", "t2 = b > 0", "if t2 goto L1", "goto L2",
    "L1:", "t3 = verdadero", "goto L3",
    "L2:", "t3 = falso",
    "L3:"]
print("Cortocircuito y si/sino: OK")

# 4. Si un atributo se llama t1, los temporales no usan ese nombre
_, codigo = compilar(personaje("t1: entero = 5; t2: entero = t1 * 2 + 1;"))
assert procedimiento(codigo, "P.iniciar")[:4] == ["t1 = 5", "t3 = t1 * 2", "t4 = t3 + 1", "t2 = t4"]
print("Nombres de temporales: OK")

# 5. Simulación sobre el TAC de los dos ejemplos del repositorio
ejemplos = os.path.join(os.path.dirname(__file__), "..", "ejemplos")
programa, codigo = compilar(open(os.path.join(ejemplos, "caballero.pxl"), encoding="utf-8").read())
traza = simular(programa, codigo)
assert traza[0] == "simular Caballero"
assert traza[1] == "  inicio            -> Reposo       vida=100 daño_golpe=25 velocidad=0.0 y=0.0"
assert traza[2] == "  saltar            -> Saltando     vida=100 daño_golpe=25 velocidad=0.0 y=2.5"
assert traza[4] == "  atacar            -> Atacando     vida=100 daño_golpe=25 velocidad=1.5 y=0.0"
assert traza[8] == "  recibir_golpe     -> Aturdido     vida=25 daño_golpe=25 velocidad=0.0 y=0.0"
assert traza[9] == "  fin_aturdimiento  -> Reposo       vida=25 daño_golpe=25 velocidad=0.0 y=0.0"
assert traza[10] == "  atacar            -> Atacando     vida=25 daño_golpe=25 velocidad=1.0 y=0.0"
assert traza[-1] == "  fin_aturdimiento  -> Derrotado    vida=0 daño_golpe=25 velocidad=0.0 y=0.0"
programa, codigo = compilar(open(os.path.join(ejemplos, "slime.pxl"), encoding="utf-8").read())
assert [linea.split()[2] for linea in simular(programa, codigo)[1:]] == [
    "Patrulla", "Persecucion", "Aturdido", "Persecucion", "Aturdido", "Aturdido", "Aplastado"]
# En un estado final los eventos se ignoran; sin transición, el personaje se queda
programa, codigo = compilar(
    "personaje Puerta { eventos abrir, cerrar; inicial estado Cerrada { cuando abrir -> Abierta; } "
    "final estado Abierta { } } simular Puerta: cerrar, abrir, cerrar, abrir;")
assert [linea.split()[2] for linea in simular(programa, codigo)[1:]] == [
    "Cerrada", "Cerrada", "Abierta", "Abierta", "Abierta"]
# Una división entre cero se reporta como error de ejecución y detiene esa simulación
programa, codigo = compilar(personaje(
    "a: entero = 0; b: entero = 1;",
    "inicial estado S { cuando e -> T; } estado T { al_entrar { b = b / a; } cuando e -> S; }")
    + " simular P: e, e;")
traza = simular(programa, codigo)
assert traza[-1].split() == ["e", "error", "de", "ejecución:", "división", "entre", "cero",
                             "en", "P.al_entrar_T:", "t1", "=", "b", "/", "a"]
print("Simulación: OK")
