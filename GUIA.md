# Guía para compilar y ejecutar PixelLang en Visual Studio Code

Esta guía está pensada para Windows 10 u 11. Al final hay una sección con los cambios para WSL, Linux o macOS.

Compilar PixelLang significa dos cosas: generar el lexer y el parser a partir de la gramática `PixelLang.g4` con ANTLR, y ejecutar el driver `src/main.py`. El driver hace el análisis léxico, sintáctico y semántico de un programa `.pxl`, construye su árbol de sintaxis abstracta (AST), genera el código de tres direcciones, sobre el que se ejecutan los bloques `simular`, y genera código LLVM, que se ejecuta con JIT o se enlaza como una biblioteca nativa (una DLL en Windows) que usa la escena de Unity de la carpeta `unity`.

## 1. Programas necesarios

| Programa | Para qué sirve | Cómo comprobarlo |
|---|---|---|
| Java 11 o superior | ANTLR es un archivo `.jar` y necesita Java para ejecutarse | `java -version` |
| Python 3.10 o superior | El compilador está escrito en Python | `py --version` |
| Visual Studio Code | Editor | |
| `antlr-4.13.2-complete.jar` | Genera el lexer y el parser | |
| Visual Studio 2022 o posterior, con **Desarrollo para el escritorio con C++** | Solo para enlazar la DLL (usa su `link.exe`) | |
| .NET SDK 8 o posterior | Solo para la prueba de la DLL desde C# fuera de Unity | `dotnet --list-sdks` |
| Unity 6.3 LTS (6000.3.29f1) | Solo para la escena de la carpeta `unity` | Unity Hub |

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

El comando crea la carpeta `src/generado` con `PixelLangLexer.py`, `PixelLangParser.py` y `PixelLangVisitor.py`. Esos archivos no se editan a mano: cada vez que se modifique `PixelLang.g4` hay que volver a ejecutar el comando. En el hito 2 la gramática cambió (sus alternativas tienen etiquetas), así que después de actualizar el repositorio también hay que volver a generar el parser.

Desde VS Code también se puede hacer con **Ctrl+Shift+B**, que ejecuta la tarea **Generar parser (ANTLR)** definida en `.vscode/tasks.json`.

## 7. Ejecutar el compilador

```
python src/main.py ejemplos/caballero.pxl
python src/main.py ejemplos/caballero.pxl --tokens
python src/main.py ejemplos/caballero.pxl --arbol
python src/main.py ejemplos/caballero.pxl --tabla
python src/main.py ejemplos/caballero.pxl --ast
python src/main.py ejemplos/caballero.pxl --tac
python src/main.py ejemplos/caballero.pxl --cuadruplos --triples
python src/main.py ejemplos/caballero.pxl --simular
```

| Opción | Qué muestra |
|---|---|
| sin opciones | si el programa tiene errores léxicos, sintácticos o semánticos |
| `--tokens` | la lista de tokens: línea, nombre del token y lexema |
| `--arbol` | el árbol sintáctico, un nodo por línea |
| `--tabla` | la tabla de símbolos: el ámbito global con los personajes y el ámbito de cada personaje con sus atributos, eventos y estados |
| `--ast` | el árbol de sintaxis abstracta, un nodo por línea |
| `--tac` | el código de tres direcciones: un procedimiento para iniciar cada personaje, uno por estado y uno por evento, y uno por cada bloque `simular` |
| `--cuadruplos` | el mismo código como cuádruplos (operador, argumento 1, argumento 2, resultado) |
| `--triples` | el mismo código como triples: cada temporal se reemplaza por la posición del triple que lo calcula |
| `--simular` | ejecuta los bloques `simular` sobre el código de tres direcciones y muestra el estado y los atributos después de cada evento. Los enteros son de 32 bits: si un resultado entero se sale de ese rango, o si se divide entre cero, esa simulación se detiene con un error de ejecución |

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

