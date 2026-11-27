# PixelLang

Lenguaje de dominio específico para describir la máquina de estados de los personajes de un videojuego 2D. Cada personaje es un autómata finito A = {Q, Σ, δ, q0, F}: sus estados forman Q, sus eventos forman el alfabeto Σ y sus transiciones definen δ. El compilador hace el análisis léxico, sintáctico y semántico de un programa, verifica que ese autómata esté bien formado, genera su código intermedio (código de tres direcciones) y lo traduce a LLVM IR, que se ejecuta con JIT o se enlaza como una biblioteca nativa. Un minijuego de Unity usa esa biblioteca: el caballero y dos slimes son personajes de PixelLang (los slimes, dos instancias del mismo personaje, cada una con su estado y su vida), el juego les envía los eventos y el código generado decide sus estados.

Trabajo Parcial y Final de Teoría de Compiladores, Universidad Peruana de Ciencias Aplicadas, 2026.

## Integrantes

| Código | Apellidos y nombres |
|---|---|
| U20221G222 | Ruiz Soto, Diego Gilmer |
| U202417368 | Ramos Parihuaman, David Miguel |
| U20241D937 | Quito Anccasi, Antony Rodrigo |
| U202412516 | Monge Jiménez, Mateo Alonso |

## Entrega del trabajo final (hito 3)

| Entregable | Enlace |
|---|---|
| Informe | [docs/PixelLang_TrabajoFinal.pdf](docs/PixelLang_TrabajoFinal.pdf) |
| Presentación | [docs/PixelLang_TrabajoFinal_Presentacion.pdf](docs/PixelLang_TrabajoFinal_Presentacion.pdf) |
| Video de demostración | [docs/PixelLang_TrabajoFinal_Demo.mp4](docs/PixelLang_TrabajoFinal_Demo.mp4) |
| Minijuego de Unity | carpeta [unity](unity) |
| Evidencias de las pruebas | carpeta [evidencias](evidencias) |

## Entrega del segundo avance (hito 2)

| Entregable | Enlace |
|---|---|
| Informe | [docs/PixelLang_Hito2.pdf](docs/PixelLang_Hito2.pdf) |

## Entrega del trabajo parcial (hito 1)

