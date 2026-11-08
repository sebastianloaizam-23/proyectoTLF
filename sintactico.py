"""Analizador sintáctico de UAV-LANG (Fase 2 -> Fase 3).

Parser descendente recursivo predictivo LL(1): una función por cada no
terminal de la gramática final. Las decisiones entre alternativas se toman
consultando la tabla de análisis predictivo (gramatica.TABLA).

Recuperación de errores: como cada instrucción ocupa una línea, ante un error
se descarta el resto de la línea (modo pánico con TK_SALTO_LINEA como token de
sincronización) y se continúa, para poder reportar varios errores.
"""
from gramatica import POSTERIORES, PRIMERO, TABLA
from tokens import (
    ORDEN_TOKENS, PALABRAS_RESERVADAS, TK_ACRO, TK_CONFIGURAR, TK_EOF,
    TK_FAILSAFE, TK_FINALIZAR, TK_IDENTIFICADOR, TK_INICIAR, TK_MODO,
    TK_NUMERO, TK_PERFIL, TK_RETURN, TK_SALTO_LINEA, TK_SEGURIDAD, TK_VALIDAR,
    Error,
)

TOKENS_RESERVADOS = set(PALABRAS_RESERVADAS.values())


class Nodo:
    """Nodo del árbol de derivación sintáctica."""

    def __init__(self, nombre, token=None):
        self.nombre = nombre      # "⟨inicio⟩", "TK_PERFIL", "ε"
        self.token = token        # solo en hojas terminales
        self.hijos = []
        self.regla = None         # número de producción aplicada
        self.faltante = False     # la instrucción no apareció
        self.error = False        # hubo un error dentro de la instrucción

    def agregar(self, hijo):
        self.hijos.append(hijo)
        return hijo

    def marcar_faltante(self):
        self.faltante = True
        return self

    def etiqueta(self):
        if self.token is not None:
            if self.token.tipo == TK_SALTO_LINEA:
                return self.nombre
            return f'{self.nombre}  "{self.token.lexema}"'
        if self.regla is not None:
            return f"{self.nombre}  ({self.regla})"
        return self.nombre

    def recorrer(self):
        """Recorrido en preorden, sin recursión."""
        pila = [self]
        while pila:
            n = pila.pop()
            yield n
            pila.extend(reversed(n.hijos))

    def primer_token(self):
        for n in self.recorrer():
            if n.token is not None:
                return n.token
        return None

    def dibujar(self):
        lineas = [self.etiqueta()]
        self._dibujar_hijos("", lineas)
        return "\n".join(lineas)

    def _dibujar_hijos(self, prefijo, salida):
        for i, h in enumerate(self.hijos):
            ultimo = i == len(self.hijos) - 1
            salida.append(prefijo + ("└── " if ultimo else "├── ") + h.etiqueta())
            h._dibujar_hijos(prefijo + ("    " if ultimo else "│   "), salida)


class _Abortar(Exception):
    """Señal interna: la instrucción actual tiene un error ya registrado."""


def _ordenar(tokens):
    return sorted(tokens, key=lambda t: ORDEN_TOKENS.index(t) if t in ORDEN_TOKENS else 99)


def _lista(tokens):
    t = _ordenar(tokens)
    if len(t) == 1:
        return t[0]
    return ", ".join(t[:-1]) + " o " + t[-1]


