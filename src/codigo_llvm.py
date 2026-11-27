"""Generación de código con LLVM para PixelLang (hito 3).

Recorre el AST verificado con llvmlite, como el LLVMGenerator de los laboratorios 7 y 8,
y sigue el esquema del código de tres direcciones del hito 2 (codigo_intermedio.py):

- cada procedimiento del TAC es una función: P.iniciar, P.al_entrar_E y P.cuando_ev;
- cada etiqueta del TAC es un bloque básico y cada salto, el terminador de un bloque
  (br o ret), como en la semana 11;
- los atributos, el estado actual y el código de error de cada personaje son variables
  globales, porque conservan su valor de un evento al siguiente.

Los tipos son i32 (entero), double (real) e i1 (logico). La máquina de TAC detiene la
simulación si hay una división entre cero o un entero que no cabe en 32 bits, y el código
LLVM hace lo mismo: comprueba el divisor antes de dividir y calcula las operaciones
enteras en i64 para revisar el rango antes de truncar a i32. Si algo falla, guarda el
código de error del personaje y la función termina sin ejecutar las acciones que faltan.

El juego usa el código a través de una interfaz C con índices (pl_iniciar, pl_evento,
pl_estado, ...): es la que exporta la biblioteca nativa que llama Unity.

Cada personaje puede tener varias instancias (por ejemplo, tres slimes), cada una con su
propia ficha: una copia de sus atributos, su estado y su código de error. Los
procedimientos trabajan sobre la memoria del personaje, igual que en el TAC; antes de
ejecutar uno, la interfaz copia ahí la ficha de la instancia y después la guarda. La
instancia n del personaje p es p + P·n, donde P es el número de personajes, así que la
instancia p es la primera ficha del personaje p.
"""
import ctypes
import json
import unicodedata
from pathlib import Path

from llvmlite import ir, binding as llvm

from ast_pixellang import Asignacion, Logico, Numero, Unaria, Variable, texto_expresion
from maquina_tac import MINIMO, MAXIMO, ErrorEjecucion, mostrar

I1, I32, I64, F64 = ir.IntType(1), ir.IntType(32), ir.IntType(64), ir.DoubleType()
VOID = ir.VoidType()
TIPOS = {"entero": I32, "real": F64, "logico": I1}
COMPARACIONES = ("<", ">", "<=", ">=", "==", "!=")

# Códigos de error que guarda cada personaje y que devuelve la interfaz C
SIN_ERROR, DIVISION_ENTRE_CERO, DESBORDAMIENTO, INDICE_INVALIDO = 0, 1, 2, 3
ERRORES = {DIVISION_ENTRE_CERO: "división entre cero",
           DESBORDAMIENTO: "desbordamiento de entero",
           INDICE_INVALIDO: "instancia, evento o atributo inválido"}

# Instancias (fichas) de cada personaje que guarda la biblioteca
INSTANCIAS = 64

# Interfaz C: nombre -> (tipo que devuelve, parámetros)
INTERFAZ = {
    "pl_iniciar": (ctypes.c_int32, ["instancia"]),
    "pl_evento": (ctypes.c_int32, ["instancia", "evento"]),
    "pl_estado": (ctypes.c_int32, ["instancia"]),
    "pl_error": (ctypes.c_int32, ["instancia"]),
    "pl_entero": (ctypes.c_int32, ["instancia", "atributo"]),
    "pl_real": (ctypes.c_double, ["instancia", "atributo"]),
    "pl_logico": (ctypes.c_int32, ["instancia", "atributo"]),
}