Con `--tac`, el estado `Atacando` del caballero se traduce así. La condición del `si` se convierte en saltos:

```
Caballero.al_entrar_Atacando:
    estado = Atacando
    t2 = vida < 50
    if t2 goto L1
    goto L2
L1:
    velocidad = 1.0
    goto L3
L2:
    velocidad = 1.5
L3:
    return
```

Si el programa no tiene errores, la salida termina con `Sin errores léxicos, sintácticos ni semánticos.` El AST, el código de tres direcciones y la simulación solo se muestran cuando no hay errores.

Para probar un programa propio, crea un archivo `.pxl` y pásalo como argumento.

## 8. Ejecutar con F5

El archivo `.vscode/launch.json` tiene cuatro configuraciones, que aparecen en la pestaña **Run and Debug** (Ctrl+Shift+D):

- **PixelLang: analizar el archivo abierto**: abre cualquier archivo `.pxl`, elige esta configuración y presiona F5. Primero se regenera el parser y luego se ejecuta `main.py` con `--tokens --arbol --tabla` sobre ese archivo.
- **PixelLang: código LLVM y ejecución con JIT del archivo abierto**: lo mismo con `--llvm --jit`.
- **PixelLang: correr todas las pruebas**: ejecuta `pruebas/correr_pruebas.py`.
- **PixelLang: validar todo (niveles 1 a 8)**: ejecuta `pruebas/validar_todo.py 3000 7`.

Como se ejecuta con el depurador, se pueden poner puntos de interrupción en `src/semantico.py` para ver cómo el visitor llena la tabla de símbolos, o en `src/codigo_intermedio.py` y `src/codigo_llvm.py` para seguir la generación del código. Para ver el código intermedio o la simulación con F5, se agregan `--tac` o `--simular` a la lista `args` de la primera configuración.

## 9. Código LLVM, JIT y biblioteca nativa (hito 3)

```
python src/main.py ejemplos/caballero.pxl --llvm
python src/main.py ejemplos/caballero.pxl --jit
python src/main.py ejemplos/caballero.pxl --emitir build/pixellang --biblioteca
```

| Opción | Qué hace |
|---|---|
| `--llvm` | muestra el módulo LLVM IR, después de verificarlo con `verify()` |
| `--jit` | compila el módulo con JIT (MCJIT, como en el laboratorio 8) y ejecuta los bloques `simular`; la traza tiene que ser igual a la de `--simular` |
| `--emitir PREFIJO` | guarda `PREFIJO.ll` (LLVM IR), el código objeto (`.obj` en Windows, `.o` en Linux), el ensamblador (`.s`), el mapa de la interfaz (`.json`) y la lista de funciones exportadas (`.def`) |
| `--biblioteca` | con `--emitir`, enlaza la biblioteca nativa: `PREFIJO.dll` en Windows (con `link.exe` de Visual Studio) o `PREFIJO.so` en Linux |

El módulo tiene una función por procedimiento del código de tres direcciones (`Caballero.iniciar`, `Caballero.al_entrar_Atacando`, `Caballero.cuando_saltar`...) y una interfaz C que es lo único que se exporta:

| Función | Qué hace |
|---|---|
| `int pl_iniciar(int personaje)` | da los valores iniciales y entra al estado inicial; devuelve el código de error |
| `int pl_evento(int personaje, int evento)` | ejecuta la función de transición del evento; devuelve el código de error |
| `int pl_estado(int personaje)` | índice del estado actual (-1 si el índice del personaje no existe) |
| `int pl_error(int personaje)` | código del último error de ejecución |
| `int pl_entero`, `double pl_real`, `int pl_logico` (personaje, atributo) | valor de un atributo |

Los índices siguen el orden de declaración del programa y están en el `.json`. Los códigos de error son 0 sin error, 1 división entre cero, 2 desbordamiento de entero y 3 índice inválido. Después de un error, el personaje no responde a más eventos hasta volver a llamar a `pl_iniciar`, igual que la simulación sobre el TAC se detiene.

