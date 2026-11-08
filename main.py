"""UAV-LANG: analizador léxico, sintáctico y semántico para perfiles de drones FPV.

Uso:
    python main.py perfil.uav                 # analiza y muestra árbol o errores
    python main.py perfil.uav --tokens        # lista también los tokens
    python main.py perfil.uav --derivacion    # reglas aplicadas (derivación izquierda)
    python main.py --teoria                   # AFD, PRIMERO/SIGUIENTE y tabla LL(1)
"""
import argparse
import sys
from dataclasses import dataclass, field

import lexico
import semantico
from gramatica import CONFLICTOS, NO_TERMINALES, PRIMERO, SIGUIENTE, TABLA
from lexico import Lexico
from sintactico import Parser

sys.setrecursionlimit(20000)  # el árbol de listas largas es profundo (por la derecha)


@dataclass
class Resultado:
    tokens: list
    errores: list = field(default_factory=list)
    arbol: object = None
    derivacion: list = field(default_factory=list)
    simbolos: dict = field(default_factory=dict)

    @property
    def valido(self):
        return not self.errores


def analizar_texto(texto: str) -> Resultado:
    """Tubería completa: léxico -> sintáctico -> semántico.

    Cada fase solo se ejecuta si la anterior no encontró errores, para no
    reportar errores en cascada que no son reales.
    """
    tokens, errores = Lexico(texto).tokenizar()
    res = Resultado(tokens, errores)
    if errores:
        return res
    parser = Parser(tokens)
    arbol = parser.analizar()
    res.derivacion = parser.derivacion
    if parser.errores:
        res.errores = parser.errores
        return res
    res.arbol = arbol
    res.simbolos, res.errores = semantico.analizar(arbol)
    return res


def _fmt(conjunto):
    return "{ " + ", ".join(sorted(conjunto)) + " }"


def imprimir_teoria():
    print("=== AFD (Fase 1) ===")
    for afd in lexico.AUTOMATAS:
        print(f"\n{afd.nombre}  (* = estado de aceptación)")
        print(afd.matriz())
    print("\n=== PRIMERO y SIGUIENTE (Fase 2) ===")
    for nt in NO_TERMINALES:
        print(f"⟨{nt}⟩\n    PRIMERO   = {_fmt(PRIMERO[nt])}\n    SIGUIENTE = {_fmt(SIGUIENTE[nt])}")
    print("\n=== Tabla de análisis predictivo LL(1) ===")
    for (nt, t), regla in sorted(TABLA.items(), key=lambda x: (x[1], x[0][1])):
        print(f"M[⟨{nt}⟩, {t}] = regla ({regla})")
    print("\nConflictos:", CONFLICTOS if CONFLICTOS else "ninguno -> la gramática es LL(1)")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

    ap = argparse.ArgumentParser(description="Analizador de perfiles UAV-LANG")
    ap.add_argument("archivo", nargs="?", help="archivo de texto con el perfil")
    ap.add_argument("--tokens", action="store_true", help="muestra la lista de tokens")
    ap.add_argument("--derivacion", action="store_true",
                    help="muestra las reglas aplicadas (derivación por la izquierda)")
    ap.add_argument("--teoria", action="store_true",
                    help="muestra AFD, PRIMERO/SIGUIENTE y la tabla LL(1)")
    args = ap.parse_args(argv)

    if args.teoria:
        imprimir_teoria()
        if not args.archivo:
            return 0
    if not args.archivo:
        ap.error("indique un archivo a analizar (o use --teoria)")

    try:
        with open(args.archivo, encoding="utf-8-sig") as f:
            texto = f.read()
    except OSError as e:
        print(f"No se pudo abrir '{args.archivo}': {e.strerror}", file=sys.stderr)
        return 2

    res = analizar_texto(texto)

    if args.tokens:
        print("=== Tokens ===")
        for t in res.tokens:
            print(f"{t.linea:>3}:{t.columna:<3} {t.tipo:<20} {t.lexema!r}")
        print()

    if args.derivacion and res.derivacion:
        print("=== Derivación por la izquierda (números de regla) ===")
        print(" ".join(f"({n})" for n in res.derivacion))
        print()

    if res.valido:
        print(f"PERFIL VÁLIDO: {args.archivo} (léxico, sintáctico y semántico)\n")
        print("=== Tabla de símbolos ===")
        for nombre, valor in res.simbolos.items():
            print(f"  {nombre:<15} = {valor}")
        print("\n=== Árbol de derivación sintáctica ===")
        print(res.arbol.dibujar())
        return 0

    print(f"{len(res.errores)} ERROR(ES) en {args.archivo}:\n")
    for e in res.errores:
        print(f"  {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
