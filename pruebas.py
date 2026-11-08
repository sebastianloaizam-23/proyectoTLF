"""Pruebas automáticas de UAV-LANG.  Ejecutar:  python pruebas.py

1. Los AFD coinciden con las expresiones regulares (todas las cadenas cortas).
2. PRIMERO/SIGUIENTE calculados coinciden con las tablas del documento (Fase 2)
   y la tabla LL(1) no tiene conflictos.
3. Casos de prueba de perfiles válidos e inválidos (se escriben en ejemplos/).
"""
import itertools
import os
import re
import sys

import lexico
from gramatica import CONFLICTOS, PRIMERO, SIGUIENTE
from main import analizar_texto

PERFIL = [
    "INICIAR PERFIL FPV_01",          # 0
    "MODO ACRO",                      # 1
    "CONFIGURAR ALTURA_MAX 120",      # 2
    "CONFIGURAR VELOCIDAD_MAX 80",    # 3
    "CONFIGURAR BATERIA_MIN 20",      # 4
    "CONFIGURAR TASA_GIRO 200",       # 5
    "CONFIGURAR POTENCIA_MOTOR 75",   # 6
    "SEGURIDAD FAILSAFE RETURN",      # 7
    "VALIDAR PERFIL",                 # 8
    "FINALIZAR PERFIL",               # 9
]


def j(lineas):
    return "\n".join(lineas) + "\n"


def sin(*idx):
    return [l for k, l in enumerate(PERFIL) if k not in idx]


def con(**cambios):
    """Copia del perfil con líneas reemplazadas: con(l2="...")"""
    out = list(PERFIL)
    for k, v in cambios.items():
        out[int(k[1:])] = v
    return out


def swap(a, b):
    out = list(PERFIL)
    out[a], out[b] = out[b], out[a]
    return out


S, L, M = "Sintáctico", "Léxico", "Semántico"

# nombre -> (texto, [(fase, regla), ...])   regla None = sin RF asociada
CASOS = {
    "01_valido_basico": (j(PERFIL), []),
    "02_valido_minusculas_tabs_blancos_crlf": (
        "\n\n" + "\r\n\r\n".join(l.lower().replace(" ", "\t\t") for l in PERFIL), []),
    "03_valido_modo_horizon": (j(con(l1="MODO HORIZON")), []),
    "04_valido_valores_grandes": (j(con(l2="CONFIGURAR ALTURA_MAX 99999999999999999999")), []),
    # --- sintácticos ---
    "10_sin_iniciar_perfil": (j(sin(0)), [(S, "RF01")]),
    "11_sin_identificador": (j(con(l0="INICIAR PERFIL")), [(S, "RF02")]),
    "12_dos_modos": (j(PERFIL[:2] + ["MODO ANGLE"] + PERFIL[2:]), [(S, "RF03")]),
    "13_sin_modo": (j(sin(1)), [(S, "RF03")]),
    "14_sin_seguridad": (j(sin(7)), [(S, "RF07")]),
    "15_validar_antes_de_configurar": (
        j(PERFIL[:2] + ["VALIDAR PERFIL"] + PERFIL[2:8] + PERFIL[9:]),
        [(S, "RF08"), (S, "RF08")]),
    "16_sin_finalizar_perfil": (j(sin(9)), [(S, "RF09")]),
    "17_instruccion_despues_del_fin": (j(PERFIL + ["MODO ACRO"]), [(S, "RF10")]),
    "18_identificador_es_palabra_reservada": (j(con(l0="INICIAR PERFIL ACRO")), [(S, "RF02")]),
    "19_seguridad_con_guion_bajo": (
        j(con(l7="SEGURIDAD_FAILSAFE_RETURN")), [(S, None), (S, "RF07")]),
    "20_falta_numero": (j(con(l2="CONFIGURAR ALTURA_MAX")), [(S, None)]),
    "21_seguridad_incompleta": (j(con(l7="SEGURIDAD FAILSAFE")), [(S, "RF07")]),
    "22_token_sobrante_en_config": (j(con(l2="CONFIGURAR ALTURA_MAX 10 20")), [(S, None)]),
    "23_archivo_vacio": ("", [(S, "RF01")]),
    "24_varios_errores_sintacticos": (j(sin(0, 9)), [(S, "RF01"), (S, "RF09")]),
    # --- léxicos ---
    "30_numero_negativo": (j(con(l2="CONFIGURAR ALTURA_MAX -10")), [(L, "RF06")]),
    "31_numero_decimal": (j(con(l2="CONFIGURAR ALTURA_MAX 10.5")), [(L, "RF06")]),
    "32_identificador_empieza_con_digito": (j(con(l0="INICIAR PERFIL 01_FPV")), [(L, None)]),
    "33_identificador_empieza_con_guion_bajo": (j(con(l0="INICIAR PERFIL _FPV01")), [(L, None)]),
    "34_caracter_fuera_del_alfabeto": (j(con(l1="MODO ACRO @")), [(L, None)]),
    "35_letra_fuera_del_alfabeto": (j(con(l0="INICIAR PERFIL Ñandú")), [(L, None), (L, None)]),
    # --- semánticos ---
    "40_parametro_repetido": (
        j(con(l4="CONFIGURAR ALTURA_MAX 50")), [(M, "RF12"), (M, "RF04")]),
    "41_faltan_parametros": (j(sin(5, 6)), [(M, "RF04"), (M, "RF04")]),
    "42_orden_incorrecto": (j(swap(2, 3)), [(M, "RF05")]),
    "43_valor_cero": (j(con(l3="CONFIGURAR VELOCIDAD_MAX 0")), [(M, "RF06")]),
}


