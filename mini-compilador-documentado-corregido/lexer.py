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

    # ── Tokens de error semántico/léxico ──────────────────────────────────
    'ID_CON_ERROR',     # Identificador con caracteres ilegales, ej: ent@ro
    'CADENA_ERROR',     # Cadena abierta sin comilla de cierre, ej: "hola mundo

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
#
#    ORDEN IMPORTANTE en PLY:
#    Las funciones t_* se ordenan por longitud de su docstring (la regex).
#    Las reglas más específicas o largas deben ir primero para que PLY
#    no aplique una regla más corta antes de tiempo.
#    Por eso CADENA_ERROR y ID_CON_ERROR van antes de LITERAL_CADENA e ID.
# =============================================================================

def t_CADENA_ERROR(t):
    r'"[^"\n]*(?=\n|$)'
    """
    Cadena sin comilla de cierre — error léxico.

    Detecta una comilla de apertura seguida de contenido que llega hasta
    el fin de la línea actual sin encontrar la comilla de cierre.

    El patrón se compone de tres partes:
        "           → comilla de apertura obligatoria
        [^"\\n]*    → cualquier carácter EXCEPTO comilla y salto de línea;
                      esto es lo que realmente detiene el match en la línea
        (?=\\n|$)   → lookahead: confirma que lo que sigue es un salto de
                      línea o fin de texto, sin consumirlo

    Por qué [^"\\n]* es suficiente:
        PLY no activa re.MULTILINE, así que el ancla $ sola no garantiza
        detenerse en cada línea. Al excluir \\n del grupo de caracteres,
        el match termina naturalmente al llegar al salto de línea,
        sin arrastrarse a las líneas siguientes.

    Comportamiento:
        - Captura solo el renglón donde está la comilla sin cerrar.
        - Las líneas posteriores se siguen tokenizando con normalidad.
        - Guarda el contenido sin la comilla inicial como valor del token.
        - Reporta el error indicando línea y contenido.

    Parámetro:
        t: objeto LexToken de PLY
    Retorna:
        t (LexToken): tipo CADENA_ERROR, value = texto sin comilla inicial
    """
    # Conserva el contenido completo (sin la comilla inicial) como evidencia
    t.value = t.value[1:]
    print(f"[Lexico] Cadena sin cerrar en linea {t.lineno}: \"{t.value}")
    return t


