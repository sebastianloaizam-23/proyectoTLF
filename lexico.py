"""Analizador léxico de UAV-LANG (Fase 1).

Implementa los cuatro AFD de la Fase 1 (identificadores, números, espacios y
saltos de línea) con sus matrices de transición. Las palabras reservadas NO
tienen autómata propio: se reconoce un identificador y luego se consulta el
diccionario PALABRAS_RESERVADAS (sección 4.5).
"""
import string

from tokens import (
    PALABRAS_RESERVADAS,
    TK_EOF,
    TK_IDENTIFICADOR,
    TK_NUMERO,
    TK_SALTO_LINEA,
    Error,
    Token,
)

LETRAS = set(string.ascii_letters)  # Σ_L: solo A-Z y a-z
DIGITOS = set(string.digits)        # Σ_N: 0-9


def clasificar(ch: str) -> str:
    """Clase de símbolo del alfabeto Σ usada en las matrices de transición."""
    if ch in LETRAS:
        return "L"
    if ch in DIGITOS:
        return "D"
    if ch == "_":
        return "_"
    if ch in " \t\r":  # espacio, tab (y \r, para archivos de Windows)
        return "E"
    if ch == "\n":
        return "LF"
    return "OTRO"


class AFD:
    """Autómata finito determinista M = (Q, Σ, δ, q0, F) con estado de rechazo qR."""

    RECHAZO = "qR"

    def __init__(self, nombre, estados, clases, delta, inicial, aceptacion):
        self.nombre = nombre
        self.estados = estados
        self.clases = clases
        self.delta = delta          # {estado: {clase: estado}}; lo no listado va a qR
        self.inicial = inicial
        self.aceptacion = set(aceptacion)

    def paso(self, estado: str, ch: str) -> str:
        if estado == self.RECHAZO:
            return self.RECHAZO
        return self.delta.get(estado, {}).get(clasificar(ch), self.RECHAZO)

    def reconocer(self, texto: str) -> bool:
        """True si el AFD acepta la cadena completa."""
        q = self.inicial
        for ch in texto:
            q = self.paso(q, ch)
            if q == self.RECHAZO:
                return False
        return q in self.aceptacion

    def prefijo_mas_largo(self, texto: str, pos: int = 0) -> int:
        """Longitud del prefijo más largo (desde pos) que el AFD acepta."""
        q, ultimo = self.inicial, 0
        for i in range(pos, len(texto)):
            q = self.paso(q, texto[i])
            if q == self.RECHAZO:
                break
            if q in self.aceptacion:
                ultimo = i - pos + 1
        return ultimo

    def matriz(self) -> str:
        """Matriz de transiciones en texto (para la sustentación)."""
        cols = self.clases + ["OTRO"]
        filas = [["Estado"] + cols]
        for q in self.estados + [self.RECHAZO]:
            filas.append([q + ("*" if q in self.aceptacion else "")]
                         + [self.paso(q, _EJEMPLO[c]) if q != self.RECHAZO
                            else self.RECHAZO for c in cols])
        ancho = [max(len(f[i]) for f in filas) for i in range(len(cols) + 1)]
        return "\n".join("  ".join(c.ljust(ancho[i]) for i, c in enumerate(f)) for f in filas)


# un carácter representante de cada clase (solo para imprimir matrices)
_EJEMPLO = {"L": "a", "D": "0", "_": "_", "E": " ", "LF": "\n", "OTRO": "@"}

# 4.1 Identificadores: L_ID = [A-Za-z][A-Za-z0-9_]*
AFD_ID = AFD("Identificadores", ["q0", "q1"], ["L", "D", "_"],
             {"q0": {"L": "q1"}, "q1": {"L": "q1", "D": "q1", "_": "q1"}},
             "q0", ["q1"])

# 4.2 Números enteros sin signo: ER_NUM = [0-9]+
AFD_NUM = AFD("Números enteros", ["q0", "q1"], ["D"],
              {"q0": {"D": "q1"}, "q1": {"D": "q1"}},
              "q0", ["q1"])

# 4.3 Espacios y tabuladores: ER_ESP = [espacio o tab]+
AFD_ESP = AFD("Espacios", ["q0", "q1"], ["E"],
              {"q0": {"E": "q1"}, "q1": {"E": "q1"}},
              "q0", ["q1"])

# 4.4 Salto de línea: ER_NL = \n  (exactamente uno)
AFD_NL = AFD("Saltos de línea", ["q0", "q1"], ["LF"],
             {"q0": {"LF": "q1"}},
             "q0", ["q1"])

AUTOMATAS = [AFD_ID, AFD_NUM, AFD_ESP, AFD_NL]


class Lexico:
    def __init__(self, texto: str):
        self.texto = texto

    def tokenizar(self):
        """Devuelve (tokens, errores). Los errores léxicos no detienen el escaneo."""
        texto, n = self.texto, len(self.texto)
        tokens, errores = [], []
        pos, linea, ini_linea = 0, 1, 0

        def error(msg, col, regla=None):
            errores.append(Error("Léxico", msg, linea, col, regla))

        while pos < n:
            c = texto[pos]
            col = pos - ini_linea + 1
            clase = clasificar(c)

            if clase == "E":  # TK_ESPACIO: se reconoce y se descarta
                pos += AFD_ESP.prefijo_mas_largo(texto, pos)

            elif clase == "LF":
                pos += AFD_NL.prefijo_mas_largo(texto, pos)
                # Saltos consecutivos (líneas en blanco) se colapsan en uno solo,
                # y no se emite ninguno antes de la primera instrucción.
                if tokens and tokens[-1].tipo != TK_SALTO_LINEA:
                    tokens.append(Token(TK_SALTO_LINEA, "\\n", linea, col))
                linea += 1
                ini_linea = pos

            elif clase in ("L", "D", "_"):
                # Se toma la palabra completa (letras, dígitos y '_') y se
                # decide qué AFD la acepta.
                j = pos
                while j < n and clasificar(texto[j]) in ("L", "D", "_"):
                    j += 1
                lexema = texto[pos:j]
                if AFD_ID.reconocer(lexema):
                    # Paso 2-4 de "¿Cómo se reconocen las palabras reservadas?"
                    tipo = PALABRAS_RESERVADAS.get(lexema.upper(), TK_IDENTIFICADOR)
                    tokens.append(Token(tipo, lexema, linea, col))
                elif AFD_NUM.reconocer(lexema):
                    tokens.append(Token(TK_NUMERO, lexema, linea, col))
                elif lexema[0] == "_":
                    error(f"Lexema inválido '{lexema}': un identificador no puede "
                          f"comenzar con guion bajo", col)
                else:
                    error(f"Lexema inválido '{lexema}': no es un identificador "
                          f"(no puede comenzar con un número) ni un entero", col)
                pos = j

            else:
                if c in "-+.":
                    error(f"Carácter no reconocido {c!r}: los valores deben ser "
                          f"enteros positivos, sin signo ni parte decimal", col, "RF06")
                else:
                    error(f"Carácter no reconocido {c!r}: no pertenece al alfabeto Σ",
                          col)
                pos += 1

        col = pos - ini_linea + 1
        if tokens and tokens[-1].tipo != TK_SALTO_LINEA:  # salto implícito antes de $
            tokens.append(Token(TK_SALTO_LINEA, "\\n", linea, col))
        tokens.append(Token(TK_EOF, "$", linea, col))
        return tokens, errores
