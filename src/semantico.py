from collections import deque
from dataclasses import dataclass, field

from frontend import PixelLangParser as P

ERRORES = {
    "E01": "Transición hacia un estado no declarado",
    "E02": "Evento no declarado",
    "E03": "Transiciones no deterministas",
    "E04": "Estado inicial ausente o repetido",
    "E05": "Estado inalcanzable",
    "E06": "Nombre declarado dos veces o usado para dos cosas",
    "E07": "Atributo no declarado",
    "E08": "Tipos incompatibles",
    "E09": "Estado final con transiciones de salida",
    "E10": "Simulación de un personaje no declarado",
}

NUMERICOS = ("entero", "real")


@dataclass
class Simbolo:
    nombre: str
    categoria: str
    linea: int
    tipo: str = None
    modificador: str = None


@dataclass
class TablaPersonaje:
    nombre: str
    linea: int
    atributos: dict = field(default_factory=dict)
    eventos: dict = field(default_factory=dict)
    estados: dict = field(default_factory=dict)
    transiciones: list = field(default_factory=list)
    inicial: str = None


class AnalizadorSemantico:
    def __init__(self):
        self.personajes = {}
        self.errores = []
        self.advertencias = []

    def error(self, linea, codigo, mensaje):
        self.errores.append((linea, codigo, mensaje))

    def advertir(self, linea, mensaje):
        self.advertencias.append((linea, mensaje))

    @staticmethod
    def compatible(destino, origen):
        if "error" in (destino, origen):
            return True
        return destino == origen or (destino == "real" and origen == "entero")

    def analizar(self, arbol):
        for pj in arbol.personaje():
            self.personaje(pj)
        for sim in arbol.simulacion():
            self.simulacion(sim)
        self.errores.sort(key=lambda e: e[0])
        self.advertencias.sort(key=lambda a: a[0])
        return self.errores

    def personaje(self, ctx):
        nombre = ctx.ID().getText()
        linea = ctx.start.line
        if nombre in self.personajes:
            previo = self.personajes[nombre].linea
            self.error(linea, "E06",
                       f"el personaje '{nombre}' ya fue declarado en la línea {previo}")
            return
        tabla = TablaPersonaje(nombre, linea)
        self.personajes[nombre] = tabla

        for atr in ctx.atributo():
            self.atributo(tabla, atr)
        for ev in ctx.eventos().ID():
            self.declarar(tabla, tabla.eventos, ev.getText(), "evento", ev.symbol.line)
        for est in ctx.estado():
            mod = est.modificador().getText() if est.modificador() else None
            self.declarar(tabla, tabla.estados, est.ID().getText(), "estado",
                          est.start.line, modificador=mod)

        iniciales = [s for s in tabla.estados.values() if s.modificador == "inicial"]
        if not iniciales:
            self.error(linea, "E04",
                       f"el personaje '{nombre}' no tiene estado inicial")
        elif len(iniciales) > 1:
            lista = ", ".join(f"'{s.nombre}'" for s in iniciales)
            self.error(iniciales[1].linea, "E04",
                       f"el personaje '{nombre}' tiene más de un estado inicial: {lista}")
        else:
            tabla.inicial = iniciales[0].nombre

        for est in ctx.estado():
            self.cuerpo_estado(tabla, est)

        self.alcanzabilidad(tabla)

    def declarar(self, tabla, espacio, nombre, categoria, linea, **extra):
        if nombre in espacio:
            previo = espacio[nombre].linea
            self.error(linea, "E06",
                       f"el {categoria} '{nombre}' ya fue declarado en la línea {previo}")
            return False
        for otro in (tabla.atributos, tabla.eventos, tabla.estados):
            if otro is not espacio and nombre in otro:
                previo = otro[nombre]
                self.error(linea, "E06",
                           f"'{nombre}' ya es el nombre de un {previo.categoria} "
                           f"(línea {previo.linea}); un nombre no puede usarse "
                           f"para dos cosas distintas")
                break
        espacio[nombre] = Simbolo(nombre, categoria, linea, **extra)
        return True

    def atributo(self, tabla, ctx):
        nombre = ctx.ID().getText()
        tipo = ctx.tipo().getText()
        tipo_valor = self.tipo_expr(tabla, ctx.expr())
        if not self.compatible(tipo, tipo_valor):
            self.error(ctx.start.line, "E08",
                       f"el atributo '{nombre}' es {tipo} y se inicializa con un valor {tipo_valor}")
        self.declarar(tabla, tabla.atributos, nombre, "atributo", ctx.start.line, tipo=tipo)

    def cuerpo_estado(self, tabla, ctx):
        origen = ctx.ID().getText()
        mod = ctx.modificador().getText() if ctx.modificador() else None
        if ctx.alEntrar():
            self.bloque(tabla, ctx.alEntrar().bloque())

        sin_guarda = {}
        for tr in ctx.transicion():
            evento, destino = tr.ID(0).getText(), tr.ID(1).getText()
            linea = tr.start.line
            if evento not in tabla.eventos:
                self.error(linea, "E02",
                           f"el evento '{evento}' no está declarado en '{tabla.nombre}'")
            if destino not in tabla.estados:
                self.error(linea, "E01",
                           f"la transición de '{origen}' con '{evento}' va hacia "
                           f"'{destino}', que no es un estado declarado")
            if tr.guarda():
                t = self.tipo_expr(tabla, tr.guarda().expr())
                if t not in ("logico", "error"):
                    self.error(linea, "E08",
                               f"la guarda de la transición debe ser logico, no {t}")
            if evento in sin_guarda:
                self.error(linea, "E03",
                           f"en '{origen}', la transición con '{evento}' de la línea "
                           f"{linea} nunca se toma: la de la línea {sin_guarda[evento]} "
                           f"responde al mismo evento sin guarda")
            elif not tr.guarda():
                sin_guarda[evento] = linea
            tabla.transiciones.append((origen, evento, tr.guarda() is not None,
                                       destino, linea))

        if mod == "final" and ctx.transicion():
            self.error(ctx.start.line, "E09",
                       f"'{origen}' es un estado final y no puede tener transiciones")
        if mod != "final" and not ctx.transicion():
            self.advertir(ctx.start.line,
                          f"'{origen}' no tiene transiciones de salida y no es final: "
                          f"el personaje quedaría atrapado ahí")

    def alcanzabilidad(self, tabla):
        if tabla.inicial is None:
            return
        vecinos = {}
        for origen, _, _, destino, _ in tabla.transiciones:
            vecinos.setdefault(origen, []).append(destino)
        visitados = {tabla.inicial}
        cola = deque([tabla.inicial])
        while cola:
            q = cola.popleft()
            for r in vecinos.get(q, []):
                if r in tabla.estados and r not in visitados:
                    visitados.add(r)
                    cola.append(r)
        for nombre, sim in tabla.estados.items():
            if nombre not in visitados:
                self.error(sim.linea, "E05",
                           f"el estado '{nombre}' no es alcanzable desde "
                           f"'{tabla.inicial}'")

    def bloque(self, tabla, ctx):
        for s in ctx.sentencia():
            if isinstance(s, P.AsignacionContext):
                nombre = s.ID().getText()
                t_valor = self.tipo_expr(tabla, s.expr())
                if nombre not in tabla.atributos:
                    self.error(s.start.line, "E07",
                               f"'{nombre}' no es un atributo de '{tabla.nombre}'")
                    continue
                t_var = tabla.atributos[nombre].tipo
                if not self.compatible(t_var, t_valor):
                    self.error(s.start.line, "E08",
                               f"no se puede asignar un valor {t_valor} al atributo "
                               f"'{nombre}', que es {t_var}")
            else:
                t = self.tipo_expr(tabla, s.expr())
                if t not in ("logico", "error"):
                    self.error(s.start.line, "E08",
                               f"la condición de 'si' debe ser logico, no {t}")
                for b in s.bloque():
                    self.bloque(tabla, b)

    def simulacion(self, ctx):
        nombre = ctx.ID(0).getText()
        if nombre not in self.personajes:
            self.error(ctx.start.line, "E10",
                       f"no existe un personaje llamado '{nombre}'")
            return
        tabla = self.personajes[nombre]
        for ev in ctx.ID()[1:]:
            if ev.getText() not in tabla.eventos:
                self.error(ev.symbol.line, "E02",
                           f"el evento '{ev.getText()}' no está declarado en '{nombre}'")

    def tipo_expr(self, tabla, ctx):
        if isinstance(ctx, (P.ExprContext, P.ConjContext)):
            hijos = ctx.conj() if isinstance(ctx, P.ExprContext) else ctx.rel()
            tipos = [self.tipo_expr(tabla, h) for h in hijos]
            if len(tipos) == 1:
                return tipos[0]
            op = "||" if isinstance(ctx, P.ExprContext) else "&&"
            return self.operar_logico(ctx, op, tipos)
        if isinstance(ctx, P.RelContext):
            tipos = [self.tipo_expr(tabla, h) for h in ctx.arit()]
            if len(tipos) == 1:
                return tipos[0]
            op = ctx.opRel().getText()
            a, b = tipos
            if "error" in tipos:
                return "logico"
            if op in ("==", "!="):
                ok = (a in NUMERICOS and b in NUMERICOS) or a == b
            else:
                ok = a in NUMERICOS and b in NUMERICOS
            if not ok:
                self.error(ctx.start.line, "E08",
                           f"no se puede comparar {a} con {b} usando '{op}'")
            return "logico"
        if isinstance(ctx, (P.AritContext, P.TermContext)):
            hijos = ctx.term() if isinstance(ctx, P.AritContext) else ctx.unario()
            tipos = [self.tipo_expr(tabla, h) for h in hijos]
            if len(tipos) == 1:
                return tipos[0]
            ops = [c.getText() for c in ctx.getChildren()
                   if c.getText() in ("+", "-", "*", "/") and not hasattr(c, "getRuleIndex")]
            if "error" in tipos:
                return "error"
            malos = [t for t in tipos if t not in NUMERICOS]
            if malos:
                self.error(ctx.start.line, "E08",
                           f"el operador '{ops[0]}' necesita números y recibió {malos[0]}")
                return "error"
            return "real" if "real" in tipos else "entero"
        if isinstance(ctx, P.UnarioContext):
            if ctx.factor():
                return self.tipo_expr(tabla, ctx.factor())
            t = self.tipo_expr(tabla, ctx.unario())
            op = ctx.getChild(0).getText()
            if t == "error":
                return t
            if op == "!" and t != "logico":
                self.error(ctx.start.line, "E08", f"'!' necesita un valor logico, no {t}")
                return "error"
            if op == "-" and t not in NUMERICOS:
                self.error(ctx.start.line, "E08", f"'-' necesita un número, no {t}")
                return "error"
            return t
        if isinstance(ctx, P.FactorContext):
            if ctx.expr():
                return self.tipo_expr(tabla, ctx.expr())
            if ctx.NUM_ENTERO():
                return "entero"
            if ctx.NUM_REAL():
                return "real"
            if ctx.VERDADERO() or ctx.FALSO():
                return "logico"
            nombre = ctx.ID().getText()
            if nombre not in tabla.atributos:
                self.error(ctx.start.line, "E07",
                           f"'{nombre}' no es un atributo de '{tabla.nombre}'")
                return "error"
            return tabla.atributos[nombre].tipo
        raise TypeError(type(ctx).__name__)

    def operar_logico(self, ctx, op, tipos):
        if "error" in tipos:
            return "logico"
        for t in tipos:
            if t != "logico":
                self.error(ctx.start.line, "E08",
                           f"el operador '{op}' necesita valores logico y recibió {t}")
                break
        return "logico"
