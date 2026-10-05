from frontend import PixelLangParser as P


class ErrorEjecucion(Exception):
    pass


class Simulador:
    def __init__(self, arbol):
        self.personajes = {pj.ID().getText(): pj for pj in arbol.personaje()}
        self.arbol = arbol

    def ejecutar_todo(self):
        salida = []
        for sim in self.arbol.simulacion():
            nombre = sim.ID(0).getText()
            eventos = [e.getText() for e in sim.ID()[1:]]
            try:
                salida.extend(self.ejecutar(nombre, eventos))
            except ErrorEjecucion as e:
                salida.append(f"Error de ejecución en la simulación de {nombre}: {e}")
        return salida

    def ejecutar(self, nombre, eventos):
        pj = self.personajes[nombre]
        entorno = {}
        for atr in pj.atributo():
            valor = self.evaluar(atr.expr(), entorno)
            if atr.tipo().getText() == "real":
                valor = float(valor)
            entorno[atr.ID().getText()] = valor
        tipos = {a.ID().getText(): a.tipo().getText() for a in pj.atributo()}
        self.visibles = self.modificados(pj)
        estados = {e.ID().getText(): e for e in pj.estado()}
        actual = next(e.ID().getText() for e in pj.estado()
                      if e.modificador() and e.modificador().getText() == "inicial")
        self.entrar(estados[actual], entorno, tipos)

        lineas = [f"simular {nombre}", f"  {'inicio':<17} -> {actual:<12} {self.ver(entorno)}".rstrip()]
        for ev in eventos:
            est = estados[actual]
            if est.modificador() and est.modificador().getText() == "final":
                lineas.append(f"  {ev:<17} ignorado: '{actual}' es final")
                continue
            elegida = None
            for tr in est.transicion():
                if tr.ID(0).getText() != ev:
                    continue
                if tr.guarda() is None or self.evaluar(tr.guarda().expr(), entorno):
                    elegida = tr
                    break
            if elegida is None:
                lineas.append(f"  {ev:<17} -> {actual:<12} (sin transición, se queda)")
                continue
            actual = elegida.ID(1).getText()
            self.entrar(estados[actual], entorno, tipos)
            lineas.append(f"  {ev:<17} -> {actual:<12} {self.ver(entorno)}".rstrip())
        return lineas

    @staticmethod
    def modificados(pj):
        nombres = set()

        def recorrer(bloque):
            for s in bloque.sentencia():
                if isinstance(s, P.AsignacionContext):
                    nombres.add(s.ID().getText())
                else:
                    for b in s.bloque():
                        recorrer(b)

        for est in pj.estado():
            if est.alEntrar():
                recorrer(est.alEntrar().bloque())
        return nombres

    def ver(self, entorno):
        partes = []
        for k, v in entorno.items():
            if k not in self.visibles:
                continue
            if isinstance(v, bool):
                v = "verdadero" if v else "falso"
            partes.append(f"{k}={v}")
        return " ".join(partes)

    def entrar(self, estado, entorno, tipos):
        if estado.alEntrar():
            self.bloque(estado.alEntrar().bloque(), entorno, tipos)

    def bloque(self, ctx, entorno, tipos):
        for s in ctx.sentencia():
            if isinstance(s, P.AsignacionContext):
                nombre = s.ID().getText()
                valor = self.evaluar(s.expr(), entorno)
                entorno[nombre] = float(valor) if tipos[nombre] == "real" else valor
            elif self.evaluar(s.expr(), entorno):
                self.bloque(s.bloque(0), entorno, tipos)
            elif s.bloque(1) is not None:
                self.bloque(s.bloque(1), entorno, tipos)

    def evaluar(self, ctx, entorno):
        if isinstance(ctx, (P.ExprContext, P.ConjContext)):
            hijos = ctx.conj() if isinstance(ctx, P.ExprContext) else ctx.rel()
            if len(hijos) == 1:
                return self.evaluar(hijos[0], entorno)
            if isinstance(ctx, P.ExprContext):
                return any(self.evaluar(c, entorno) for c in hijos)
            return all(self.evaluar(c, entorno) for c in hijos)
        if isinstance(ctx, P.RelContext):
            a = self.evaluar(ctx.arit(0), entorno)
            if not ctx.opRel():
                return a
            b = self.evaluar(ctx.arit(1), entorno)
            return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b,
                    "==": a == b, "!=": a != b}[ctx.opRel().getText()]
        if isinstance(ctx, (P.AritContext, P.TermContext)):
            hijos = list(ctx.getChildren())
            valor = self.evaluar(hijos[0], entorno)
            for i in range(1, len(hijos), 2):
                op, der = hijos[i].getText(), self.evaluar(hijos[i + 1], entorno)
                if op == "+":
                    valor = valor + der
                elif op == "-":
                    valor = valor - der
                elif op == "*":
                    valor = valor * der
                elif der == 0:
                    raise ErrorEjecucion(f"división entre cero en la línea {ctx.start.line}")
                elif isinstance(valor, int) and isinstance(der, int):
                    valor = int(valor / der)
                else:
                    valor = valor / der
            return round(valor, 6) if isinstance(valor, float) else valor
        if isinstance(ctx, P.UnarioContext):
            if ctx.factor():
                return self.evaluar(ctx.factor(), entorno)
            v = self.evaluar(ctx.unario(), entorno)
            return (not v) if ctx.getChild(0).getText() == "!" else -v
        if isinstance(ctx, P.FactorContext):
            if ctx.expr():
                return self.evaluar(ctx.expr(), entorno)
            if ctx.NUM_ENTERO():
                return int(ctx.getText())
            if ctx.NUM_REAL():
                return float(ctx.getText())
            if ctx.VERDADERO():
                return True
            if ctx.FALSO():
                return False
            return entorno[ctx.ID().getText()]
        raise TypeError(type(ctx).__name__)