## 10. Escena de Unity

La carpeta `unity` es un proyecto de Unity 6.3 (plantilla Universal 2D). Para abrirlo, en Unity Hub se elige **Add > Add project from disk** y la carpeta `unity`; luego se abre la escena `Assets/Scenes/JuegoPixelLang.unity` y se presiona Play. La DLL está en `Assets/Plugins/x86_64` y su mapa, en `Assets/Resources/pixellang.json`; las dos salen de `ejemplos/juego.pxl`, que tiene dos personajes: el caballero (índice 0) y el slime (índice 1).

La escena `JuegoPixelLang` es un minijuego: el caballero se controla con el teclado y un slime lo persigue. El script de C# es el cuerpo de los personajes y la DLL es su cerebro. El script convierte lo que pasa en el juego en eventos y los envía con `pl_evento`; la DLL decide el estado y los atributos, y el script solo los dibuja.

| Lo que pasa en el juego | Evento | Personaje |
|---|---|---|
| Espacio (o W) | `saltar` | caballero |
| J (o K) | `atacar` | caballero |
| termina la animación del salto, del ataque o del aturdimiento | `aterrizar`, `fin_ataque`, `fin_aturdimiento` | caballero |
| el slime lo toca | `recibir_golpe` | caballero |
| la espada lo alcanza o el caballero le cae encima | `recibir_golpe` | slime |
| el caballero entra a su campo de visión o sale de él | `ver_jugador`, `perder_jugador` | slime |
| termina su aturdimiento | `fin_aturdimiento` | slime |

Si un evento no tiene transición en el estado actual, la DLL lo ignora: por ejemplo, `atacar` mientras el caballero está Aturdido. Abajo, la escena muestra la función de transición δ de cada personaje y resalta la transición que se acaba de tomar; un evento ignorado aparece en naranja. La partida termina cuando un personaje llega a su estado final (Derrotado o Aplastado); R reinicia y Tab abre la escena de validación.

La escena `DemoPixelLang` es la validación: el botón **Ejecutar la simulación** repite el bloque `simular` del caballero y compara cada paso con la traza de la máquina de TAC guardada en el mapa.

Si se cambia el programa, se genera de nuevo la DLL y se copia al proyecto (con Unity cerrado, porque Unity no suelta una DLL nativa cargada):

```
python src/main.py ejemplos/juego.pxl --emitir build/unity/pixellang --biblioteca
copy build\unity\pixellang.dll unity\Assets\Plugins\x86_64\
copy build\unity\pixellang.json unity\Assets\Resources\
```

Con Unity cerrado, también se puede usar la herramienta de línea de comandos de Unity (`winget install Unity.CLI`):

```
unity test unity --mode PlayMode
unity run unity -- -executeMethod EscenaPixelLang.ConstruirWindows
```

El primer comando ejecuta las seis pruebas de Unity (nivel 9 del plan de validación) y el segundo construye el reproductor de Windows en `unity/Build`; el reproductor empieza en el minijuego. El menú **PixelLang** del editor tiene las mismas dos acciones: crear las escenas y construir para Windows.

## 11. Pruebas

```
python pruebas/validar_todo.py 3000 7
```

Ese comando ejecuta todas las pruebas de los niveles 1 a 8 del plan de validación, guarda la salida de cada una en la carpeta `evidencias` y termina con `fallos: 0`. Cada prueba también se puede correr sola:

```
python pruebas/probar_construcciones.py
python pruebas/correr_pruebas.py
python pruebas/probar_ast.py
python pruebas/probar_tac.py
python pruebas/probar_llvm.py
python pruebas/probar_biblioteca.py
python pruebas/probar_generados.py 3000 7
dotnet run --project pruebas/nativo
```

