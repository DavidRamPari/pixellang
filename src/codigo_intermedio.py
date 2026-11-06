"""Generación de código de tres direcciones (TAC) para PixelLang.

Sigue el laboratorio 6 y la semana 10: cada instrucción Instr tiene a lo más una
operación, cada operación guarda su resultado en un temporal nuevo y las
expresiones se recorren en postorden (generar_expr). Los tipos salen de la tabla
de símbolos del análisis semántico: cuando un entero se combina con un real se
inserta intToFloat. Las condiciones de las guardas y de si/sino se traducen a
saltos con cortocircuito (generar_cond, el genCond de la semana 10).

Cada personaje P se traduce en procedimientos:
  P.iniciar          da el valor inicial a los atributos y entra al estado inicial
  P.al_entrar_E      guarda E en la variable estado y ejecuta las acciones de E
  P.cuando_ev        la función de transición para el evento ev: en el estado
                     actual toma la primera transición con ev cuya guarda se cumple
Cada bloque simular se traduce en un procedimiento simular_N que llama a
P.iniciar y luego al procedimiento de cada evento, en orden.
"""
from dataclasses import dataclass

from ast_pixellang import Asignacion, Binaria, Logico, Numero, Unaria, Variable
from semantico import tipo_aritmetico

ARITMETICOS = ("+", "-", "*", "/")
SALTOS = ("label", "goto", "if", "ifFalse")


@dataclass(frozen=True)
class Instr:
    op: str
    arg1: object = None
    arg2: object = None
    resultado: object = None


def formatear_tac(i):
    if i.op == "copy": return f"{i.resultado} = {i.arg1}"
    if i.op == "label": return f"{i.resultado}:"
    if i.op == "goto": return f"goto {i.resultado}"
    if i.op in ("if", "ifFalse"): return f"{i.op} {i.arg1} goto {i.resultado}"
    if i.op == "call": return f"call {i.arg1}, {i.arg2}"
    if i.op == "return": return "return"
    if i.op == "minus": return f"{i.resultado} = -{i.arg1}"
    if i.op == "!": return f"{i.resultado} = !{i.arg1}"
    if i.op == "intToFloat": return f"{i.resultado} = intToFloat({i.arg1})"
    return f"{i.resultado} = {i.arg1} {i.op} {i.arg2}"


def es_procedimiento(etiqueta):
    """Las etiquetas L1, L2... son internas; las demás empiezan un procedimiento."""
    return not (etiqueta.startswith("L") and etiqueta[1:].isdigit())


def listado_tac(instrucciones):
    lineas = []
    for i in instrucciones:
        if i.op == "label":
            if lineas and es_procedimiento(i.resultado):
                lineas.append("")
            lineas.append(formatear_tac(i))
        else:
            lineas.append("    " + formatear_tac(i))
    return lineas


