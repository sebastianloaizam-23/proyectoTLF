"""Análisis semántico de UAV-LANG.

Verifica lo que la gramática (que acepta una o más instrucciones <config>) no
puede expresar: RF04 (los cinco parámetros), RF05 (orden), RF06 (valores
positivos) y RF12 (sin repeticiones). Solo se ejecuta si no hubo errores
léxicos ni sintácticos. Construye la tabla de símbolos del perfil.
"""
from tokens import ORDEN_PARAMETROS, TK_NUMERO, Error, nombre_parametro


def _configuraciones(arbol):
    """Lista de (token_parametro, token_numero) en orden de aparición."""
    res = []
    for nodo in arbol.recorrer():
        if nodo.nombre == "⟨config⟩":
            parametro = next(h for h in nodo.hijos if h.nombre == "⟨parametro⟩")
            numero = next(h for h in nodo.hijos if h.nombre == TK_NUMERO)
            res.append((parametro.hijos[0].token, numero.token))
    return res


def analizar(arbol):
    """Devuelve (tabla_de_simbolos, errores)."""
    errores = []
    simbolos = {}  # tipo de parámetro -> (valor, token del parámetro)

    def error(msg, tok, regla):
        errores.append(Error("Semántico", msg, tok.linea, tok.columna, regla))

    for par, num in _configuraciones(arbol):
        nombre = nombre_parametro(par.tipo)
        if par.tipo in simbolos:  # RF12 (y RF04: se configura una sola vez)
            previo = simbolos[par.tipo][1]
            error(f"Parámetro {nombre} repetido (ya se configuró en la línea "
                  f"{previo.linea})", par, "RF12")
            continue
        valor = int(num.lexema)
        if valor <= 0:  # RF06: enteros positivos
            error(f"El valor de {nombre} debe ser un entero positivo "
                  f"(se encontró {valor})", num, "RF06")
        simbolos[par.tipo] = (valor, par)

    # RF04: deben estar los cinco. Se reporta en la línea de SEGURIDAD.
    ref = next(n for n in arbol.hijos if n.nombre == "⟨seguridad⟩").primer_token()
    for p in ORDEN_PARAMETROS:
        if p not in simbolos:
            error(f"Falta configurar el parámetro {nombre_parametro(p)}", ref, "RF04")

    # RF05: orden establecido (se compara el orden relativo de los presentes)
    encontrados = [p for p in dict.fromkeys(par.tipo for par, _ in _configuraciones(arbol))]
    esperados = [p for p in ORDEN_PARAMETROS if p in simbolos]
    for i, (hallado, esperado) in enumerate(zip(encontrados, esperados)):
        if hallado != esperado:
            orden = ", ".join(nombre_parametro(p) for p in ORDEN_PARAMETROS)
            error(f"Orden incorrecto: se encontró {nombre_parametro(hallado)} donde se "
                  f"esperaba {nombre_parametro(esperado)}. Orden requerido: {orden}",
                  simbolos[hallado][1], "RF05")
            break

    errores.sort(key=lambda e: (e.linea, e.columna))
    return {nombre_parametro(p): v for p, (v, _) in simbolos.items()}, errores
