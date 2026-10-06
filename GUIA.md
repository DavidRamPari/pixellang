# Guía para compilar y ejecutar PixelLang en Visual Studio Code

Esta guía está pensada para Windows 10 u 11. Al final hay una sección con los cambios para WSL, Linux o macOS.

En este hito, compilar PixelLang significa dos cosas: generar el lexer y el parser a partir de la gramática `PixelLang.g4` con ANTLR, y ejecutar el driver `src/main.py`, que hace el análisis léxico, sintáctico y semántico de un programa `.pxl`. La generación de código con LLVM corresponde al hito 3.

## 1. Programas necesarios

| Programa | Para qué sirve | Cómo comprobarlo |
|---|---|---|
| Java 11 o superior | ANTLR es un archivo `.jar` y necesita Java para ejecutarse | `java -version` |
| Python 3.10 o superior | El compilador está escrito en Python | `py --version` |
| Visual Studio Code | Editor | |
| `antlr-4.13.2-complete.jar` | Genera el lexer y el parser | |

Si falta alguno, se puede instalar desde PowerShell con `winget`:

```
winget install -e --id EclipseAdoptium.Temurin.21.JDK
winget install -e --id Python.Python.3.12
winget install -e --id Microsoft.VisualStudioCode
```

También se pueden descargar desde sus páginas oficiales (adoptium.net, python.org y code.visualstudio.com). Al instalar Python hay que marcar la casilla **Add python.exe to PATH**. Después de instalar, cierra y vuelve a abrir VS Code para que reconozca los programas nuevos.

## 2. Extensiones de VS Code

Instala estas dos extensiones desde la pestaña de extensiones (Ctrl+Shift+X). Al abrir el proyecto, VS Code las sugiere solo, porque están en `.vscode/extensions.json`.

- **Python** (Microsoft): ejecución, depuración y selección del entorno virtual.
- **ANTLR4 grammar syntax support** (Mike Lischke): colorea el archivo `.g4` y puede mostrar los diagramas de las reglas, lo que sirve para la presentación.

## 3. Abrir el proyecto

1. Descomprime `PixelLang_codigo.zip` o clona el repositorio.
2. En VS Code: **File > Open Folder** y elige la carpeta `pixellang`, la que contiene `gramatica`, `src`, `ejemplos` y `pruebas`.
3. Abre una terminal con **Terminal > New Terminal** (Ctrl+ñ en teclado en español). Todos los comandos de esta guía se ejecutan en esa terminal, desde la carpeta `pixellang`.

## 4. Descargar ANTLR

Descarga el `.jar` en la carpeta del proyecto:

```
curl.exe -L -o antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
```

El archivo no se sube al repositorio (está en `.gitignore`), así que cada integrante tiene que descargarlo una vez. La versión del `.jar` tiene que coincidir con la del runtime de Python, 4.13.2.

## 5. Crear el entorno virtual e instalar las dependencias

```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell responde que no puede ejecutar `Activate.ps1`, ejecuta una sola vez el comando siguiente, responde **S** y vuelve a activar el entorno:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Luego, en VS Code, presiona Ctrl+Shift+P, escribe **Python: Select Interpreter** y elige el de `.venv`. Así las terminales nuevas y el botón de ejecutar usan ese entorno.

## 6. Generar el lexer y el parser

```
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -no-listener -o src/generado -Xexact-output-dir gramatica/PixelLang.g4
```

El comando crea la carpeta `src/generado` con `PixelLangLexer.py`, `PixelLangParser.py` y `PixelLangVisitor.py`. Esos archivos no se editan a mano: cada vez que se modifique `PixelLang.g4` hay que volver a ejecutar el comando.

Desde VS Code también se puede hacer con **Ctrl+Shift+B**, que ejecuta la tarea **Generar parser (ANTLR)** definida en `.vscode/tasks.json`.

## 7. Ejecutar el compilador

```
python src/main.py ejemplos/caballero.pxl
python src/main.py ejemplos/caballero.pxl --tokens
python src/main.py ejemplos/caballero.pxl --arbol
python src/main.py ejemplos/caballero.pxl --tabla
```

| Opción | Qué muestra |
|---|---|
| sin opciones | si el programa tiene errores léxicos, sintácticos o semánticos |
| `--tokens` | la lista de tokens: línea, nombre del token y lexema |
| `--arbol` | el árbol sintáctico, un nodo por línea |
| `--tabla` | la tabla de símbolos: el ámbito global con los personajes y el ámbito de cada personaje con sus atributos, eventos y estados |

Las opciones se pueden combinar. Los errores semánticos indican el código, la línea y la columna (contada desde 0, como en ANTLR). Para `ejemplos/caballero.pxl`, `--tabla` empieza así:

```
Ámbito global
NOMBRE             CATEGORÍA  TIPO O MODIFICADOR  LÍNEA
Caballero          personaje                      1

