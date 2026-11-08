"""Tokens, palabras reservadas y estructuras comunes de UAV-LANG (Fase 1)."""
from dataclasses import dataclass
from typing import Optional

# --- Palabras reservadas (sección 4.5 de la Fase 1) -------------------------
# La búsqueda se hace con el lexema convertido a mayúsculas (RF11).
PALABRAS_RESERVADAS = {
    "INICIAR": "TK_INICIAR",
    "PERFIL": "TK_PERFIL",
    "MODO": "TK_MODO",
    "CONFIGURAR": "TK_CONFIGURAR",
    "SEGURIDAD": "TK_SEGURIDAD",
    "FAILSAFE": "TK_FAILSAFE",
    "RETURN": "TK_RETURN",
    "VALIDAR": "TK_VALIDAR",
    "FINALIZAR": "TK_FINALIZAR",
    "ACRO": "TK_ACRO",
    "ANGLE": "TK_ANGLE",
    "HORIZON": "TK_HORIZON",
    "ALTURA_MAX": "TK_ALTURA_MAX",
    "VELOCIDAD_MAX": "TK_VELOCIDAD_MAX",
    "BATERIA_MIN": "TK_BATERIA_MIN",
    "TASA_GIRO": "TK_TASA_GIRO",
    "POTENCIA_MOTOR": "TK_POTENCIA_MOTOR",
}

# --- Nombres de token (se usan como terminales de la gramática) -------------
TK_INICIAR = "TK_INICIAR"
TK_PERFIL = "TK_PERFIL"
TK_MODO = "TK_MODO"
TK_CONFIGURAR = "TK_CONFIGURAR"
TK_SEGURIDAD = "TK_SEGURIDAD"
TK_FAILSAFE = "TK_FAILSAFE"
TK_RETURN = "TK_RETURN"
TK_VALIDAR = "TK_VALIDAR"
TK_FINALIZAR = "TK_FINALIZAR"
TK_ACRO = "TK_ACRO"
TK_ANGLE = "TK_ANGLE"
TK_HORIZON = "TK_HORIZON"
TK_ALTURA_MAX = "TK_ALTURA_MAX"
TK_VELOCIDAD_MAX = "TK_VELOCIDAD_MAX"
TK_BATERIA_MIN = "TK_BATERIA_MIN"
TK_TASA_GIRO = "TK_TASA_GIRO"
TK_POTENCIA_MOTOR = "TK_POTENCIA_MOTOR"
TK_IDENTIFICADOR = "TK_IDENTIFICADOR"
TK_NUMERO = "TK_NUMERO"
TK_SALTO_LINEA = "TK_SALTO_LINEA"
TK_EOF = "$"

# Orden establecido de los parámetros (RF05)
ORDEN_PARAMETROS = [
    TK_ALTURA_MAX,
    TK_VELOCIDAD_MAX,
    TK_BATERIA_MIN,
    TK_TASA_GIRO,
    TK_POTENCIA_MOTOR,
]

# Orden de presentación de los tokens en los mensajes de error
ORDEN_TOKENS = list(PALABRAS_RESERVADAS.values()) + [
    TK_IDENTIFICADOR,
    TK_NUMERO,
    TK_SALTO_LINEA,
    TK_EOF,
]


def nombre_parametro(tipo_token: str) -> str:
    """TK_ALTURA_MAX -> ALTURA_MAX"""
    return tipo_token[3:]


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    linea: int
    columna: int


@dataclass
class Error:
    fase: str  # "Léxico" | "Sintáctico" | "Semántico"
    mensaje: str
    linea: int
    columna: int
    regla: Optional[str] = None  # RF01..RF12 cuando aplica

    def __str__(self) -> str:
        r = f" ({self.regla})" if self.regla else ""
        return f"[{self.fase}] línea {self.linea}, col {self.columna}: {self.mensaje}{r}"