| Comando | Resultado esperado |
|---|---|
| `probar_construcciones.py` | los 35 ejemplos de las construcciones en `ok` y `fallos: 0` |
| `correr_pruebas.py` | la salida del compilador para cada prueba léxica, sintáctica y semántica |
| `probar_ast.py` | `OK` en las pruebas de precedencia, asociatividad y estructura del AST, y en el texto de las expresiones que se guarda en el mapa |
| `probar_tac.py` | `OK` en las pruebas del código de tres direcciones, los cuádruplos, los triples y la simulación |
| `probar_llvm.py` | `OK` en las pruebas del código LLVM: bloques de si/sino y de la función de transición, cortocircuito con `phi`, casos límite de los enteros de 32 bits y de la división, ejemplos y grafo de flujo de control |
| `probar_biblioteca.py` | enlaza la DLL del caballero y la del minijuego (`ejemplos/juego.pxl`, dos personajes), las carga con `ctypes` y termina con `fallos: 0` si sus trazas son iguales a las de la máquina de TAC |
| `probar_generados.py` | `fallos: 0`: en los programas generados al azar, el intérprete de referencia (que recorre el AST), la máquina de TAC y el código LLVM con JIT dan la misma traza |
| `dotnet run --project pruebas/nativo` | la DLL usada desde C# con las mismas declaraciones `DllImport` del proyecto de Unity: `fallos: 0` (requiere haber generado `build/pixellang.dll`) |

## 12. Problemas comunes

| Mensaje | Causa y solución |
|---|---|
| `java` no se reconoce como un comando | Java no está en el PATH. Reinstálalo o reinicia VS Code después de instalarlo. |
| `py` o `python` no se reconoce | Python no está en el PATH. Reinstálalo marcando **Add python.exe to PATH**. |
| `No module named 'antlr4'` | El entorno virtual no está activo o faltan dependencias. Actívalo y ejecuta `pip install -r requirements.txt`. |
| `No module named 'PixelLangLexer'` | Falta generar el parser. Ejecuta el paso 6. |
| `Could not deserialize ATN` | El `.jar` y el runtime de Python son de versiones distintas. Usa la 4.13.2 en ambos. |
| Errores semánticos que hablan de `None`, como `no se puede asignar un valor None` | El parser de `src/generado` es de una versión anterior de la gramática. Vuelve a generarlo con el paso 6. |
| `No such file or directory: 'ejemplos/caballero.pxl'` | La terminal no está en la carpeta `pixellang`. Muévete con `cd` a esa carpeta. |
| Las tildes o la ñ se ven mal | Ejecuta `$env:PYTHONUTF8=1` en la terminal y vuelve a correr el comando. |
| `No module named 'llvmlite'` | Falta instalar las dependencias del hito 3: `pip install -r requirements.txt`. |
| `No se encontró link.exe` | Falta Visual Studio con **Desarrollo para el escritorio con C++**. Sin él se pueden usar `--llvm`, `--jit` y `--emitir`, pero no `--biblioteca`. |
| `DllNotFoundException: pixellang` en Unity | Falta `Assets/Plugins/x86_64/pixellang.dll`, o se generó en otro sistema operativo. Genera la DLL en Windows y cópiala como en la sección 10. |

## 13. WSL, Linux o macOS

Los pasos son los mismos con estos cambios:

```
sudo apt install openjdk-21-jdk python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
curl -L -o antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
```

En Linux, `--biblioteca` genera `build/pixellang.so` con el compilador de C del sistema (`sudo apt install build-essential`), y `probar_biblioteca.py` la carga igual que la DLL. La escena de Unity del repositorio usa la DLL de Windows.

En macOS, Java se instala con `brew install openjdk`. En lugar de `py` se usa `python3`, y el entorno se activa con `source .venv/bin/activate`. Para trabajar dentro de WSL desde VS Code, se instala la extensión **WSL** de Microsoft y se abre la carpeta con **WSL: Open Folder in WSL**.
