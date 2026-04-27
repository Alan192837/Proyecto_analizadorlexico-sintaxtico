"""
=============================================================================
lexer.py — Analizador Léxico (Tokenizador)
=============================================================================
Propósito general:
    Convierte el texto fuente (una cadena de caracteres) en una secuencia
    ordenada de TOKENS que el parser puede consumir.

    Un token es la unidad mínima con significado dentro del lenguaje:
    un número, una palabra reservada, un operador, un delimitador, etc.

    Este módulo implementa la PRIMERA FASE de la compilación/interpretación:
        Texto fuente  →  [Lexer]  →  Lista de tokens  →  [Parser]

Herramienta utilizada:
    PLY (Python Lex-Yacc) — módulo ply.lex.
    PLY espera que este archivo defina las variables 'tokens' y las
    reglas t_* siguiendo convenciones de nombre específicas.

PALABRAS RESERVADAS DEL LENGUAJE (NO usar como nombres de variable):
    entero    → tipo entero          (equivale a int)
    cadena    → tipo cadena de texto (equivale a string)
    logico    → tipo booleano        (equivale a bool)
    si        → condicional          (equivale a if)
    sino      → rama alternativa     (equivale a else)
    leer      → entrada de datos     (equivale a read / input)
    mostrar   → salida de datos      (equivale a print)
    verdadero → literal verdadero    (equivale a True)
    falso     → literal falso        (equivale a False)
    y         → operador AND lógico
    o         → operador OR  lógico
    no        → operador NOT lógico

REGLA DE ORO — igual que en C/Java no puedes nombrar una variable "if"
o "int", en este lenguaje no puedes usar "si", "y", "o", "no", etc.
Usa nombres descriptivos: eje_y, valor_a, bandera, resultado, etc.
=============================================================================
"""

import ply.lex as lex   # Biblioteca PLY para construcción de lexers


# =============================================================================
# 1. PALABRAS RESERVADAS
#    Diccionario que mapea texto del fuente → tipo de token.
#    Cada vez que el lexer reconoce un identificador (secuencia de letras),
#    consulta este diccionario: si la palabra está aquí, produce el token
#    reservado; de lo contrario, produce un token ID (identificador normal).
# =============================================================================
reserved = {
    'entero'     : 'ENTERO',       # Tipo de dato entero
    'cadena'     : 'CADENA_TIPO',  # Tipo de dato cadena (alias para no chocar con LITERAL_CADENA)
    'logico'     : 'LOGICO_TIPO',  # Tipo de dato lógico/booleano
    'si'         : 'SI',           # Inicio de condicional
    'sino'       : 'SINO',         # Rama alternativa del condicional
    'leer'       : 'LEER',         # Sentencia de entrada
    'mostrar'    : 'MOSTRAR',      # Sentencia de salida
    'verdadero'  : 'VERDADERO',    # Literal booleano verdadero
    'falso'      : 'FALSO',        # Literal booleano falso
    'y'          : 'Y',            # Operador AND lógico
    'o'          : 'O',            # Operador OR  lógico
    'no'         : 'NO',           # Operador NOT lógico
}


# =============================================================================
# 2. LISTA COMPLETA DE TOKENS
#    PLY exige que exista una variable llamada exactamente 'tokens' con
#    TODOS los tipos de token que el lexer puede producir, incluyendo los
#    reservados. El parser importa esta misma lista para saber qué tokens
#    puede recibir.
# =============================================================================
tokens = [
    # ── Literales ─────────────────────────────────────────────────────────
    'NUMERO',           # Número entero, ej: 42
    'LITERAL_CADENA',   # Cadena entre comillas, ej: "hola mundo"
    'ID',               # Identificador de variable, ej: miContador

    # ── Operadores aritméticos ─────────────────────────────────────────────
    'MAS',      # Suma:        +
    'MENOS',    # Resta:       -
    'POR',      # Multiplicación: *
    'ENTRE',    # División:    /

    # ── Operadores relacionales ────────────────────────────────────────────
    # Los de 2 caracteres deben reconocerse ANTES que los de 1 caracter para
    # evitar que '>=' se tokenice como '>' seguido de '='.
    'MAYOR_IG', # Mayor o igual: >=
    'MENOR_IG', # Menor o igual: <=
    'IGUAL',    # Igualdad:      ==
    'DISTINTO', # Desigualdad:   !=
    'MAYOR',    # Mayor que:     >
    'MENOR',    # Menor que:     <

    # ── Asignación ────────────────────────────────────────────────────────
    'ASIGNAR',  # Operador de asignación: =  (distinto de IGUAL '==')

    # ── Puntuación / delimitadores ────────────────────────────────────────
    'PAR_IZQ',  # Paréntesis izquierdo:  (
    'PAR_DER',  # Paréntesis derecho:    )
    'LLA_IZQ',  # Llave izquierda:       {
    'LLA_DER',  # Llave derecha:         }
    'PUNTOCOM', # Fin de sentencia:      ;
    'COMA',     # Separador (reservado para futuras expansiones): ,

] + list(reserved.values())   # Agrega los tokens de palabras reservadas al final


