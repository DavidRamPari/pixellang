import argparse
import sys

from frontend import tokens, analizar, arbol_indentado, formatear
from semantico import AnalizadorSemantico
from ast_pixellang import construir_ast, ast_indentado
from codigo_intermedio import GeneradorTAC, listado_tac, cuadruplos, a_triples, verificar_tac
from maquina_tac import simular


def imprimir_tabla(sem):
    encabezado = f"{'NOMBRE':<18} {'CATEGORÍA':<10} {'TIPO O MODIFICADOR':<19} LÍNEA"
    print("Ámbito global")
    print(encabezado)
    for s in sem.tabla_global.simbolos():
        print(f"{s.nombre:<18} {s.categoria:<10} {'':<19} {s.linea}")
    for p in sem.tabla_global.simbolos("personaje"):
        print()
        print(f"Ámbito de {p.nombre}")
        print(encabezado)
        for nombre, categoria, detalle, linea, _ in p.ambito.mostrar():
            print(f"{nombre:<18} {categoria:<10} {detalle:<19} {linea}")
    print()


def texto(valor):
    return "" if valor is None else str(valor)


def imprimir_cuadruplos(codigo):
    print(f"{'#':>4}  {'OP':<11} {'ARG1':<30} {'ARG2':<12} RESULTADO")
    for k, (op, a1, a2, r) in enumerate(cuadruplos(codigo)):
        print(f"{k:>4}  {op:<11} {texto(a1):<30} {texto(a2):<12} {texto(r)}".rstrip())
    print()


def imprimir_triples(codigo):
    print(f"{'#':>4}  {'OP':<11} {'ARG1':<30} ARG2")
    for k, (op, a1, a2) in enumerate(a_triples(codigo)):
        print(f"{k:>4}  {op:<11} {texto(a1):<30} {texto(a2)}".rstrip())
    print()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Compilador de PixelLang")
    ap.add_argument("archivo")
    ap.add_argument("--tokens", action="store_true", help="muestra los tokens")
    ap.add_argument("--arbol", action="store_true", help="muestra el árbol sintáctico")
    ap.add_argument("--tabla", action="store_true", help="muestra la tabla de símbolos")
    ap.add_argument("--ast", action="store_true", help="muestra el árbol de sintaxis abstracta")
    ap.add_argument("--tac", action="store_true", help="muestra el código de tres direcciones")
    ap.add_argument("--cuadruplos", action="store_true",
                    help="muestra el código de tres direcciones como cuádruplos")
    ap.add_argument("--triples", action="store_true",
                    help="muestra el código de tres direcciones como triples")
    ap.add_argument("--simular", action="store_true",
                    help="ejecuta los bloques simular sobre el código de tres direcciones")
    args = ap.parse_args()

    with open(args.archivo, encoding="utf-8") as f:
        fuente = f.read()

    if args.tokens:
        lista, _ = tokens(fuente)
        print(f"{'LÍNEA':<6} {'TOKEN':<12} LEXEMA")
        for nombre, lexema, linea in lista:
            print(f"{linea:<6} {nombre:<12} {lexema}")
        print()

    arbol, parser, errores = analizar(fuente)
    if errores:
        for tipo, linea, col, msg in errores:
            print("\n".join(formatear(f"Error {tipo} en la línea {linea}, columna {col}:", msg)))
        return 1

    if args.arbol:
        print("\n".join(arbol_indentado(arbol, parser)))
        print()

    sem = AnalizadorSemantico()
    sem.analizar(arbol)
    if args.tabla:
        imprimir_tabla(sem)
    for linea, col, msg in sem.advertencias:
        print("\n".join(formatear(f"Advertencia en la línea {linea}, columna {col}:", msg)))
    for linea, col, codigo, msg in sem.errores:
        print("\n".join(formatear(f"Error semántico {codigo} en la línea {linea}, columna {col}:", msg)))
    if sem.errores:
        return 1

    # Generación de código intermedio: AST y código de tres direcciones
    programa = construir_ast(arbol)
    generador = GeneradorTAC(sem.tabla_global)
    codigo = generador.generar(programa)
    problemas = verificar_tac(codigo, generador.temporales)
    if problemas:
        print("Error interno: el código de tres direcciones no está bien formado.")
        print("\n".join("  " + p for p in problemas))
        return 2
    if args.ast:
        print("\n".join(ast_indentado(programa)))
        print()
    if args.tac:
        print("\n".join(listado_tac(codigo)))
        print()
    if args.cuadruplos:
        imprimir_cuadruplos(codigo)
    if args.triples:
        imprimir_triples(codigo)

    print("Sin errores léxicos, sintácticos ni semánticos.")
    if args.simular:
        print()
        if programa.simulaciones:
            print("\n".join(simular(programa, codigo)))
        else:
            print("El programa no tiene bloques simular.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