| Entregable | Enlace |
|---|---|
| Informe | [docs/PixelLang_Hito1.pdf](docs/PixelLang_Hito1.pdf) |
| Presentación | [docs/PixelLang_Presentacion.pdf](docs/PixelLang_Presentacion.pdf) |
| Video de demostración | [Google Drive](https://drive.google.com/file/d/1asrzQjXH87vR6JPZDanqDFVFOEntwdZ8/view?usp=sharing) |

## Ejemplo

```
personaje Puerta {
    eventos ser_abierta;
    inicial estado Cerrada {
        cuando ser_abierta -> Abierta;
    }
    final estado Abierta { }
}

simular Puerta: ser_abierta;
```

El ejemplo completo, un caballero con atributos, guardas y acciones, está en [ejemplos/caballero.pxl](ejemplos/caballero.pxl); [ejemplos/juego.pxl](ejemplos/juego.pxl) junta al caballero y al slime en el programa que usa el minijuego de Unity. Con `--simular`, el compilador ejecuta su bloque `simular` sobre el código de tres direcciones, y con `--jit`, sobre el código LLVM compilado; las dos trazas son iguales:

```
simular Caballero
  inicio            -> Reposo       vida=100 daño_golpe=25 velocidad=0.0 y=0.0
  saltar            -> Saltando     vida=100 daño_golpe=25 velocidad=0.0 y=2.5
  aterrizar         -> Reposo       vida=100 daño_golpe=25 velocidad=0.0 y=0.0
  atacar            -> Atacando     vida=100 daño_golpe=25 velocidad=1.5 y=0.0
  ...
  fin_aturdimiento  -> Derrotado    vida=0 daño_golpe=25 velocidad=0.0 y=0.0
```

## Cómo ejecutarlo

La guía completa para instalar, compilar y ejecutar el proyecto en Visual Studio Code está en [GUIA.md](GUIA.md). En resumen, en Windows:

```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -no-listener -o src/generado -Xexact-output-dir gramatica/PixelLang.g4
python src/main.py ejemplos/caballero.pxl --tokens --arbol --tabla
python src/main.py ejemplos/caballero.pxl --ast --tac --simular
python src/main.py ejemplos/caballero.pxl --llvm --jit
python src/main.py ejemplos/caballero.pxl --emitir build/pixellang --biblioteca
python pruebas/validar_todo.py 3000 7
```

| Opción | Qué muestra |
|---|---|
| sin opciones | si el programa tiene errores léxicos, sintácticos o semánticos |
| `--tokens` | la lista de tokens |
| `--arbol` | el árbol sintáctico |
| `--tabla` | la tabla de símbolos de cada ámbito |
| `--ast` | el árbol de sintaxis abstracta |
| `--tac` | el código de tres direcciones |
| `--cuadruplos` | el código de tres direcciones como cuádruplos |
| `--triples` | el código de tres direcciones como triples |
| `--simular` | la ejecución de los bloques `simular` sobre el código de tres direcciones |
| `--llvm` | el código LLVM IR, verificado con `verify()` |
| `--jit` | la ejecución de los bloques `simular` con el código LLVM compilado con JIT |
| `--emitir PREFIJO` | guarda el LLVM IR, el código objeto, el ensamblador y el mapa de la interfaz |
| `--biblioteca` | con `--emitir`, enlaza la biblioteca nativa (DLL en Windows) |

## Estructura

| Carpeta o archivo | Contenido |
|---|---|
| `gramatica/PixelLang.g4` | Gramática combinada: léxico y sintaxis |
| `src/main.py` | Driver |
| `src/frontend.py` | Lexer y parser con recolección de errores |
| `src/semantico.py` | Visitor semántico: tabla de símbolos y errores E01 a E10 |
| `src/ast_pixellang.py` | Nodos del AST y visitor que lo construye |
| `src/codigo_intermedio.py` | Generador de código de tres direcciones, cuádruplos y triples |
| `src/maquina_tac.py` | Máquina que ejecuta el código de tres direcciones (opción `--simular`) |
| `src/codigo_llvm.py` | Generador de LLVM IR con llvmlite, interfaz C, JIT y emisión del código objeto |
| `src/biblioteca_nativa.py` | Enlace del código objeto como DLL (Windows) o `.so` (Linux) |
| `unity/` | Proyecto de Unity 6.3: el minijuego del caballero contra dos slimes, la escena de validación, la DLL de `ejemplos/juego.pxl` y sus pruebas |
| `evidencias/` | Salida de la última ejecución de todas las pruebas |
| `ejemplos/` | Programas de ejemplo |
| `pruebas/` | Pruebas léxicas, sintácticas, semánticas, del AST, del código intermedio, del código LLVM, de la biblioteca nativa (también desde C#) y diferenciales |
| `.vscode/` | Tarea para generar el parser y configuraciones de ejecución |
| `docs/` | Informes de los hitos 1, 2 y 3 y presentaciones del trabajo parcial y del trabajo final |

## Avance

Las tareas de cada hito están en los [issues](https://github.com/DavidRamPari/pixellang/issues) y los [hitos](https://github.com/DavidRamPari/pixellang/milestones) del repositorio.

| Hito | Contenido | Estado |
|---|---|---|
| 1 | Léxico, gramáticas y derivaciones, lexer y parser en ANTLR4, análisis semántico | Terminado |
| 2 | Gramática actualizada, analizador semántico completo, AST, código de tres direcciones, simulación sobre el TAC, arquitectura del compilador y plan de validación | Terminado |
| 3 | Generación de código con LLVM, biblioteca nativa, escena de Unity y resultados de la validación | Terminado |
