"""Gramática final de UAV-LANG en BNF (Fase 2) y cálculo de PRIMERO, SIGUIENTE
y la tabla de análisis predictivo LL(1).

La gramática está escrita como datos; los conjuntos y la tabla se CALCULAN a
partir de ella, de modo que el parser no depende de tablas escritas a mano.
"""
from tokens import (
    TK_ACRO, TK_ALTURA_MAX, TK_ANGLE, TK_BATERIA_MIN, TK_CONFIGURAR, TK_EOF,
    TK_FAILSAFE, TK_FINALIZAR, TK_HORIZON, TK_IDENTIFICADOR, TK_INICIAR,
    TK_MODO, TK_NUMERO, TK_PERFIL, TK_POTENCIA_MOTOR, TK_RETURN,
    TK_SALTO_LINEA, TK_SEGURIDAD, TK_TASA_GIRO, TK_VALIDAR, TK_VELOCIDAD_MAX,
)

EPS = "ε"
INICIAL = "programa"

# (número de regla, cabeza, cuerpo). Los no terminales van sin ⟨ ⟩.
PRODUCCIONES = [
    (1, "programa", ["inicio", "modo", "lista_config", "seguridad", "validar", "fin"]),
    (2, "inicio", [TK_INICIAR, TK_PERFIL, TK_IDENTIFICADOR, TK_SALTO_LINEA]),
    (3, "modo", [TK_MODO, "tipo_modo", TK_SALTO_LINEA]),
    (4, "tipo_modo", [TK_ACRO]),
    (5, "tipo_modo", [TK_ANGLE]),
    (6, "tipo_modo", [TK_HORIZON]),
    (7, "lista_config", ["config", "lista_config'"]),
    (8, "lista_config'", ["config", "lista_config'"]),
    (9, "lista_config'", []),  # ε
    (10, "config", [TK_CONFIGURAR, "parametro", TK_NUMERO, TK_SALTO_LINEA]),
    (11, "parametro", [TK_ALTURA_MAX]),
    (12, "parametro", [TK_VELOCIDAD_MAX]),
    (13, "parametro", [TK_BATERIA_MIN]),
    (14, "parametro", [TK_TASA_GIRO]),
    (15, "parametro", [TK_POTENCIA_MOTOR]),
    (16, "seguridad", [TK_SEGURIDAD, TK_FAILSAFE, TK_RETURN, TK_SALTO_LINEA]),
    (17, "validar", [TK_VALIDAR, TK_PERFIL, TK_SALTO_LINEA]),
    (18, "fin", [TK_FINALIZAR, TK_PERFIL, TK_SALTO_LINEA]),
]

NO_TERMINALES = []
for _, _cabeza, _ in PRODUCCIONES:
    if _cabeza not in NO_TERMINALES:
        NO_TERMINALES.append(_cabeza)


def primero_secuencia(secuencia, primero):
    """PRIMERO de una secuencia de símbolos (puede contener EPS)."""
    res = set()
    for s in secuencia:
        if s in primero:  # no terminal
            res |= primero[s] - {EPS}
            if EPS not in primero[s]:
                return res
        else:  # terminal
            res.add(s)
            return res
    res.add(EPS)
    return res


def _calcular_primero():
    P = {nt: set() for nt in NO_TERMINALES}
    cambio = True
    while cambio:
        cambio = False
        for _, A, cuerpo in PRODUCCIONES:
            nuevo = primero_secuencia(cuerpo, P)
            if not nuevo <= P[A]:
                P[A] |= nuevo
                cambio = True
    return P


def _calcular_siguiente(P):
    S = {nt: set() for nt in NO_TERMINALES}
    S[INICIAL].add(TK_EOF)
    cambio = True
    while cambio:
        cambio = False
        for _, A, cuerpo in PRODUCCIONES:
            for i, s in enumerate(cuerpo):
                if s not in S:
                    continue
                f = primero_secuencia(cuerpo[i + 1:], P)
                nuevo = f - {EPS}
                if EPS in f:
                    nuevo |= S[A]
                if not nuevo <= S[s]:
                    S[s] |= nuevo
                    cambio = True
    return S


def _calcular_tabla(P, S):
    """Tabla LL(1): (no terminal, terminal) -> número de regla."""
    tabla, conflictos = {}, []
    for n, A, cuerpo in PRODUCCIONES:
        f = primero_secuencia(cuerpo, P)
        terminales = f - {EPS}
        if EPS in f:
            terminales |= S[A]
        for t in terminales:
            if (A, t) in tabla:
                conflictos.append((A, t, tabla[(A, t)], n))
            tabla[(A, t)] = n
    return tabla, conflictos


def _calcular_posteriores(P):
    """Para cada símbolo del cuerpo de la regla (1): los terminales con que
    pueden comenzar las instrucciones que vienen DESPUÉS de él. Se usan para
    recuperarse de errores (modo pánico) sin descartar instrucciones válidas."""
    cuerpo = dict((n, c) for n, _, c in PRODUCCIONES)[1]
    res = {}
    for i, s in enumerate(cuerpo):
        acc = set()
        for t in cuerpo[i + 1:]:
            acc |= P[t] - {EPS}
        res[s] = acc
    return res


PRIMERO = _calcular_primero()
SIGUIENTE = _calcular_siguiente(PRIMERO)
TABLA, CONFLICTOS = _calcular_tabla(PRIMERO, SIGUIENTE)
POSTERIORES = _calcular_posteriores(PRIMERO)
