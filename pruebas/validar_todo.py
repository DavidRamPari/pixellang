"""Plan de validación completo (niveles 1 a 8) con un solo comando.

Ejecuta todas las pruebas de la carpeta pruebas, guarda la salida de cada una en la carpeta
evidencias y un resumen en evidencias/resultados.json. El nivel 9 (Unity) se ejecuta dentro
de Unity: unity test unity --mode PlayMode (ver GUIA.md).

Uso: python pruebas/validar_todo.py [cantidad de programas al azar] [semilla]
     python pruebas/validar_todo.py 3000 7
"""
import json
import os
import platform
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, ".."))
sys.path.insert(0, os.path.join(RAIZ, "src"))
from frontend import analizar, tokens                  # noqa: E402
from semantico import AnalizadorSemantico              # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

cantidad = sys.argv[1] if len(sys.argv) > 1 else "3000"
semilla = sys.argv[2] if len(sys.argv) > 2 else "7"
evidencias = os.path.join(RAIZ, "evidencias")
os.makedirs(evidencias, exist_ok=True)
resumen = {"python": platform.python_version(), "sistema": platform.platform(),
           "programas_al_azar": int(cantidad), "semilla": int(semilla), "niveles": {}}
fallos_totales = 0


def guardar(nombre, texto):
    with open(os.path.join(evidencias, nombre), "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def ejecutar(nivel, script, *args):
    """Corre una prueba en otro proceso; pasa si termina bien y no reporta fallos."""
    global fallos_totales
    inicio = time.perf_counter()
    r = subprocess.run([sys.executable, os.path.join(AQUI, script), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    salida = r.stdout + r.stderr
    guardar(script.replace(".py", ".txt"), salida)
    ok = r.returncode == 0 and "fallos: 0" in salida if "fallos:" in salida else r.returncode == 0
    if not ok:
        fallos_totales += 1
    resumen["niveles"].setdefault(nivel, []).append(
        {"prueba": script, "resultado": "pasa" if ok else "falla",
         "segundos": round(time.perf_counter() - inicio, 1),
         "ultima_linea": salida.strip().splitlines()[-1] if salida.strip() else ""})
    print(f"{nivel:<38} {script:<26} {'pasa' if ok else 'FALLA'}")


def archivos(carpeta):
    ruta = os.path.join(AQUI, carpeta)
    return [os.path.join(ruta, f) for f in sorted(os.listdir(ruta)) if f.endswith(".pxl")]


def revisar_errores():
    """Niveles 1 a 3: cada archivo de pruebas/lexico, sintactico y semantico da el error
    que se espera (l0_tokens.pxl es el único sin errores léxicos)."""
    global fallos_totales
    lineas, fallos = [], 0
    for ruta in archivos("lexico"):
        _, errores = tokens(open(ruta, encoding="utf-8").read())
        esperado = os.path.basename(ruta) != "l0_tokens.pxl"
        fallos += bool(errores) != esperado
        lineas.append(f"lexico/{os.path.basename(ruta)}: {len(errores)} errores léxicos")
    for ruta in archivos("sintactico"):
        _, _, errores = analizar(open(ruta, encoding="utf-8").read())
        fallos += not errores
        lineas.append(f"sintactico/{os.path.basename(ruta)}: {len(errores)} errores")
    for ruta in archivos("semantico"):
        arbol, _, errores = analizar(open(ruta, encoding="utf-8").read())
        sem = AnalizadorSemantico()
        sem.analizar(arbol)
        codigos = sorted({e[2] for e in sem.errores})
        esperado = os.path.basename(ruta)[:3].upper()
        fallos += errores != [] or esperado not in codigos
        lineas.append(f"semantico/{os.path.basename(ruta)}: {', '.join(codigos)}")
    lineas.append(f"fallos: {fallos}")
    guardar("errores_esperados.txt", "\n".join(lineas) + "\n")
    fallos_totales += fallos > 0
    nivel = "1 a 3. Léxico, sintáctico y semántico"
    resumen["niveles"][nivel] = [{"prueba": "pruebas/lexico, pruebas/sintactico y pruebas/semantico",
                                  "resultado": "pasa" if fallos == 0 else "falla",
                                  "archivos": len(lineas) - 1}]
    print(f"{nivel:<38} {'errores_esperados':<26} {'pasa' if fallos == 0 else 'FALLA'}")


inicio = time.perf_counter()
revisar_errores()
ejecutar("2. Sintáctico", "probar_construcciones.py")
ejecutar("4. AST", "probar_ast.py")
ejecutar("5. Código intermedio", "probar_tac.py")
ejecutar("6 y 8. Prueba diferencial", "probar_generados.py", cantidad, semilla)
ejecutar("8. Código LLVM", "probar_llvm.py")
ejecutar("8. Biblioteca nativa", "probar_biblioteca.py")
try:
    import llvmlite
    resumen["llvmlite"] = llvmlite.__version__
    from llvmlite import binding
    resumen["llvm"] = ".".join(map(str, binding.llvm_version_info))
except ImportError:
    pass
resumen["segundos"] = round(time.perf_counter() - inicio, 1)
resumen["fallos"] = fallos_totales
guardar("resultados.json", json.dumps(resumen, ensure_ascii=False, indent=2) + "\n")
print(f"7. Regresión: {'todas las pruebas pasan' if fallos_totales == 0 else 'hay fallos'} "
      f"({resumen['segundos']} s). Resumen en evidencias/resultados.json")
print("fallos:", fallos_totales)
sys.exit(1 if fallos_totales else 0)
