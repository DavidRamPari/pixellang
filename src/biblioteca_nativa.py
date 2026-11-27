"""Enlace del código objeto de LLVM en una biblioteca nativa.

En Windows se genera una DLL con link.exe de Visual Studio (o lld-link de LLVM), sin la
biblioteca de C ni punto de entrada: el código de PixelLang solo lee y escribe sus variables
globales. El archivo .def lista las funciones de la interfaz C que se exportan. En Linux y
macOS se usa el compilador de C del sistema para generar un .so o un .dylib.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def buscar_link():
    raiz = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft Visual Studio"
    candidatos = sorted(raiz.glob("*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/link.exe"), reverse=True)
    if candidatos:
        return str(candidatos[0])
    lld = shutil.which("lld-link")
    if lld:
        return lld
    raise RuntimeError("No se encontró link.exe: instala Visual Studio con la carga de trabajo "
                       "Desarrollo para el escritorio con C++, o LLVM (lld-link).")


def enlazar(prefijo):
    """Enlaza prefijo.obj (o prefijo.o) y devuelve la ruta de la biblioteca."""
    p = Path(prefijo).resolve()
    if sys.platform == "win32":
        salida = p.with_suffix(".dll")
        comando = [buscar_link(), "/nologo", "/dll", "/noentry", "/nodefaultlib", "/machine:x64",
                   f"/def:{p.with_suffix('.def')}", f"/out:{salida}", str(p.with_suffix(".obj"))]
    else:
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            raise RuntimeError("No se encontró un compilador de C para enlazar la biblioteca.")
        salida = p.with_suffix(".dylib" if sys.platform == "darwin" else ".so")
        opcion = "-dynamiclib" if sys.platform == "darwin" else "-shared"
        comando = [cc, opcion, "-o", str(salida), str(p.with_suffix(".o"))]
    r = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr).strip())
    return salida
