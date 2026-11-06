"""Pruebas del AST: estructura, precedencia y asociatividad, como las del laboratorio 6."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from frontend import analizar                                      # noqa: E402
from semantico import AnalizadorSemantico                          # noqa: E402
from ast_pixellang import (construir_ast, ast_indentado, Programa, Personaje,  # noqa: E402
                           Atributo, Estado, Transicion, Simulacion, Bloque, Asignacion,
                           Seleccion, Numero, Logico, Variable, Unaria, Binaria)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def ast_de(fuente):
    arbol, _, errores = analizar(fuente)
    assert not errores, errores
    sem = AnalizadorSemantico()
    sem.analizar(arbol)
    assert not sem.errores, sem.errores
    return construir_ast(arbol)


def expr(texto, tipo="entero"):
    """AST de una expresión, como valor inicial de un atributo r."""
    fuente = ("personaje P { a: entero = 1; b: entero = 2; c: entero = 3; x: real = 0.5; "
              f"v: logico = verdadero; w: logico = falso; r: {tipo} = {texto}; "
              "eventos e; inicial estado S { cuando e -> S; } }")
    return ast_de(fuente).personajes[0].atributos[-1].valor


a, b, c = Variable("a"), Variable("b"), Variable("c")
v, w = Variable("v"), Variable("w")

# Precedencia: * antes que +, como en el laboratorio 6
assert expr("a + b * c") == Binaria("+", a, Binaria("*", b, c))
assert expr("(a + b) * c") == Binaria("*", Binaria("+", a, b), c)
# Asociatividad por la izquierda: (a - b) - c y (a / b) / c
assert expr("a - b - c") == Binaria("-", Binaria("-", a, b), c)
assert expr("a / b / c") == Binaria("/", Binaria("/", a, b), c)
# El menos unario es un nodo propio, no una resta, y tiene más precedencia que *
assert expr("-a * b") == Binaria("*", Unaria("-", a), b)
assert expr("-(a + b)") == Unaria("-", Binaria("+", a, b))
# Las comparaciones agrupan expresiones aritméticas completas
assert expr("a + 1 < b * 2", "logico") == Binaria("<", Binaria("+", a, Numero(1)), Binaria("*", b, Numero(2)))
# && tiene más precedencia que ||, y ! más que ambos
assert expr("v || w && v", "logico") == Binaria("||", v, Binaria("&&", w, v))
assert expr("!v && w", "logico") == Binaria("&&", Unaria("!", v), w)
assert expr("!(v && w)", "logico") == Unaria("!", Binaria("&&", v, w))
# Literales: entero, real y lógico
assert expr("7") == Numero(7) and isinstance(expr("7").valor, int)
assert expr("2.5", "real") == Numero(2.5)
assert expr("verdadero", "logico") == Logico(True) and expr("falso", "logico") == Logico(False)
print("Expresiones: OK")

# Estructura de un programa completo
programa = ast_de(open(os.path.join(os.path.dirname(__file__), "..", "ejemplos", "caballero.pxl"),
                       encoding="utf-8").read())
assert isinstance(programa, Programa) and len(programa.personajes) == 1
caballero = programa.personajes[0]
assert isinstance(caballero, Personaje) and caballero.nombre == "Caballero"
assert caballero.atributos[0] == Atributo("vida", "entero", Numero(100))
assert caballero.atributos[2] == Atributo("velocidad", "real", Numero(0.0))
assert caballero.eventos == ("saltar", "atacar", "aterrizar", "fin_ataque",
                             "recibir_golpe", "fin_aturdimiento")
estados = {e.nombre: e for e in caballero.estados}
assert estados["Reposo"].modificador == "inicial" and estados["Derrotado"].modificador == "final"
assert estados["Saltando"].modificador is None
# al_entrar con una selección si/sino
atacando = estados["Atacando"].al_entrar
assert isinstance(atacando, Bloque) and isinstance(atacando.sentencias[0], Seleccion)
seleccion = atacando.sentencias[0]
assert seleccion.condicion == Binaria("<", Variable("vida"), Numero(50))
assert seleccion.entonces == Bloque((Asignacion("velocidad", Numero(1.0)),))
assert seleccion.sino == Bloque((Asignacion("velocidad", Numero(1.5)),))
# Transiciones en el orden en que se escribieron, con su guarda
aturdido = estados["Aturdido"].transiciones
assert aturdido[1] == Transicion("fin_aturdimiento", Binaria("<=", Variable("vida"), Numero(0)), "Derrotado")
assert aturdido[2] == Transicion("fin_aturdimiento", None, "Reposo")
# Un estado sin al_entrar
assert estados["Reposo"].al_entrar is not None and ast_de(
    "personaje Q { eventos e; inicial estado S { cuando e -> S; } }").personajes[0].estados[0].al_entrar is None
# La simulación guarda el personaje y la secuencia de eventos
assert programa.simulaciones[0] == Simulacion("Caballero", (
    "saltar", "aterrizar", "atacar", "fin_ataque", "recibir_golpe", "recibir_golpe",
    "recibir_golpe", "fin_aturdimiento", "atacar", "fin_ataque", "recibir_golpe", "fin_aturdimiento"))
print("Programa completo: OK")

# El listado del AST usa el mismo formato que la opción --arbol
lineas = ast_indentado(programa)
assert lineas[0] == "Programa" and lineas[1] == '├── Personaje("Caballero")'
assert '│   ├── Atributo("vida", entero)' in lineas
assert any(linea.endswith('Transicion("fin_aturdimiento" -> "Derrotado")') for linea in lineas)
print("Listado del AST: OK")