# =============================================================================
# 3. REGLAS SIMPLES — expresiones regulares como cadenas
#    PLY detecta estas variables por su prefijo 't_' y las usa directamente
#    como patrones de expresión regular para reconocer tokens.
#    Las cadenas simples se ordenan automáticamente de mayor a menor
#    longitud, garantizando que '>=' se reconoce antes que '>'.
# =============================================================================

# Relacionales de 2 caracteres — deben definirse antes de los de 1 caracter
t_MAYOR_IG  = r'>='    # Patrón para >=
t_MENOR_IG  = r'<='    # Patrón para <=
t_IGUAL     = r'=='    # Patrón para == (igualdad, no asignación)
t_DISTINTO  = r'!='    # Patrón para !=

# Relacionales de 1 caracter
t_MAYOR     = r'>'
t_MENOR     = r'<'

# Operadores aritméticos
t_MAS       = r'\+'    # El '+' debe escaparse en regex porque es cuantificador
t_MENOS     = r'-'
t_POR       = r'\*'   # El '*' también es un cuantificador en regex
t_ENTRE     = r'/'

# Asignación — se define DESPUÉS de '==' para que PLY intente primero '=='
t_ASIGNAR   = r'='

# Puntuación
t_PAR_IZQ   = r'\('   # '(' se escapa porque tiene significado especial en regex
t_PAR_DER   = r'\)'
t_LLA_IZQ   = r'\{'
t_LLA_DER   = r'\}'
t_PUNTOCOM  = r';'
t_COMA      = r','


# =============================================================================
# 4. REGLAS CON ACCIÓN — requieren función Python
#    Se usan cuando, además de reconocer el patrón, hay que transformar
#    el valor del token o actualizar estado interno del lexer.
# =============================================================================

def t_NUMERO(t):
    r'\d+'
    """
    Reconoce una secuencia de uno o más dígitos y convierte el texto
    al tipo Python int para que el intérprete pueda operar directamente
    con él sin necesidad de conversión posterior.

    Parámetro:
        t: objeto LexToken de PLY con atributos type, value, lineno, lexpos
    Retorna:
        t (LexToken): con t.value convertido a int
    """
    # Convierte el texto reconocido (ej. "42") al entero Python equivalente
    t.value = int(t.value)
    return t


def t_LITERAL_CADENA(t):
    r'"[^"]*"'
    """
    Reconoce una cadena entre comillas dobles, sin permitir saltos de
    línea dentro de ella (el patrón [^"]* excluye comillas pero acepta
    cualquier otro carácter).

    La acción elimina las comillas delimitadoras para que el valor del
    token sea el contenido puro de la cadena.

    Parámetro:
        t: objeto LexToken
    Retorna:
        t (LexToken): con t.value sin las comillas (ej. "hola" → hola)
    """
    # Quita la comilla inicial [0] y la comilla final [-1]
    t.value = t.value[1:-1]
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    """
    Reconoce un identificador: empieza con letra o guion bajo, seguido
    de letras, dígitos o guiones bajos.

    Después de reconocerlo, verifica si coincide con una palabra reservada.
    Si sí, cambia el tipo de token para que el parser lo trate como palabra
    clave y no como nombre de variable.

    Ejemplos de comportamiento:
        'contador' → tipo ID      (variable normal)
        'si'       → tipo SI      (palabra reservada)
        'y'        → tipo Y       (operador lógico reservado)

    Parámetro:
        t: objeto LexToken
    Retorna:
        t (LexToken): con t.type ajustado si es palabra reservada
    """
    # Busca el texto en el diccionario de reservadas; si no está, devuelve 'ID'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_COMENTARIO(t):
    r'//[^\n]*'
    """
    Reconoce comentarios de línea al estilo C++: desde '//' hasta el fin
    de la línea. La función NO retorna el token (simplemente termina sin
    'return t'), lo que hace que PLY descarte el comentario por completo.

    Los comentarios no producen ningún token; son invisibles para el parser.

    Parámetro:
        t: objeto LexToken (descartado implícitamente al no retornarlo)
    """
    pass   # No retornar nada = descartar el token


