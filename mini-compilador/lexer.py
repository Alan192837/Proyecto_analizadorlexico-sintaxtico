# =============================================================================
# lexer.py — Analizador Léxico
# =============================================================================
# Responsabilidad: leer el texto fuente y convertirlo en una secuencia de
# tokens que el parser podrá consumir.
#
# Herramienta: PLY (Python Lex-Yacc) → módulo ply.lex
#
# PALABRAS RESERVADAS DEL LENGUAJE (NO usar como nombres de variable):
#   entero    → tipo entero          (equivale a int)
#   cadena    → tipo cadena de texto (equivale a string)
#   logico    → tipo booleano        (equivale a bool)
#   si        → condicional          (equivale a if)
#   sino      → rama alternativa     (equivale a else)
#   leer      → entrada de datos     (equivale a read/input)
#   mostrar   → salida de datos      (equivale a print)
#   verdadero → literal verdadero    (equivale a true)
#   falso     → literal falso        (equivale a false)
#   y         → operador AND lógico  ← RESERVADA, no usar como variable
#   o         → operador OR  lógico  ← RESERVADA, no usar como variable
#   no        → operador NOT lógico  ← RESERVADA, no usar como variable
#
# REGLA DE ORO:
#   Igual que en C/Java no puedes llamar a una variable "if", "int" o "while",
#   en este lenguaje no puedes usar "si", "y", "o", "no", etc. como variables.
#   Usa nombres descriptivos: eje_y, valor_a, bandera, resultado, etc.
# =============================================================================

import ply.lex as lex

# ---------------------------------------------------------------------------
# 1. PALABRAS RESERVADAS
#    Diccionario { texto_en_fuente -> tipo_de_token }
#    El lexer consulta esta tabla cada vez que reconoce un identificador.
# ---------------------------------------------------------------------------
reserved = {
    'entero'     : 'ENTERO',
    'cadena'     : 'CADENA_TIPO',
    'logico'     : 'LOGICO_TIPO',
    'si'         : 'SI',
    'sino'       : 'SINO',
    'leer'       : 'LEER',
    'mostrar'    : 'MOSTRAR',
    'verdadero'  : 'VERDADERO',
    'falso'      : 'FALSO',
    'y'          : 'Y',
    'o'          : 'O',
    'no'         : 'NO',
}

# ---------------------------------------------------------------------------
# 2. LISTA COMPLETA DE TOKENS
#    PLY exige esta variable con TODOS los tipos de token posibles.
# ---------------------------------------------------------------------------
tokens = [
    # Literales
    'NUMERO',           # 42
    'LITERAL_CADENA',   # "hola mundo"
    'ID',               # nombreVariable

    # Operadores aritmeticos
    'MAS',      # +
    'MENOS',    # -
    'POR',      # *
    'ENTRE',    # /

    # Operadores relacionales (2 chars antes que 1 char para evitar ambiguedad)
    'MAYOR_IG', # >=
    'MENOR_IG', # <=
    'IGUAL',    # ==
    'DISTINTO', # !=
    'MAYOR',    # >
    'MENOR',    # <

    # Asignacion
    'ASIGNAR',  # =

    # Puntuacion
    'PAR_IZQ',  # (
    'PAR_DER',  # )
    'LLA_IZQ',  # {
    'LLA_DER',  # }
    'PUNTOCOM', # ;
    'COMA',     # ,
] + list(reserved.values())


# ---------------------------------------------------------------------------
# 3. REGLAS SIMPLES — cadenas de patron (sin accion Python extra)
#    PLY las ordena de mayor a menor longitud automaticamente,
#    garantizando que ">=" se reconoce antes que ">".
# ---------------------------------------------------------------------------

# Relacionales 2 caracteres (deben definirse ANTES que los de 1 caracter)
t_MAYOR_IG  = r'>='
t_MENOR_IG  = r'<='
t_IGUAL     = r'=='
t_DISTINTO  = r'!='
# Relacionales 1 caracter
t_MAYOR     = r'>'
t_MENOR     = r'<'

# Aritmeticos
t_MAS       = r'\+'
t_MENOS     = r'-'
t_POR       = r'\*'
t_ENTRE     = r'/'

# Asignacion (despues de == para no confundirse)
t_ASIGNAR   = r'='

# Puntuacion
t_PAR_IZQ   = r'\('
t_PAR_DER   = r'\)'
t_LLA_IZQ   = r'\{'
t_LLA_DER   = r'\}'
t_PUNTOCOM  = r';'
t_COMA      = r','


# ---------------------------------------------------------------------------
# 4. REGLAS CON ACCION — requieren funcion Python
# ---------------------------------------------------------------------------

def t_NUMERO(t):
    r'\d+'
    # Convierte el texto "42" al entero Python 42
    t.value = int(t.value)
    return t


def t_LITERAL_CADENA(t):
    r'"[^"]*"'
    # Elimina las comillas: "hola" -> hola
    t.value = t.value[1:-1]
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # Si el identificador es una palabra reservada, cambia su tipo de token.
    # Ejemplo: el texto "si" produce token SI, no token ID.
    t.type = reserved.get(t.value, 'ID')
    return t


def t_COMENTARIO(t):
    r'//[^\n]*'
    # Los comentarios de linea se descartan; no producen ningun token.
    pass


def t_newline(t):
    r'\n+'
    # Actualiza el contador de lineas para mensajes de error precisos.
    t.lexer.lineno += len(t.value)


# Caracteres ignorados entre tokens
t_ignore = ' \t\r'


def t_error(t):
    """Caracter no reconocido: se reporta y se salta para intentar continuar."""
    print(f"[Lexico] Caracter ilegal '{t.value[0]}' en linea {t.lineno}")
    t.lexer.skip(1)


# ---------------------------------------------------------------------------
# 5. CONSTRUCCION DEL LEXER
# ---------------------------------------------------------------------------
lexer = lex.lex()


# ---------------------------------------------------------------------------
# 6. FUNCION DE UTILIDAD
#    Usa lexer.clone() para no consumir tokens que el parser necesitara.
#    Sin esto, llamar a tokenize() antes de parse() dejaria el parser sin tokens.
# ---------------------------------------------------------------------------
def tokenize(source_code: str, verbose: bool = True):
    """
    Tokeniza source_code con un clon del lexer (no afecta al parser).
    Si verbose=True imprime cada token en pantalla.
    Devuelve la lista de tokens.
    """
    lexer_clone = lexer.clone()
    lexer_clone.input(source_code)
    token_list = []
    for tok in lexer_clone:
        token_list.append(tok)
        if verbose:
            print(f"  Token({tok.type:15s}) -> {str(tok.value)!r:22} linea {tok.lineno}")
    return token_list
