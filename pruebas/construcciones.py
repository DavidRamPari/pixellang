CONSTRUCCIONES = [
    ("C1", "Programa y declaración de personaje", "programa", "programa", [
        """personaje Estatua {
    eventos ser_tocada;
    inicial estado Quieta {
        cuando ser_tocada -> Quieta;
    }
}""",
        """personaje Puerta {
    eventos ser_abierta;
    inicial estado Cerrada {
        cuando ser_abierta -> Abierta;
    }
    final estado Abierta { }
}
simular Puerta: ser_abierta;""",
        """personaje Moneda {
    valor: entero = 10;
    eventos ser_recogida;
    inicial estado Visible {
        cuando ser_recogida -> Recogida;
    }
    final estado Recogida { }
}""",
        """personaje Boton {
    eventos ser_pulsado;
    inicial estado Suelto {
        cuando ser_pulsado -> Suelto;
    }
}
personaje Bandera {
    eventos ser_tocada;
    inicial estado Abajo {
        cuando ser_tocada -> Arriba;
    }
    final estado Arriba { }
}""",
        """personaje Torreta {
    municion: entero = 3;
    eventos disparar, fin_disparo, fin_recarga;
    inicial estado Lista {
        cuando disparar si municion > 0 -> Disparando;
        cuando disparar -> Recargando;
    }
    estado Disparando {
        al_entrar { municion = municion - 1; }
        cuando fin_disparo -> Lista;
    }
    estado Recargando {
        al_entrar { municion = 3; }
        cuando fin_recarga -> Lista;
    }
}
simular Torreta: disparar, fin_disparo, disparar;""",
    ], [0, 1, 2, 3]),

    ("C2", "Declaración de atributos", "atributo", "decl_atr", [
        "vida: entero = 100;",
        "velocidad: real = 2.5;",
        "vivo: logico = verdadero;",
        "gravedad: real = -9.8;",
        "daño_critico: entero = daño_golpe * 2;",
    ], [0, 1, 2, 3]),

    ("C3", "Declaración de eventos", "eventos", "decl_evs", [
        "eventos saltar;",
        "eventos saltar, atacar;",
        "eventos saltar, atacar, recibir_golpe;",
        "eventos ver_jugador, perder_jugador, recibir_golpe;",
        "eventos pulsar_a, pulsar_b, soltar_a, soltar_b, pausar;",
    ], [0, 1, 2, 4]),

    ("C4", "Declaración de estados", "estado", "decl_est", [
        "estado Reposo { }",
        "inicial estado Reposo { cuando saltar -> Saltando; }",
        "final estado Derrotado { }",
        """estado Aturdido {
    al_entrar { vida = vida - daño_golpe; }
    cuando recibir_golpe -> Aturdido;
}""",
        """estado Saltando {
    al_entrar { y = y + 2.5; }
    cuando aterrizar -> Reposo;
    cuando recibir_golpe -> Aturdido;
}""",
    ], [0, 1, 2, 3]),

    ("C5", "Transiciones", "transicion", "transicion", [
        "cuando saltar -> Saltando;",
        "cuando fin_aturdimiento si vida <= 0 -> Derrotado;",
        "cuando fin_ataque -> Reposo;",
        "cuando disparar si municion > 0 && !bloqueada -> Disparando;",
        "cuando recibir_golpe si escudo || vida > 50 -> Bloqueando;",
    ], [0, 1, 3, 4]),

    ("C6", "Acciones: asignación y selección", "sentencia", "sentencia", [
        "vida = 100;",
        "velocidad = velocidad * 0.5;",
        "si vida < 50 { velocidad = 1.0; }",
        "si vida < 50 { velocidad = 1.0; } sino { velocidad = 1.5; }",
        """si escudo {
    escudo = falso;
} sino {
    vida = vida - daño_golpe;
    si vida <= 0 { vivo = falso; }
}""",
    ], [0, 1, 2, 3]),

    ("C7", "Expresiones", "expr", "expr", [
        "vida - 25 < 10",
        "2 * (velocidad + 1.5) / 4",
        "vida <= 0 || !vivo",
        "municion > 0 && escudo != verdadero",
        "-gravedad * tiempo >= 9.8",
    ], [0, 1, 2, 3]),
]