class GeneradorTAC:
    def __init__(self, tabla_global):
        self.tabla_global = tabla_global   # tabla de símbolos del análisis semántico
        self.tabla = None                  # ámbito del personaje que se traduce
        self.codigo = []
        self.temporales = set()
        self.contador = 0
        self.etiquetas = 0

    def nuevo_temporal(self):
        self.contador += 1
        # un atributo podría llamarse t1, t2...: ese nombre se salta
        while self.tabla and self.tabla.buscar_local(f"t{self.contador}"):
            self.contador += 1
        self.temporales.add(f"t{self.contador}")
        return f"t{self.contador}"

    def nueva_etiqueta(self):
        self.etiquetas += 1
        return f"L{self.etiquetas}"

    # Expresiones -----------------------------------------------------------

    def tipo(self, nodo):
        """Tipo de una expresión, con las mismas reglas del analizador semántico."""
        if isinstance(nodo, Numero): return "real" if isinstance(nodo.valor, float) else "entero"
        if isinstance(nodo, Logico): return "logico"
        if isinstance(nodo, Variable): return self.tabla.buscar(nodo.nombre, "atributo").tipo
        if isinstance(nodo, Unaria): return "logico" if nodo.op == "!" else self.tipo(nodo.operando)
        if nodo.op in ARITMETICOS:
            return tipo_aritmetico([self.tipo(nodo.izquierda), self.tipo(nodo.derecha)])
        return "logico"

    def a_real(self, valor, tipo):
        """Promoción numérica: un entero que se combina con un real se convierte antes."""
        if tipo != "entero":
            return valor
        temp = self.nuevo_temporal()
        self.codigo.append(Instr("intToFloat", valor, None, temp))
        return temp

    def generar_expr(self, nodo):
        if isinstance(nodo, Numero): return str(nodo.valor)
        if isinstance(nodo, Logico): return "verdadero" if nodo.valor else "falso"
        if isinstance(nodo, Variable): return nodo.nombre
        if isinstance(nodo, Unaria):
            valor = self.generar_expr(nodo.operando)
            temp = self.nuevo_temporal()
            self.codigo.append(Instr("minus" if nodo.op == "-" else "!", valor, None, temp))
            return temp
        if isinstance(nodo, Binaria):
            if nodo.op in ("&&", "||"):
                return self.generar_valor_logico(nodo)
            izquierda = self.generar_expr(nodo.izquierda)
            derecha = self.generar_expr(nodo.derecha)
            ti, td = self.tipo(nodo.izquierda), self.tipo(nodo.derecha)
            if "real" in (ti, td):
                izquierda = self.a_real(izquierda, ti)
                derecha = self.a_real(derecha, td)
            temp = self.nuevo_temporal()
            self.codigo.append(Instr(nodo.op, izquierda, derecha, temp))
            return temp
        raise TypeError(f"Nodo no soportado: {type(nodo).__name__}")

    def generar_cond(self, nodo, verdadero, falso):
        """Salta a verdadero si la condición se cumple y a falso si no. En A && B y
        en A || B, B solo se evalúa si A no decide el resultado (cortocircuito)."""
        if isinstance(nodo, Binaria) and nodo.op == "&&":
            medio = self.nueva_etiqueta()
            self.generar_cond(nodo.izquierda, medio, falso)
            self.codigo.append(Instr("label", None, None, medio))
            self.generar_cond(nodo.derecha, verdadero, falso)
        elif isinstance(nodo, Binaria) and nodo.op == "||":
            medio = self.nueva_etiqueta()
            self.generar_cond(nodo.izquierda, verdadero, medio)
            self.codigo.append(Instr("label", None, None, medio))
            self.generar_cond(nodo.derecha, verdadero, falso)
        elif isinstance(nodo, Unaria) and nodo.op == "!":
            self.generar_cond(nodo.operando, falso, verdadero)
        elif isinstance(nodo, Logico):
            self.codigo.append(Instr("goto", None, None, verdadero if nodo.valor else falso))
        else:
            valor = self.generar_expr(nodo)   # una comparación o un atributo logico
            self.codigo.append(Instr("if", valor, None, verdadero))
            self.codigo.append(Instr("goto", None, None, falso))

    def generar_valor_logico(self, nodo):
        """Un && o un || que se usa como valor: se evalúa con saltos y el resultado
        queda en un temporal."""
        verdadero, falso, fin = self.nueva_etiqueta(), self.nueva_etiqueta(), self.nueva_etiqueta()
        self.generar_cond(nodo, verdadero, falso)
        temp = self.nuevo_temporal()
        self.codigo.append(Instr("label", None, None, verdadero))
        self.codigo.append(Instr("copy", "verdadero", None, temp))
        self.codigo.append(Instr("goto", None, None, fin))
        self.codigo.append(Instr("label", None, None, falso))
        self.codigo.append(Instr("copy", "falso", None, temp))
        self.codigo.append(Instr("label", None, None, fin))
        return temp

    # Sentencias ------------------------------------------------------------

    def generar_asignacion(self, nombre, expresion):
        valor = self.generar_expr(expresion)
        if self.tabla.buscar(nombre, "atributo").tipo == "real":
            valor = self.a_real(valor, self.tipo(expresion))
        self.codigo.append(Instr("copy", valor, None, nombre))

    def generar_bloque(self, bloque):
        for s in bloque.sentencias:
            if isinstance(s, Asignacion):
                self.generar_asignacion(s.nombre, s.expresion)
            else:
                self.generar_seleccion(s)

    def generar_seleccion(self, s):
        entonces = self.nueva_etiqueta()
        sino = self.nueva_etiqueta() if s.sino else None
        fin = self.nueva_etiqueta()
        self.generar_cond(s.condicion, entonces, sino or fin)
        self.codigo.append(Instr("label", None, None, entonces))
        self.generar_bloque(s.entonces)
        if s.sino:
            self.codigo.append(Instr("goto", None, None, fin))
            self.codigo.append(Instr("label", None, None, sino))
            self.generar_bloque(s.sino)
        self.codigo.append(Instr("label", None, None, fin))

    # Personajes y simulaciones -----------------------------------------------

    def generar(self, programa):
        for pj in programa.personajes:
            self.generar_personaje(pj)
        self.tabla = None
        for k, sim in enumerate(programa.simulaciones, 1):
            self.codigo.append(Instr("label", None, None, f"simular_{k}"))
            self.codigo.append(Instr("call", f"{sim.personaje}.iniciar", 0))
            for ev in sim.eventos:
                self.codigo.append(Instr("call", f"{sim.personaje}.cuando_{ev}", 0))
            self.codigo.append(Instr("return"))
        return self.codigo

    def generar_personaje(self, pj):
        self.tabla = self.tabla_global.buscar(pj.nombre, "personaje").ambito
        p = pj.nombre
        # P.iniciar: valores iniciales de los atributos y entrada al estado inicial
        self.codigo.append(Instr("label", None, None, f"{p}.iniciar"))
        for a in pj.atributos:
            self.generar_asignacion(a.nombre, a.valor)
        inicial = next(e for e in pj.estados if e.modificador == "inicial")
        self.codigo.append(Instr("call", f"{p}.al_entrar_{inicial.nombre}", 0))
        self.codigo.append(Instr("return"))
        # P.al_entrar_E: un procedimiento por estado
        for e in pj.estados:
            self.codigo.append(Instr("label", None, None, f"{p}.al_entrar_{e.nombre}"))
            self.codigo.append(Instr("copy", e.nombre, None, "estado"))
            if e.al_entrar:
                self.generar_bloque(e.al_entrar)
            self.codigo.append(Instr("return"))
        # P.cuando_ev: la función de transición para cada evento
        for ev in pj.eventos:
            self.generar_evento(p, pj, ev)

    def generar_evento(self, p, pj, ev):
        self.codigo.append(Instr("label", None, None, f"{p}.cuando_{ev}"))
        for e in pj.estados:
            transiciones = [t for t in e.transiciones if t.evento == ev]
            if not transiciones:
                continue
            otro_estado = self.nueva_etiqueta()
            temp = self.nuevo_temporal()
            self.codigo.append(Instr("==", "estado", e.nombre, temp))
            self.codigo.append(Instr("ifFalse", temp, None, otro_estado))
            # Las transiciones se prueban en el orden en que se escribieron; el
            # semántico (E03) asegura que una sin guarda sea la última del evento
            for t in transiciones:
                if t.guarda is not None:
                    tomar, siguiente = self.nueva_etiqueta(), self.nueva_etiqueta()
                    self.generar_cond(t.guarda, tomar, siguiente)
                    self.codigo.append(Instr("label", None, None, tomar))
                self.codigo.append(Instr("call", f"{p}.al_entrar_{t.destino}", 0))
                self.codigo.append(Instr("return"))
                if t.guarda is not None:
                    self.codigo.append(Instr("label", None, None, siguiente))
            if transiciones[-1].guarda is not None:
                self.codigo.append(Instr("return"))   # ninguna guarda se cumplió
            self.codigo.append(Instr("label", None, None, otro_estado))
        self.codigo.append(Instr("return"))           # el estado no responde a ev