def t_ID_CON_ERROR(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*(?:[^a-zA-Z0-9_\s\+\-\*\/\=\<\>\!\(\)\{\}\;\,\"\n][a-zA-Z0-9_]*)+'
    """
    CORRECCIÓN 2 — Identificador con caracteres ilegales intercalados.

    El problema original: cuando el lexer encontraba 'ent@ro', reconocía
    primero 'ent' como ID, luego '@' disparaba t_error (un carácter a la
    vez), y finalmente 'ro' como otro ID. Resultado: tres tokens separados.

    Esta regla captura TODO en una sola pasada:
        - Empieza igual que un ID normal: [a-zA-Z_][a-zA-Z0-9_]*
        - Continúa con grupos opcionales que incluyen UN carácter ilegal
          seguido de más caracteres alfanuméricos: (?:[carácter_ilegal][alnum]*)
        - El grupo se repite (*) para cubrir múltiples errores: en@t#ro

    Caracteres que se consideran "ilegales dentro de un ID":
        Cualquier cosa que NO sea: letras, dígitos, guion bajo, espacios,
        operadores reconocidos (+−*/=<>!), delimitadores ((){}),
        puntuación (;,") ni saltos de línea.
        Básicamente: @, #, $, %, ~, `, ^, &, |, ?, etc.

    Comportamiento:
        - Captura el lexema completo (ej. 'ent@ro') en un solo token.
        - Reporta el error indicando el símbolo ilegal encontrado.
        - Devuelve el token para que aparezca en .tok y .tab.

    Parámetro:
        t: objeto LexToken
    Retorna:
        t (LexToken): tipo ID_CON_ERROR, value = lexema completo (ej. 'ent@ro')
    """
    # Busca los caracteres ilegales dentro del lexema para incluirlos en el
    # mensaje de error. Un carácter es ilegal si no es alfanumérico ni guion bajo.
    import re
    ilegales = re.findall(r'[^a-zA-Z0-9_]', t.value)
    simbolos = ', '.join(f"'{c}'" for c in ilegales)
    print(f"[Lexico] Identificador con caracter(es) ilegal(es) {simbolos} "
          f"en linea {t.lineno}: '{t.value}'")
    return t


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

    NOTA: Esta regla solo aplica cuando la cadena SÍ tiene comilla de cierre.
    Si no la tiene, t_CADENA_ERROR la captura primero (tiene mayor prioridad
    por estar definida antes en el archivo).

    Parámetro:
        t: objeto LexToken
    Retorna:
        t (LexToken): con t.value sin las comillas (ej. "hola" → hola)
    """
    t.value = t.value[1:-1]
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    """
    Reconoce un identificador LIMPIO: empieza con letra o guion bajo,
    seguido solo de letras, dígitos o guiones bajos. Sin caracteres ilegales.

    Después de reconocerlo, verifica si coincide con una palabra reservada.
    Si sí, cambia el tipo de token para que el parser lo trate como palabra
    clave y no como nombre de variable.

    NOTA: Esta regla solo aplica cuando el identificador no contiene
    caracteres ilegales. Si los contiene, t_ID_CON_ERROR lo captura
    primero por tener un patrón más largo (PLY prefiere el match más largo).

    Ejemplos de comportamiento:
        'contador' → tipo ID          (variable normal)
        'si'       → tipo SI          (palabra reservada)
        'ent@ro'   → tipo ID_CON_ERROR (capturado por la regla anterior)

    Parámetro:
        t: objeto LexToken
    Retorna:
        t (LexToken): con t.type ajustado si es palabra reservada
    """
    t.type = reserved.get(t.value, 'ID')
    return t


def t_COMENTARIO(t):
    r'//[^\n]*'
    """
    Reconoce comentarios de línea al estilo C++: desde '//' hasta el fin
    de la línea. La función NO retorna el token, lo que hace que PLY
    descarte el comentario por completo.

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

    Parámetro:
        t: objeto LexToken con t.value = secuencia de '\\n'
    """
    t.lexer.lineno += len(t.value)
    # No retornamos t → PLY descarta los saltos de línea como tokens


# Caracteres que el lexer ignora completamente entre tokens.
t_ignore = ' \t\r'


def t_error(t):
    """
    CORRECCIÓN 1 — Manejador de error léxico mejorado.

    El manejador original solo imprimía un mensaje y avanzaba un carácter,
    lo que causaba que caracteres ilegales AISLADOS (no pegados a un ID)
    se perdieran y no aparecieran en .tok ni en .tab.

    Ahora se genera un token especial de tipo 'ERROR_LEXICO' con el
    carácter problemático como valor, y se retorna para que:
        - Aparezca en la lista de tokens de tokenize()
        - Se registre en .tok con la nota de error
        - Se registre en .tab con la nota de error

    Caracteres ilegales pegados a identificadores (ej: ent@ro) son
    capturados por t_ID_CON_ERROR ANTES de llegar aquí. Este manejador
    solo recibe caracteres verdaderamente aislados (ej: una @ sola).

    Parámetro:
        t: objeto LexToken donde t.value[0] es el carácter ilegal
    """
    # Captura solo el carácter ilegal como lexema del token de error
    t.type  = 'ERROR_LEXICO'
    t.value = t.value[0]
    print(f"[Lexico] Caracter ilegal '{t.value}' en linea {t.lineno}")
    # Avanza un carácter para continuar el análisis del resto del fuente
    t.lexer.skip(1)
    return t   # ← CLAVE: retornar el token para que aparezca en los reportes


# ERROR_LEXICO no puede estar en 'tokens' porque PLY no lo define como regla
# normal (viene de t_error). Lo agregamos manualmente para que los reportes
# en main.py puedan reconocerlo sin causar errores en el parser.
# El parser nunca lo verá porque el código con errores léxicos no llega
# a ejecutarse normalmente; pero sí debe aparecer en .tok y .tab.
tokens = list(tokens) + ['ERROR_LEXICO']


# =============================================================================
# 5. CONSTRUCCIÓN DEL LEXER
# =============================================================================
lexer = lex.lex()


# =============================================================================
# 6. FUNCIÓN DE UTILIDAD — tokenize()
# =============================================================================

def tokenize(source_code: str, verbose: bool = True):
    """
    Tokeniza el código fuente y opcionalmente imprime cada token.

    Usa un clon del lexer global para no interferir con el lexer que
    el parser consumirá posteriormente.

    Parámetros:
        source_code (str) : texto del programa a analizar
        verbose     (bool): si es True, imprime cada token en pantalla

    Retorna:
        token_list (list[LexToken]): lista de todos los tokens generados,
                                     incluyendo tokens de error (ID_CON_ERROR,
                                     CADENA_ERROR, ERROR_LEXICO) para que
                                     aparezcan en los reportes .tok y .tab
    """
    lexer_clone = lexer.clone()
    lexer_clone.input(source_code)

    token_list = []

    for tok in lexer_clone:
        token_list.append(tok)
        if verbose:
            print(f"  Token({tok.type:15s}) -> {str(tok.value)!r:22} linea {tok.lineno}")

    return token_list
