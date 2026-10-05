import glob
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(AQUI, "..", "src", "main.py")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

for carpeta in ("lexico", "sintactico", "semantico"):
    for ruta in sorted(glob.glob(os.path.join(AQUI, carpeta, "*.pxl"))):
        print(f"== {carpeta}/{os.path.basename(ruta)}")
        if carpeta == "lexico":
            sys.path.insert(0, os.path.join(AQUI, "..", "src"))
            from frontend import tokens
            lista, errores = tokens(open(ruta, encoding="utf-8").read())
            for nombre, lexema, linea in lista:
                print(f"   {linea:<4} {nombre:<12} {lexema}")
            for tipo, linea, col, msg in errores:
                print(f"   Error {tipo} en {linea}:{col}: {msg}")
        else:
            r = subprocess.run([sys.executable, MAIN, ruta], capture_output=True, text=True, encoding="utf-8")
            print("   " + r.stdout.strip().replace("\n", "\n   "))
