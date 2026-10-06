# PixelLang

Lenguaje de dominio específico para describir la máquina de estados de los personajes de un videojuego 2D. Cada personaje es un autómata finito A = {Q, Σ, δ, q0, F}: sus estados forman Q, sus eventos forman el alfabeto Σ y sus transiciones definen δ. El compilador hace el análisis léxico, sintáctico y semántico de un programa y verifica que ese autómata esté bien formado.

Trabajo Parcial de Teoría de Compiladores, Universidad Peruana de Ciencias Aplicadas, 2026.

## Integrantes

| Código | Apellidos y nombres |
|---|---|
| U20221G222 | Ruiz Soto, Diego Gilmer |
| U202417368 | Ramos Parihuaman, David Miguel |
| U20241D937 | Quito Anccasi, Antony Rodrigo |
| U202412516 | Monge Jiménez, Mateo Alonso |

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

El ejemplo completo, un caballero con atributos, guardas y acciones, está en [ejemplos/caballero.pxl](ejemplos/caballero.pxl).

## Cómo ejecutarlo

La guía completa para instalar, compilar y ejecutar el proyecto en Visual Studio Code está en [GUIA.md](GUIA.md). En resumen, en Windows:

```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -no-listener -o src/generado -Xexact-output-dir gramatica/PixelLang.g4
python src/main.py ejemplos/caballero.pxl --tokens --arbol --tabla
python pruebas/correr_pruebas.py
```

| Opción | Qué muestra |
|---|---|
| sin opciones | si el programa tiene errores léxicos, sintácticos o semánticos |
| `--tokens` | la lista de tokens |
| `--arbol` | el árbol sintáctico |
| `--tabla` | la tabla de símbolos de cada ámbito |

## Estructura

| Carpeta o archivo | Contenido |
|---|---|
| `gramatica/PixelLang.g4` | Gramática combinada: léxico y sintaxis |
| `src/main.py` | Driver |
| `src/frontend.py` | Lexer y parser con recolección de errores |
| `src/semantico.py` | Visitor semántico: tabla de símbolos y errores E01 a E10 |
| `ejemplos/` | Programas de ejemplo |
| `pruebas/` | Pruebas léxicas, sintácticas y semánticas |
| `.vscode/` | Tarea para generar el parser y configuraciones de ejecución |
| `docs/` | Informe y presentación del trabajo parcial |

## Avance

Las tareas de cada hito están en los [issues](https://github.com/DavidRamPari/pixellang/issues) y los [hitos](https://github.com/DavidRamPari/pixellang/milestones) del repositorio.

| Hito | Contenido | Estado |
|---|---|---|
| 1 | Léxico, gramáticas y derivaciones, lexer y parser en ANTLR4, análisis semántico | Terminado |
| 2 | Errores semánticos, arquitectura del compilador y plan de validación | Pendiente |
| 3 | Generación de código con LLVM | Pendiente |