Ámbito de Caballero
NOMBRE             CATEGORÍA  TIPO O MODIFICADOR  LÍNEA
vida               atributo   entero              2
daño_golpe         atributo   entero              3
```

Si el programa no tiene errores, la salida termina con `Sin errores léxicos, sintácticos ni semánticos.`

Para probar un programa propio, crea un archivo `.pxl` y pásalo como argumento.

## 8. Ejecutar con F5

El archivo `.vscode/launch.json` tiene dos configuraciones, que aparecen en la pestaña **Run and Debug** (Ctrl+Shift+D):

- **PixelLang: analizar el archivo abierto**: abre cualquier archivo `.pxl`, elige esta configuración y presiona F5. Primero se regenera el parser y luego se ejecuta `main.py` con `--tokens --arbol --tabla` sobre ese archivo.
- **PixelLang: correr todas las pruebas**: ejecuta `pruebas/correr_pruebas.py`.

Como se ejecuta con el depurador, se pueden poner puntos de interrupción en `src/semantico.py` para ver cómo el visitor llena la tabla de símbolos.

## 9. Pruebas

```
python pruebas/probar_construcciones.py
python pruebas/correr_pruebas.py
```

| Comando | Resultado esperado |
|---|---|
| `probar_construcciones.py` | los 35 ejemplos de las construcciones en `ok` y `fallos: 0` |
| `correr_pruebas.py` | la salida del compilador para cada prueba léxica, sintáctica y semántica |

## 10. Problemas comunes

| Mensaje | Causa y solución |
|---|---|
| `java` no se reconoce como un comando | Java no está en el PATH. Reinstálalo o reinicia VS Code después de instalarlo. |
| `py` o `python` no se reconoce | Python no está en el PATH. Reinstálalo marcando **Add python.exe to PATH**. |
| `No module named 'antlr4'` | El entorno virtual no está activo o faltan dependencias. Actívalo y ejecuta `pip install -r requirements.txt`. |
| `No module named 'PixelLangLexer'` | Falta generar el parser. Ejecuta el paso 6. |
| `Could not deserialize ATN` | El `.jar` y el runtime de Python son de versiones distintas. Usa la 4.13.2 en ambos. |
| `No such file or directory: 'ejemplos/caballero.pxl'` | La terminal no está en la carpeta `pixellang`. Muévete con `cd` a esa carpeta. |
| Las tildes o la ñ se ven mal | Ejecuta `$env:PYTHONUTF8=1` en la terminal y vuelve a correr el comando. |

## 11. WSL, Linux o macOS

Los pasos son los mismos con estos cambios:

```
sudo apt install openjdk-21-jdk python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
curl -L -o antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
```

En macOS, Java se instala con `brew install openjdk`. En lugar de `py` se usa `python3`, y el entorno se activa con `source .venv/bin/activate`. Para trabajar dentro de WSL desde VS Code, se instala la extensión **WSL** de Microsoft y se abre la carpeta con **WSL: Open Folder in WSL**.