def nombre_llvm(texto):
    """Los símbolos del código objeto se escriben en ASCII: daño_golpe pasa a dano_golpe."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode() or "x"


def iniciar_llvm():
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()


def maquina_destino(jit=False):
    """La máquina destino es la del equipo que compila (el triple por defecto de LLVM)."""
    iniciar_llvm()
    target = llvm.Target.from_default_triple()
    return target.create_target_machine(reloc="pic", codemodel="jitdefault" if jit else "default",
                                        jit=jit)


class GeneradorLLVM:
    def __init__(self, programa):
        self.programa = programa
        self.maquina = maquina_destino()
        self.module = ir.Module(name="pixellang")
        self.module.triple = self.maquina.triple
        self.module.data_layout = str(self.maquina.target_data)
        if "windows" in self.module.triple:
            # LLVM referencia _fltused cuando hay operaciones con reales; sin la biblioteca de
            # C, la DLL la define ella misma
            fltused = ir.GlobalVariable(self.module, I32, "_fltused")
            fltused.initializer = ir.Constant(I32, 0)
        self.builder = None
        self.memorias = []      # por personaje: sus atributos, su estado y su código de error
        self.memoria = None     # memoria del personaje que se traduce
        self.funciones = {}     # nombre del procedimiento del TAC -> función LLVM
        self.exportadas = []

    # Memoria y procedimientos ----------------------------------------------------

    def variable_global(self, nombre, tipo, inicial=0):
        g = ir.GlobalVariable(self.module, tipo, self.module.get_unique_name(nombre_llvm(nombre)))
        g.linkage = "internal"
        g.initializer = ir.Constant(tipo, inicial)
        return g

    def arreglo_global(self, nombre, tipo, inicial=0):
        """Una variable por instancia: un arreglo de INSTANCIAS elementos."""
        arreglo = ir.ArrayType(tipo, INSTANCIAS)
        g = ir.GlobalVariable(self.module, arreglo, self.module.get_unique_name(nombre_llvm(nombre)))
        g.linkage = "internal"
        # un arreglo de ceros se escribe zeroinitializer; el del estado empieza en -1
        g.initializer = (ir.Constant(arreglo, None) if inicial == 0
                         else ir.Constant(arreglo, [ir.Constant(tipo, inicial)] * INSTANCIAS))
        return g

    def declarar_personaje(self, pj):
        p = pj.nombre
        self.memorias.append({
            "atributos": {a.nombre: self.variable_global(f"{p}.{a.nombre}", TIPOS[a.tipo])
                          for a in pj.atributos},
            "estado": self.variable_global(f"{p}.estado", I32, -1),
            "error": self.variable_global(f"{p}.error", I32, SIN_ERROR),
            # la ficha de cada instancia; la interfaz la copia a la memoria de arriba
            "fichas": {
                "atributos": {a.nombre: self.arreglo_global(f"{p}.fichas.{a.nombre}", TIPOS[a.tipo])
                              for a in pj.atributos},
                "estado": self.arreglo_global(f"{p}.fichas.estado", I32, -1),
                "error": self.arreglo_global(f"{p}.fichas.error", I32, SIN_ERROR),
            },
        })
        procedimientos = (["iniciar"] + [f"al_entrar_{e.nombre}" for e in pj.estados]
                          + [f"cuando_{ev}" for ev in pj.eventos])
        for nombre in procedimientos:
            f = ir.Function(self.module, ir.FunctionType(VOID, []),
                            name=self.module.get_unique_name(nombre_llvm(f"{p}.{nombre}")))
            f.linkage = "internal"
            self.funciones[f"{p}.{nombre}"] = f

    def comenzar(self, procedimiento):
        f = self.funciones[procedimiento]
        self.builder = ir.IRBuilder(f.append_basic_block("entry"))

    def generar(self):
        for pj in self.programa.personajes:
            self.declarar_personaje(pj)
        for k, pj in enumerate(self.programa.personajes):
            self.memoria = self.memorias[k]
            self.generar_personaje(pj)
        self.generar_interfaz()
        self.verificar()
        return self.module

    def verificar(self):
        """Como en el laboratorio 8: el texto del módulo se vuelve a leer y se verifica."""
        compilado = llvm.parse_assembly(str(self.module))
        compilado.verify()
        return compilado

    # Expresiones -----------------------------------------------------------------

    def comprobar(self, falla, codigo, nombre):
        """Si la condición falla es verdadera, guarda el código de error y termina el
        procedimiento; si no, la generación sigue en un bloque nuevo."""
        error_bb = self.builder.function.append_basic_block(nombre)
        sigue_bb = self.builder.function.append_basic_block("sigue")
        self.builder.cbranch(falla, error_bb, sigue_bb)
        self.builder.position_at_end(error_bb)
        self.builder.store(ir.Constant(I32, codigo), self.memoria["error"])
        self.builder.ret_void()
        self.builder.position_at_end(sigue_bb)

    def entero_32(self, valor):
        """valor es un resultado en i64. Si no cabe en 32 bits es un desbordamiento, como
        entero_32 en la máquina de TAC; si cabe, se trunca a i32."""
        menor = self.builder.icmp_signed("<", valor, ir.Constant(I64, MINIMO))
        mayor = self.builder.icmp_signed(">", valor, ir.Constant(I64, MAXIMO))
        self.comprobar(self.builder.or_(menor, mayor), DESBORDAMIENTO, "error_rango")
        return self.builder.trunc(valor, I32)

    def a_real(self, valor):
        """Promoción numérica: el intToFloat del TAC es sitofp en LLVM."""
        return self.builder.sitofp(valor, F64) if valor.type == I32 else valor

    def generar_expr(self, n):
        if isinstance(n, Numero):
            if isinstance(n.valor, float):
                return ir.Constant(F64, n.valor)
            if not MINIMO <= n.valor <= MAXIMO:      # un literal que no cabe en 32 bits
                self.comprobar(ir.Constant(I1, 1), DESBORDAMIENTO, "error_rango")
                return ir.Constant(I32, 0)
            return ir.Constant(I32, n.valor)
        if isinstance(n, Logico):
            return ir.Constant(I1, int(n.valor))
        if isinstance(n, Variable):
            return self.builder.load(self.memoria["atributos"][n.nombre],
                                     name=nombre_llvm(n.nombre))
        if isinstance(n, Unaria):
            v = self.generar_expr(n.operando)
            if n.op == "!":
                return self.builder.not_(v)
            if v.type == F64:
                return self.builder.fneg(v)
            return self.entero_32(self.builder.neg(self.builder.sext(v, I64)))
        if n.op in ("&&", "||"):
            return self.logical(n)
        a = self.generar_expr(n.izquierda)
        b = self.generar_expr(n.derecha)
        if F64 in (a.type, b.type):
            a, b = self.a_real(a), self.a_real(b)
        if n.op in COMPARACIONES:
            if a.type == F64:
                # con NaN, != es verdadero y las demás comparaciones son falsas, como en Python
                comparar = self.builder.fcmp_unordered if n.op == "!=" else self.builder.fcmp_ordered
                return comparar(n.op, a, b)
            return self.builder.icmp_signed(n.op, a, b)
        if n.op == "/":
            if b.type == F64:
                es_cero = self.builder.fcmp_ordered("==", b, ir.Constant(F64, 0.0))
            else:
                es_cero = self.builder.icmp_signed("==", b, ir.Constant(I32, 0))
            self.comprobar(es_cero, DIVISION_ENTRE_CERO, "error_division")
        if a.type == F64:
            ops = {"+": self.builder.fadd, "-": self.builder.fsub,
                   "*": self.builder.fmul, "/": self.builder.fdiv}
            return ops[n.op](a, b)
        a, b = self.builder.sext(a, I64), self.builder.sext(b, I64)
        ops = {"+": self.builder.add, "-": self.builder.sub,
               "*": self.builder.mul, "/": self.builder.sdiv}
        return self.entero_32(ops[n.op](a, b))

    def logical(self, n):
        """&& y || con cortocircuito, como el TODO 6 del laboratorio 8: el lado derecho se
        evalúa en su propio bloque y phi reúne el resultado según el bloque de llegada."""
        nombre = "and" if n.op == "&&" else "or"
        left = self.generar_expr(n.izquierda)
        left_bb = self.builder.block              # bloque donde se decide el cortocircuito
        rhs_bb = self.builder.function.append_basic_block(nombre + "_rhs")
        end_bb = self.builder.function.append_basic_block(nombre + "_end")
        if n.op == "&&":
            self.builder.cbranch(left, rhs_bb, end_bb)   # izquierdo falso: ya es falso
        else:
            self.builder.cbranch(left, end_bb, rhs_bb)   # izquierdo verdadero: ya es verdadero
        self.builder.position_at_end(rhs_bb)
        right = self.generar_expr(n.derecha)
        rhs_bb = self.builder.block               # n.derecha pudo crear más bloques
        self.builder.branch(end_bb)
        self.builder.position_at_end(end_bb)
        phi = self.builder.phi(I1, name=nombre + "_val")
        phi.add_incoming(ir.Constant(I1, 0 if n.op == "&&" else 1), left_bb)
        phi.add_incoming(right, rhs_bb)
        return phi

    # Sentencias ------------------------------------------------------------------

    def generar_asignacion(self, nombre, expresion):
        valor = self.generar_expr(expresion)
        destino = self.memoria["atributos"][nombre]
        if destino.value_type == F64:
            valor = self.a_real(valor)
        self.builder.store(valor, destino)

    def generar_bloque(self, bloque):
        for s in bloque.sentencias:
            if isinstance(s, Asignacion):
                self.generar_asignacion(s.nombre, s.expresion)
            else:
                self.gen_if(s)

    def gen_if(self, s):
        """si/sino con el gen_if del laboratorio 8 (el genIfElse de la semana 11)."""
        cond = self.generar_expr(s.condicion)
        then_bb = self.builder.function.append_basic_block("if_then")
        else_bb = self.builder.function.append_basic_block("if_else")
        end_bb = self.builder.function.append_basic_block("if_end")
        self.builder.cbranch(cond, then_bb, else_bb)
        self.builder.position_at_end(then_bb)
        self.generar_bloque(s.entonces)
        if not self.builder.block.is_terminated:
            self.builder.branch(end_bb)
        self.builder.position_at_end(else_bb)
        if s.sino is not None:
            self.generar_bloque(s.sino)
        if not self.builder.block.is_terminated:
            self.builder.branch(end_bb)
        self.builder.position_at_end(end_bb)

    # Personajes ------------------------------------------------------------------

    def generar_personaje(self, pj):
        p = pj.nombre
        indices = {e.nombre: j for j, e in enumerate(pj.estados)}
        # P.iniciar: sin error, valores iniciales de los atributos y entrada al estado inicial
        self.comenzar(f"{p}.iniciar")
        self.builder.store(ir.Constant(I32, SIN_ERROR), self.memoria["error"])
        self.builder.store(ir.Constant(I32, -1), self.memoria["estado"])
        for a in pj.atributos:
            self.generar_asignacion(a.nombre, a.valor)
        inicial = next(e for e in pj.estados if e.modificador == "inicial")
        self.builder.call(self.funciones[f"{p}.al_entrar_{inicial.nombre}"], [])
        self.builder.ret_void()
        # P.al_entrar_E: guarda el índice de E en estado y ejecuta las acciones de E
        for e in pj.estados:
            self.comenzar(f"{p}.al_entrar_{e.nombre}")
            self.builder.comment(f"estado = {e.nombre}")
            self.builder.store(ir.Constant(I32, indices[e.nombre]), self.memoria["estado"])
            if e.al_entrar:
                self.generar_bloque(e.al_entrar)
            self.builder.ret_void()
        # P.cuando_ev: la función de transición para cada evento
        for ev in pj.eventos:
            self.generar_evento(p, pj, ev, indices)

    def generar_evento(self, p, pj, ev, indices):
        """Igual que generar_evento del TAC: en el estado actual se toma la primera
        transición con ev cuya guarda se cumple; las demás no se prueban."""
        self.comenzar(f"{p}.cuando_{ev}")
        for e in pj.estados:
            transiciones = [t for t in e.transiciones if t.evento == ev]
            if not transiciones:
                continue
            en_estado = self.builder.function.append_basic_block(nombre_llvm(f"en_{e.nombre}"))
            otro_estado = self.builder.function.append_basic_block("otro_estado")
            actual = self.builder.load(self.memoria["estado"], name="estado")
            self.builder.comment(f"estado == {e.nombre}")
            es_estado = self.builder.icmp_signed("==", actual, ir.Constant(I32, indices[e.nombre]),
                                                 name=nombre_llvm(f"es_{e.nombre}"))
            self.builder.cbranch(es_estado, en_estado, otro_estado)
            self.builder.position_at_end(en_estado)
            for t in transiciones:
                if t.guarda is not None:
                    cond = self.generar_expr(t.guarda)
                    tomar = self.builder.function.append_basic_block("tomar")
                    siguiente = self.builder.function.append_basic_block("siguiente")
                    self.builder.cbranch(cond, tomar, siguiente)
                    self.builder.position_at_end(tomar)
                self.builder.call(self.funciones[f"{p}.al_entrar_{t.destino}"], [])
                self.builder.ret_void()
                if t.guarda is not None:
                    self.builder.position_at_end(siguiente)
            if not self.builder.block.is_terminated:
                self.builder.ret_void()             # ninguna guarda se cumplió
            # como en el TAC, el bloque del otro estado va después de las transiciones
            self.builder.function.blocks.remove(otro_estado)
            self.builder.function.blocks.append(otro_estado)
            self.builder.position_at_end(otro_estado)
        self.builder.ret_void()                     # el estado no responde a ev

    # Interfaz C --------------------------------------------------------------------

    def funcion_interfaz(self, nombre):
        retorno, parametros = INTERFAZ[nombre]
        tipo = F64 if retorno is ctypes.c_double else I32
        f = ir.Function(self.module, ir.FunctionType(tipo, [I32] * len(parametros)), name=nombre)
        for arg, nombre_arg in zip(f.args, parametros):
            arg.name = nombre_arg
        self.exportadas.append(nombre)
        return f, ir.IRBuilder(f.append_basic_block("entry"))

    def celda(self, b, arreglo, n):
        """Dirección del elemento n de un arreglo de fichas (getelementptr)."""
        return b.gep(arreglo, [ir.Constant(I32, 0), n], inbounds=True)

    def cargar_ficha(self, b, mem, n):
        """Copia la ficha de la instancia n a la memoria que usan los procedimientos."""
        fichas = mem["fichas"]
        for nombre, g in mem["atributos"].items():
            b.store(b.load(self.celda(b, fichas["atributos"][nombre], n)), g)
        b.store(b.load(self.celda(b, fichas["estado"], n)), mem["estado"])
        b.store(b.load(self.celda(b, fichas["error"], n)), mem["error"])

    def guardar_ficha(self, b, mem, n):
        """Guarda la memoria del personaje en la ficha de la instancia n."""
        fichas = mem["fichas"]
        for nombre, g in mem["atributos"].items():
            b.store(b.load(g), self.celda(b, fichas["atributos"][nombre], n))
        b.store(b.load(mem["estado"]), self.celda(b, fichas["estado"], n))
        b.store(b.load(mem["error"]), self.celda(b, fichas["error"], n))

    def por_instancia(self, f, b, invalido):
        """La instancia n del personaje p es p + P·n. Comprueba que la instancia exista y hace
        un switch sobre p; devuelve (personaje, memoria, bloque, n)."""
        total = ir.Constant(I32, len(self.programa.personajes))
        instancia = f.args[0]
        decodificar = f.append_basic_block("decodificar")
        b.cbranch(b.icmp_signed("<", instancia, ir.Constant(I32, 0)), invalido, decodificar)
        b.position_at_end(decodificar)
        n = b.udiv(instancia, total, name="n")
        p = b.urem(instancia, total, name="personaje")
        elegir = f.append_basic_block("elegir")
        b.cbranch(b.icmp_unsigned("<", n, ir.Constant(I32, INSTANCIAS)), elegir, invalido)
        b.position_at_end(elegir)
        sw = b.switch(p, invalido)
        for k, pj in enumerate(self.programa.personajes):
            bloque = f.append_basic_block(nombre_llvm(pj.nombre))
            sw.add_case(ir.Constant(I32, k), bloque)
            yield pj, self.memorias[k], bloque, n

    def generar_interfaz(self):
        """Funciones exportadas. Los índices siguen el orden de declaración, el mismo del
        mapa JSON que acompaña a la biblioteca."""
        # int pl_iniciar(int instancia)
        f, b = self.funcion_interfaz("pl_iniciar")
        invalido = f.append_basic_block("invalido")
        for pj, mem, bloque, n in self.por_instancia(f, b, invalido):
            b.position_at_end(bloque)
            self.cargar_ficha(b, mem, n)
            b.call(self.funciones[f"{pj.nombre}.iniciar"], [])
            self.guardar_ficha(b, mem, n)
            b.ret(b.load(mem["error"]))
        b.position_at_end(invalido)
        b.ret(ir.Constant(I32, INDICE_INVALIDO))

        # int pl_evento(int instancia, int evento): después de un error ya no se ejecuta
        # nada hasta volver a iniciar la instancia, como en la máquina de TAC
        f, b = self.funcion_interfaz("pl_evento")
        invalido = f.append_basic_block("invalido")
        for pj, mem, bloque, n in self.por_instancia(f, b, invalido):
            b.position_at_end(bloque)
            error = b.load(self.celda(b, mem["fichas"]["error"], n))
            con_error = f.append_basic_block(nombre_llvm(f"{pj.nombre}.con_error"))
            despachar = f.append_basic_block(nombre_llvm(f"{pj.nombre}.despachar"))
            b.cbranch(b.icmp_signed("!=", error, ir.Constant(I32, SIN_ERROR)), con_error, despachar)
            b.position_at_end(con_error)
            b.ret(error)
            b.position_at_end(despachar)
            self.cargar_ficha(b, mem, n)
            sw = b.switch(f.args[1], invalido)
            fin = f.append_basic_block(nombre_llvm(f"{pj.nombre}.guardar"))
            for j, ev in enumerate(pj.eventos):
                bloque_ev = f.append_basic_block(nombre_llvm(f"{pj.nombre}.{ev}"))
                sw.add_case(ir.Constant(I32, j), bloque_ev)
                b.position_at_end(bloque_ev)
                b.call(self.funciones[f"{pj.nombre}.cuando_{ev}"], [])
                b.branch(fin)
            f.blocks.remove(fin)                    # el bloque que guarda va al final
            f.blocks.append(fin)
            b.position_at_end(fin)
            self.guardar_ficha(b, mem, n)
            b.ret(b.load(mem["error"]))
        b.position_at_end(invalido)
        b.ret(ir.Constant(I32, INDICE_INVALIDO))

        # int pl_estado(int instancia) e int pl_error(int instancia)
        for nombre, campo, si_invalido in (("pl_estado", "estado", -1),
                                           ("pl_error", "error", INDICE_INVALIDO)):
            f, b = self.funcion_interfaz(nombre)
            invalido = f.append_basic_block("invalido")
            for _, mem, bloque, n in self.por_instancia(f, b, invalido):
                b.position_at_end(bloque)
                b.ret(b.load(self.celda(b, mem["fichas"][campo], n)))
            b.position_at_end(invalido)
            b.ret(ir.Constant(I32, si_invalido))

        # int pl_entero, double pl_real e int pl_logico (instancia, atributo): un atributo de
        # otro tipo o un índice fuera de rango devuelven 0
        for nombre, tipo in (("pl_entero", "entero"), ("pl_real", "real"), ("pl_logico", "logico")):
            f, b = self.funcion_interfaz(nombre)
            cero = ir.Constant(f.function_type.return_type, 0)
            invalido = f.append_basic_block("invalido")
            for pj, mem, bloque, n in self.por_instancia(f, b, invalido):
                b.position_at_end(bloque)
                sw = b.switch(f.args[1], invalido)
                for j, a in enumerate(pj.atributos):
                    if a.tipo != tipo:
                        continue
                    bloque_a = f.append_basic_block(nombre_llvm(f"{pj.nombre}.{a.nombre}"))
                    sw.add_case(ir.Constant(I32, j), bloque_a)
                    b.position_at_end(bloque_a)
                    valor = b.load(self.celda(b, mem["fichas"]["atributos"][a.nombre], n))
                    b.ret(b.zext(valor, I32) if tipo == "logico" else valor)
            b.position_at_end(invalido)
            b.ret(cero)


# Mapa de la interfaz y archivos de la compilación -------------------------------------

def mapa_interfaz(programa, trazas_tac=None):
    """Nombres e índices que usa la interfaz C. Si se dan las trazas de la máquina de TAC,
    se agregan como resultado esperado de cada bloque simular (Unity las usa para
    comprobar que la biblioteca da los mismos resultados)."""
    mapa = {"personajes": [{"indice": k, "nombre": pj.nombre,
                            "estados": [e.nombre for e in pj.estados],
                            "inicial": next(e.nombre for e in pj.estados
                                            if e.modificador == "inicial"),
                            "finales": [e.nombre for e in pj.estados if e.modificador == "final"],
                            "eventos": list(pj.eventos),
                            "atributos": [{"indice": j, "nombre": a.nombre, "tipo": a.tipo}
                                          for j, a in enumerate(pj.atributos)],
                            # la función de transición δ, para mostrarla en el juego
                            "transiciones": [{"origen": e.nombre, "evento": t.evento,
                                              "guarda": texto_expresion(t.guarda)
                                              if t.guarda is not None else "",
                                              "destino": t.destino}
                                             for e in pj.estados for t in e.transiciones]}
                           for k, pj in enumerate(programa.personajes)],
            # la instancia n del personaje p es p + P·n (P = número de personajes)
            "instancias_por_personaje": INSTANCIAS,
            "errores": [{"codigo": c, "mensaje": m} for c, m in ERRORES.items()],
            "simulaciones": []}
    if trazas_tac:
        indices = {pj.nombre: k for k, pj in enumerate(programa.personajes)}
        for personaje, pasos in trazas_tac:
            mapa["simulaciones"].append({
                "personaje": indices[personaje],
                "pasos": [{"evento": ev, "estado": est or "",
                           "valores": [float(v) for v in val] if est is not None else [],
                           "error": "" if est is not None else val}
                          for ev, est, val in pasos]})
    return mapa


def emitir(generador, prefijo, trazas_tac=None):
    """Guarda el LLVM IR (.ll), el código objeto (.o u .obj), el ensamblador (.s), el mapa
    de la interfaz (.json) y la lista de funciones exportadas (.def)."""
    p = Path(prefijo)
    p.parent.mkdir(parents=True, exist_ok=True)
    compilado = generador.verificar()
    windows = "windows" in generador.module.triple
    p.with_suffix(".ll").write_text(str(generador.module), encoding="utf-8")
    p.with_suffix(".obj" if windows else ".o").write_bytes(generador.maquina.emit_object(compilado))
    p.with_suffix(".s").write_text(generador.maquina.emit_assembly(compilado), encoding="utf-8")
    mapa = mapa_interfaz(generador.programa, trazas_tac)
    p.with_suffix(".json").write_text(json.dumps(mapa, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    p.with_suffix(".def").write_text("EXPORTS\n" + "\n".join(generador.exportadas) + "\n",
                                     encoding="ascii")
    return p


# Ejecución: JIT o biblioteca nativa -----------------------------------------------------

class InterfazPixelLang:
    """Llama a las funciones de la interfaz C, compiladas con JIT (como ejecutar_jit del
    laboratorio 8) o cargadas desde la biblioteca nativa con ctypes."""

    def __init__(self, generador=None, biblioteca=None):
        self.engine = None
        self.funciones = {}
        if biblioteca is not None:
            self.dll = ctypes.CDLL(str(Path(biblioteca).resolve()))
            for nombre, (retorno, parametros) in INTERFAZ.items():
                fn = getattr(self.dll, nombre)
                fn.restype, fn.argtypes = retorno, [ctypes.c_int32] * len(parametros)
                self.funciones[nombre] = fn
            return
        tm = maquina_destino(jit=True)
        compilado = llvm.parse_assembly(str(generador.module))
        compilado.triple = tm.triple
        compilado.data_layout = str(tm.target_data)
        compilado.verify()
        self.engine = llvm.create_mcjit_compiler(compilado, tm)
        self.engine.finalize_object()
        for nombre, (retorno, parametros) in INTERFAZ.items():
            tipo = ctypes.CFUNCTYPE(retorno, *([ctypes.c_int32] * len(parametros)))
            self.funciones[nombre] = tipo(self.engine.get_function_address(nombre))

    def cerrar(self):
        self.funciones.clear()
        if self.engine is not None:
            self.engine.close()
            self.engine = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()

    def paso(self, k, pj, evento=None):
        """Inicia al personaje k o le envía un evento; devuelve su estado y sus atributos."""
        f = self.funciones
        codigo = f["pl_iniciar"](k) if evento is None else f["pl_evento"](k, pj.eventos.index(evento))
        if codigo != SIN_ERROR:
            raise ErrorEjecucion(ERRORES[codigo])
        estado = pj.estados[f["pl_estado"](k)].nombre
        lectura = {"entero": f["pl_entero"], "real": f["pl_real"], "logico": f["pl_logico"]}
        valores = []
        for j, a in enumerate(pj.atributos):
            v = lectura[a.tipo](k, j)
            valores.append(bool(v) if a.tipo == "logico" else v)
        return estado, valores


def trazas_llvm(programa, interfaz):
    """Ejecuta los bloques simular con el código LLVM. Devuelve lo mismo que trazas() de
    la máquina de TAC: por simulación, el personaje y la lista de pasos."""
    indices = {pj.nombre: k for k, pj in enumerate(programa.personajes)}
    resultado = []
    for sim in programa.simulaciones:
        k = indices[sim.personaje]
        pj = programa.personajes[k]
        pasos = []
        for evento in (None, *sim.eventos):
            try:
                estado, valores = interfaz.paso(k, pj, evento)
            except ErrorEjecucion as e:
                pasos.append((evento or "inicio", None, str(e)))
                break
            pasos.append((evento or "inicio", estado, valores))
        resultado.append((sim.personaje, pasos))
    return resultado


def simular_llvm(programa, interfaz):
    """Las trazas como texto, con el mismo formato que la opción --simular."""
    atributos = {pj.nombre: [a.nombre for a in pj.atributos] for pj in programa.personajes}
    lineas = []
    for p, pasos in trazas_llvm(programa, interfaz):
        if lineas:
            lineas.append("")
        lineas.append(f"simular {p}")
        for evento, estado, valores in pasos:
            if estado is None:
                lineas.append(f"  {evento:<17} error de ejecución: {valores}")
                continue
            texto = " ".join(f"{a}={mostrar(v)}" for a, v in zip(atributos[p], valores))
            lineas.append(f"  {evento:<17} -> {estado:<12} {texto}".rstrip())
    return lineas
