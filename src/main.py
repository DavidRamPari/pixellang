import argparse
import sys

from frontend import tokens, analizar, arbol_indentado, formatear
from semantico import AnalizadorSemantico
from simulador import Simulador


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


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Compilador de PixelLang (hito 1)")
    ap.add_argument("archivo")
    ap.add_argument("--tokens", action="store_true", help="muestra los tokens")
    ap.add_argument("--arbol", action="store_true", help="muestra el árbol sintáctico")
    ap.add_argument("--tabla", action="store_true", help="muestra la tabla de símbolos")
    ap.add_argument("--simular", action="store_true",
                    help="ejecuta los bloques simular si no hay errores")
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

    print("Sin errores léxicos, sintácticos ni semánticos.")
    if args.simular:
        for linea in Simulador(arbol).ejecutar_todo():
            print(linea)
    return 0


if __name__ == "__main__":
    sys.exit(main())