def cuadruplos(instrucciones):
    return [(i.op, i.arg1, i.arg2, i.resultado) for i in instrucciones]


def a_triples(instrucciones):
    """Como to_triples del laboratorio 6: el temporal que calcula una instrucción
    se reemplaza por su posición. En copy y en los saltos, el segundo argumento
    del triple es el destino (la variable o la etiqueta)."""
    triples = []
    indice = {}   # temporal -> índice del triple que lo calcula
    for k, i in enumerate(instrucciones):
        arg1 = f"({indice[i.arg1]})" if i.arg1 in indice else i.arg1
        if i.op == "copy" or i.op in SALTOS:
            triples.append((i.op, arg1, i.resultado))
        else:
            arg2 = f"({indice[i.arg2]})" if i.arg2 in indice else i.arg2
            triples.append((i.op, arg1, arg2))
            if i.resultado is not None:
                indice[i.resultado] = k
    return triples


def verificar_tac(instrucciones, temporales):
    """Revisa las condiciones de corrección de la semana 10 que se pueden comprobar
    sin ejecutar el código: cada temporal se define antes de usarse, los destinos
    de los saltos y de las llamadas existen y cada procedimiento termina con
    return. Devuelve la lista de problemas; si está vacía, el TAC está bien formado.
    Como verify() de LLVM, no demuestra que la traducción conserve el significado."""
    problemas = []
    etiquetas = {i.resultado for i in instrucciones if i.op == "label"}
    definidos = set()
    for k, i in enumerate(instrucciones):
        if i.op == "label" and es_procedimiento(i.resultado) and k > 0 \
                and instrucciones[k - 1].op != "return":
            problemas.append(f"{k}: el procedimiento anterior a {i.resultado} no termina con return")
        if i.op in ("goto", "if", "ifFalse") and i.resultado not in etiquetas:
            problemas.append(f"{k}: salta a {i.resultado}, que no existe")
        if i.op == "call" and i.arg1 not in etiquetas:
            problemas.append(f"{k}: llama a {i.arg1}, que no existe")
        if i.op not in ("label", "goto", "call"):
            for arg in (i.arg1, i.arg2):
                if arg in temporales and arg not in definidos:
                    problemas.append(f"{k}: usa {arg} antes de definirlo")
        if i.op not in SALTOS and i.resultado in temporales:
            definidos.add(i.resultado)
    if instrucciones and instrucciones[-1].op != "return":
        problemas.append("el último procedimiento no termina con return")
    return problemas