def probar_afd():
    ok = True
    casos = {
        lexico.AFD_ID: r"[A-Za-z][A-Za-z0-9_]*",
        lexico.AFD_NUM: r"[0-9]+",
        lexico.AFD_ESP: r"[ \t\r]+",
        lexico.AFD_NL: r"\n",
    }
    alfabeto = ["a", "Z", "7", "_", "-", " ", "\t", "\n", "ñ"]
    total = 0
    for afd, er in casos.items():
        patron = re.compile(er)
        for n in range(0, 5):
            for tupla in itertools.product(alfabeto, repeat=n):
                s = "".join(tupla)
                total += 1
                if afd.reconocer(s) != bool(patron.fullmatch(s)):
                    print(f"  FALLA AFD {afd.nombre}: {s!r}")
                    ok = False
    print(f"[{'OK' if ok else 'FALLA'}] AFD vs expresiones regulares ({total} cadenas)")
    return ok


def probar_conjuntos():
    primero = {
        "programa": {"TK_INICIAR"}, "inicio": {"TK_INICIAR"}, "modo": {"TK_MODO"},
        "tipo_modo": {"TK_ACRO", "TK_ANGLE", "TK_HORIZON"},
        "lista_config": {"TK_CONFIGURAR"}, "lista_config'": {"TK_CONFIGURAR", "ε"},
        "config": {"TK_CONFIGURAR"},
        "parametro": {"TK_ALTURA_MAX", "TK_VELOCIDAD_MAX", "TK_BATERIA_MIN",
                      "TK_TASA_GIRO", "TK_POTENCIA_MOTOR"},
        "seguridad": {"TK_SEGURIDAD"}, "validar": {"TK_VALIDAR"}, "fin": {"TK_FINALIZAR"},
    }
    siguiente = {
        "programa": {"$"}, "inicio": {"TK_MODO"}, "modo": {"TK_CONFIGURAR"},
        "tipo_modo": {"TK_SALTO_LINEA"}, "lista_config": {"TK_SEGURIDAD"},
        "lista_config'": {"TK_SEGURIDAD"},
        "config": {"TK_CONFIGURAR", "TK_SEGURIDAD"}, "parametro": {"TK_NUMERO"},
        "seguridad": {"TK_VALIDAR"}, "validar": {"TK_FINALIZAR"}, "fin": {"$"},
    }
    ok = primero == PRIMERO and siguiente == SIGUIENTE and not CONFLICTOS
    print(f"[{'OK' if ok else 'FALLA'}] PRIMERO/SIGUIENTE = tablas del documento; "
          f"tabla LL(1) sin conflictos")
    return ok


def probar_casos():
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ejemplos")
    os.makedirs(carpeta, exist_ok=True)
    ok = True
    for nombre, (texto, esperado) in CASOS.items():
        with open(os.path.join(carpeta, nombre + ".uav"), "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        res = analizar_texto(texto)
        obtenido = [(e.fase, e.regla) for e in res.errores]
        bien = obtenido == esperado
        ok &= bien
        print(f"[{'OK' if bien else 'FALLA'}] {nombre}")
        if not bien:
            print(f"      esperado: {esperado}\n      obtenido: {obtenido}")
            for e in res.errores:
                print(f"        {e}")
    return ok


def probar_estres():
    """Un archivo con miles de instrucciones no debe agotar la pila."""
    lineas = PERFIL[:2] + ["CONFIGURAR ALTURA_MAX 5"] * 3000 + PERFIL[7:]
    res = analizar_texto(j(lineas))
    # 2999 repetidos (RF12) + 4 parámetros que faltan (RF04)
    reglas = [e.regla for e in res.errores]
    ok = len(reglas) == 3003 and reglas.count("RF12") == 2999 and reglas.count("RF04") == 4
    print(f"[{'OK' if ok else 'FALLA'}] estrés: 3000 instrucciones sin desbordar la pila")
    return ok


if __name__ == "__main__":
    resultados = [probar_afd(), probar_conjuntos(), probar_casos(), probar_estres()]
    print("\nTODAS LAS PRUEBAS PASARON" if all(resultados) else "\nHAY PRUEBAS FALLIDAS")
    sys.exit(0 if all(resultados) else 1)
