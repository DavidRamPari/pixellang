EPS = []

GRAMATICAS = [
    ("C1", [
        ("programa",   [["lista_pers", "lista_sims"]]),
        ("lista_pers", [["lista_pers", "decl_pers"], ["decl_pers"]]),
        ("lista_sims", [["lista_sims", "simulacion"], EPS]),
        ("decl_pers",  [["personaje", "id", "{", "lista_atrs", "decl_evs", "lista_est", "}"]]),
        ("lista_atrs", [["lista_atrs", "decl_atr"], EPS]),
        ("lista_est",  [["lista_est", "decl_est"], ["decl_est"]]),
        ("simulacion", [["simular", "id", ":", "lista_ids", ";"]]),
    ]),
    ("C2", [
        ("decl_atr", [["id", ":", "tipo", "=", "expr", ";"]]),
        ("tipo",     [["entero"], ["real"], ["logico"]]),
    ]),
    ("C3", [
        ("decl_evs",  [["eventos", "lista_ids", ";"]]),
        ("lista_ids", [["lista_ids", ",", "id"], ["id"]]),
    ]),
    ("C4", [
        ("decl_est",  [["modif", "estado", "id", "{", "entrada", "lista_trs", "}"]]),
        ("modif",     [["inicial"], ["final"], EPS]),
        ("entrada",   [["al_entrar", "bloque"], EPS]),
        ("lista_trs", [["lista_trs", "transicion"], EPS]),
    ]),
    ("C5", [
        ("transicion", [["cuando", "id", "guarda", "->", "id", ";"]]),
        ("guarda",     [["si", "expr"], EPS]),
    ]),
    ("C6", [
        ("sentencia",   [["id", "=", "expr", ";"], ["si", "expr", "bloque", "alternativa"]]),
        ("alternativa", [["sino", "bloque"], EPS]),
        ("bloque",      [["{", "lista_sent", "}"]]),
        ("lista_sent",  [["lista_sent", "sentencia"], EPS]),
    ]),
    ("C7", [
        ("expr",   [["expr", "||", "conj"], ["conj"]]),
        ("conj",   [["conj", "&&", "rel"], ["rel"]]),
        ("rel",    [["arit", "oprel", "arit"], ["arit"]]),
        ("oprel",  [["<"], [">"], ["<="], [">="], ["=="], ["!="]]),
        ("arit",   [["arit", "+", "term"], ["arit", "-", "term"], ["term"]]),
        ("term",   [["term", "*", "unario"], ["term", "/", "unario"], ["unario"]]),
        ("unario", [["!", "unario"], ["-", "unario"], ["factor"]]),
        ("factor", [["(", "expr", ")"], ["num"], ["dec"], ["verdadero"], ["falso"], ["id"]]),
    ]),
]

PRODUCCIONES = {cab: alts for _, prods in GRAMATICAS for cab, alts in prods}
DUENO = {cab: clave for clave, prods in GRAMATICAS for cab, _ in prods}
NO_TERMINALES = set(PRODUCCIONES)
TERMINALES = sorted({s for alts in PRODUCCIONES.values() for a in alts for s in a}
                    - NO_TERMINALES)

TOKEN_A_TERMINAL = {"ID": "id", "NUM_ENTERO": "num", "NUM_REAL": "dec", "LOGICO": "logico"}
