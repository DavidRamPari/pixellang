import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from frontend import analizar
from construcciones import CONSTRUCCIONES

fallos = 0
for clave, nombre, regla, _, ejemplos, _ in CONSTRUCCIONES:
    for i, ej in enumerate(ejemplos, 1):
        _, _, errores = analizar(ej, regla)
        estado = "ok " if not errores else "ERR"
        if errores:
            fallos += 1
        print(f"{estado} {clave}.{i} ({regla})" + (f"  {errores}" if errores else ""))
for f in ["caballero.pxl", "slime.pxl"]:
    src = open(os.path.join(os.path.dirname(__file__), "..", "ejemplos", f), encoding="utf-8").read()
    _, _, errores = analizar(src)
    print(("ok " if not errores else "ERR"), f, errores or "")
    fallos += bool(errores)
print("fallos:", fallos)