def t_newline(t):
    r'\n+'
    """
    Reconoce uno o más saltos de línea y actualiza el contador de líneas
    del lexer. Este contador es fundamental para que los mensajes de error
    indiquen la línea exacta del problema en el código fuente.

    Nota: los saltos de línea NO generan token; solo actualizan el contador.

    Parámetro:
        t: objeto LexToken con t.value = secuencia de '\\n'
    """
    # len(t.value) cuenta cuántos saltos de línea hay en el match actual
    # (puede ser más de uno si hay líneas en blanco consecutivas)
    t.lexer.lineno += len(t.value)
    # No retornamos t → PLY descarta los saltos de línea como tokens


# Caracteres que el lexer ignora completamente entre tokens.
# Incluye espacio, tabulación y retorno de carro (Windows \r).
t_ignore = ' \t\r'


def t_error(t):
    """
    Manejador de error léxico: se invoca cuando el lexer encuentra un
    carácter que no encaja con ninguna regla definida.

    Estrategia de recuperación: reportar el carácter problemático e
    intentar continuar (skip(1) avanza un carácter para no entrar en
    un bucle infinito).

    Parámetro:
        t: objeto LexToken donde t.value[0] es el carácter ilegal
    """
    print(f"[Lexico] Caracter ilegal '{t.value[0]}' en linea {t.lineno}")
    # Avanza un carácter para que el lexer intente recuperarse
    # y continúe tokenizando el resto del fuente
    t.lexer.skip(1)


# =============================================================================
# 5. CONSTRUCCIÓN DEL LEXER
#    lex.lex() escanea el módulo actual, recopila todas las reglas t_* y
#    construye el autómata finito determinista (DFA) que realiza el análisis.
#    Debe llamarse una vez al importar el módulo.
# =============================================================================
lexer = lex.lex()


# =============================================================================
# 6. FUNCIÓN DE UTILIDAD — tokenize()
#    Expone el lexer al resto del sistema de forma segura, usando un clon
#    para no consumir los tokens que el parser necesitará después.
#
#    Sin lexer.clone():
#        Si alguien llamara tokenize() antes de parse(), el lexer interno
#        quedaría al final del texto y parse() no vería ningún token.
#    Con lexer.clone():
#        Cada llamada obtiene una copia independiente; el lexer original
#        permanece intacto y disponible para el parser.
# =============================================================================

def tokenize(source_code: str, verbose: bool = True):
    """
    Tokeniza el código fuente y opcionalmente imprime cada token.

    Usa un clon del lexer global para no interferir con el lexer que
    el parser consumirá posteriormente.

    Parámetros:
        source_code (str) : texto del programa a analizar
        verbose     (bool): si es True, imprime cada token en pantalla;
                            útil para depuración (flag --tokens en main.py)

    Retorna:
        token_list (list[LexToken]): lista de todos los tokens generados,
                                     en el orden en que aparecen en el fuente
    """
    # Crea una copia independiente del lexer para esta tokenización
    lexer_clone = lexer.clone()

    # Entrega el texto fuente al clon para que lo analice
    lexer_clone.input(source_code)

    token_list = []   # Acumula los tokens reconocidos

    # Itera sobre todos los tokens hasta que el clon llegue al final del fuente
    for tok in lexer_clone:
        token_list.append(tok)
        if verbose:
            # Formato tabular: tipo del token, valor y número de línea
            print(f"  Token({tok.type:15s}) -> {str(tok.value)!r:22} linea {tok.lineno}")

    return token_list