def _describir(t):
    if t.tipo == TK_SALTO_LINEA:
        return "TK_SALTO_LINEA (fin de línea)"
    if t.tipo == TK_EOF:
        return "fin de archivo ($)"
    return f"{t.tipo} '{t.lexema}'"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errores = []
        self.derivacion = []        # números de regla en orden de derivación izquierda
        self._eof_reportado = False

    # ------------------------------------------------------------------ utilidades
    @property
    def tok(self):
        return self.tokens[self.pos]

    def _avanzar(self):
        t = self.tokens[self.pos]
        if t.tipo != TK_EOF:
            self.pos += 1
        return t

    def _regla(self, n):
        self.derivacion.append(n)

    def _al_inicio_de_linea(self, i):
        return i == 0 or self.tokens[i - 1].tipo == TK_SALTO_LINEA

    def _hay_adelante(self, primeros):
        """¿Hay más adelante una instrucción que comience con alguno de 'primeros'?"""
        for i in range(self.pos + 1, len(self.tokens)):
            if self.tokens[i].tipo in primeros and self._al_inicio_de_linea(i):
                return True
        return False

    def _sugerencia(self, t, esperados):
        if t.tipo == TK_IDENTIFICADOR and "_" in t.lexema:
            partes = t.lexema.upper().split("_")
            if len(partes) > 1 and all(p in PALABRAS_RESERVADAS for p in partes):
                return (f"las palabras reservadas deben ir separadas por espacios; "
                        f"'{t.lexema}' se lee como un único identificador "
                        f"(¿quiso escribir '{' '.join(partes)}'?)")
        if TK_IDENTIFICADOR in esperados and t.tipo in TOKENS_RESERVADOS:
            return f"'{t.lexema}' es una palabra reservada y no puede usarse como identificador"
        return None

    def _error(self, mensaje, t, regla=None):
        if t.tipo == TK_EOF:  # un solo error por "faltan cosas al final del archivo"
            if self._eof_reportado:
                return
            self._eof_reportado = True
        self.errores.append(Error("Sintáctico", mensaje, t.linea, t.columna, regla))

    def _error_esperado(self, esperados, t, regla=None):
        msg = f"Se esperaba {_lista(esperados)}, se encontró {_describir(t)}"
        extra = self._sugerencia(t, esperados)
        if extra:
            msg += f". Sugerencia: {extra}"
        self._error(msg, t, regla)

    def _saltar_linea(self):
        """Modo pánico: descarta hasta el siguiente TK_SALTO_LINEA (inclusive)."""
        while self.tok.tipo not in (TK_SALTO_LINEA, TK_EOF):
            self._avanzar()
        if self.tok.tipo == TK_SALTO_LINEA:
            self._avanzar()

    def _m(self, nodo, tipo, regla=None):
        """match: consume el token 'tipo' o registra el error y aborta la línea."""
        t = self.tok
        if t.tipo == tipo:
            nodo.agregar(Nodo(tipo, self._avanzar()))
            return
        self._error_esperado({tipo}, t, regla)
        raise _Abortar()

    def _entrada(self, simbolo, rf=None):
        """Verifica que la línea actual comience con PRIMERO(simbolo).

        Si no, registra el error una vez y decide: si la línea actual pertenece a
        una instrucción POSTERIOR (y la esperada no aparece más adelante) la
        instrucción esperada simplemente falta; en otro caso la línea está fuera
        de lugar y se descarta. Devuelve True si se debe analizar la instrucción.
        """
        primeros, posteriores = PRIMERO[simbolo], POSTERIORES[simbolo]
        reportado = False
        while True:
            t = self.tok
            if t.tipo in primeros:
                return True
            if not reportado:
                regla = rf.get(t.tipo) if isinstance(rf, dict) else rf
                self._error_esperado(primeros, t, regla)
                reportado = True
            if t.tipo == TK_EOF:
                return False
            if t.tipo in posteriores and not self._hay_adelante(primeros):
                return False
            self._saltar_linea()

    # ------------------------------------------------------------------ gramática
    def analizar(self):
        arbol = self.programa()
        if self.tok.tipo != TK_EOF:
            self._error(f"Se encontró {_describir(self.tok)} después de FINALIZAR PERFIL: "
                        f"no se permiten instrucciones fuera de la estructura del perfil",
                        self.tok, "RF10")
        return arbol

    # (1) <programa> ::= <inicio> <modo> <lista_config> <seguridad> <validar> <fin>
    def programa(self):
        n = Nodo("⟨programa⟩")
        n.regla = 1
        self._regla(1)
        n.agregar(self.inicio())
        n.agregar(self.modo())
        n.agregar(self.lista_config())
        n.agregar(self.seguridad())
        n.agregar(self.validar())
        n.agregar(self.fin())
        return n

    # (2) <inicio> ::= TK_INICIAR TK_PERFIL TK_IDENTIFICADOR TK_SALTO_LINEA
    def inicio(self):
        n = Nodo("⟨inicio⟩")
        if not self._entrada("inicio", "RF01"):
            return n.marcar_faltante()
        n.regla = 2
        self._regla(2)
        try:
            self._m(n, TK_INICIAR)
            self._m(n, TK_PERFIL)
            self._m(n, TK_IDENTIFICADOR, "RF02")
            self._m(n, TK_SALTO_LINEA)
        except _Abortar:
            n.error = True
            self._saltar_linea()
        return n

    # (3) <modo> ::= TK_MODO <tipo_modo> TK_SALTO_LINEA
    def modo(self):
        n = Nodo("⟨modo⟩")
        if not self._entrada("modo", "RF03"):
            return n.marcar_faltante()
        n.regla = 3
        self._regla(3)
        try:
            self._m(n, TK_MODO)
            n.agregar(self.tipo_modo())
            self._m(n, TK_SALTO_LINEA)
        except _Abortar:
            n.error = True
            self._saltar_linea()
        return n

    # (4)-(6) <tipo_modo> ::= TK_ACRO | TK_ANGLE | TK_HORIZON
    def tipo_modo(self):
        n = Nodo("⟨tipo_modo⟩")
        t = self.tok
        regla = TABLA.get(("tipo_modo", t.tipo))
        if regla is None:
            self._error_esperado(PRIMERO["tipo_modo"], t, "RF03")
            raise _Abortar()
        n.regla = regla
        self._regla(regla)
        n.agregar(Nodo(t.tipo, self._avanzar()))
        return n

    # (7) <lista_config> ::= <config> <lista_config'>
    def lista_config(self):
        n = Nodo("⟨lista_config⟩")
        if not self._entrada("lista_config", {TK_MODO: "RF03", TK_VALIDAR: "RF08"}):
            return n.marcar_faltante()
        n.regla = 7
        self._regla(7)
        n.agregar(self.config())
        n.agregar(self.lista_config_p())
        return n

    # (8) <lista_config'> ::= <config> <lista_config'>   (9) | ε
    # Se implementa con un ciclo (la recursión es por la derecha) para que un
    # archivo con miles de instrucciones no agote la pila de Python.
    def lista_config_p(self):
        raiz = actual = Nodo("⟨lista_config'⟩")
        while True:
            t = self.tok
            regla = TABLA.get(("lista_config'", t.tipo))
            fuera = t.tipo in POSTERIORES["lista_config"]
            if regla == 8:
                actual.regla = 8
                self._regla(8)
                actual.agregar(self.config())
                actual = actual.agregar(Nodo("⟨lista_config'⟩"))
            elif (regla == 9 or t.tipo == TK_EOF
                  or (fuera and not self._hay_adelante({TK_CONFIGURAR}))):
                # ε: la instrucción siguiente (si falta) la reporta su propia función
                actual.regla = 9
                self._regla(9)
                actual.agregar(Nodo("ε"))
                return raiz
            else:
                esperados = PRIMERO["config"] | {TK_SEGURIDAD}
                self._error_esperado(esperados, t,
                                     {TK_MODO: "RF03", TK_VALIDAR: "RF08"}.get(t.tipo))
                self._saltar_linea()

    # (10) <config> ::= TK_CONFIGURAR <parametro> TK_NUMERO TK_SALTO_LINEA
    def config(self):
        n = Nodo("⟨config⟩")
        n.regla = 10
        self._regla(10)
        try:
            self._m(n, TK_CONFIGURAR)
            n.agregar(self.parametro())
            self._m(n, TK_NUMERO)
            self._m(n, TK_SALTO_LINEA)
        except _Abortar:
            n.error = True
            self._saltar_linea()
        return n

    # (11)-(15) <parametro> ::= TK_ALTURA_MAX | TK_VELOCIDAD_MAX | ...
    def parametro(self):
        n = Nodo("⟨parametro⟩")
        t = self.tok
        regla = TABLA.get(("parametro", t.tipo))
        if regla is None:
            self._error_esperado(PRIMERO["parametro"], t)
            raise _Abortar()
        n.regla = regla
        self._regla(regla)
        n.agregar(Nodo(t.tipo, self._avanzar()))
        return n

    # (16) <seguridad> ::= TK_SEGURIDAD TK_FAILSAFE TK_RETURN TK_SALTO_LINEA
    def seguridad(self):
        n = Nodo("⟨seguridad⟩")
        if not self._entrada("seguridad", "RF07"):
            return n.marcar_faltante()
        n.regla = 16
        self._regla(16)
        try:
            self._m(n, TK_SEGURIDAD)
            self._m(n, TK_FAILSAFE, "RF07")
            self._m(n, TK_RETURN, "RF07")
            self._m(n, TK_SALTO_LINEA)
        except _Abortar:
            n.error = True
            self._saltar_linea()
        return n

    # (17) <validar> ::= TK_VALIDAR TK_PERFIL TK_SALTO_LINEA
    def validar(self):
        n = Nodo("⟨validar⟩")
        if not self._entrada("validar", "RF08"):
            return n.marcar_faltante()
        n.regla = 17
        self._regla(17)
        try:
            self._m(n, TK_VALIDAR)
            self._m(n, TK_PERFIL, "RF08")
            self._m(n, TK_SALTO_LINEA)
        except _Abortar:
            n.error = True
            self._saltar_linea()
        return n

    # (18) <fin> ::= TK_FINALIZAR TK_PERFIL TK_SALTO_LINEA
    def fin(self):
        n = Nodo("⟨fin⟩")
        if not self._entrada("fin", "RF09"):
            return n.marcar_faltante()
        n.regla = 18
        self._regla(18)
        try:
            self._m(n, TK_FINALIZAR)
            self._m(n, TK_PERFIL, "RF09")
            self._m(n, TK_SALTO_LINEA)
        except _Abortar:
            n.error = True
            self._saltar_linea()
        return n
