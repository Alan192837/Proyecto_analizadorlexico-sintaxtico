"""
=============================================================================
parser.py — Analizador Sintáctico (Parser)
=============================================================================
Propósito general:
    Consume la secuencia de tokens producida por el lexer y, siguiendo las
    reglas de la gramática del lenguaje, construye el Árbol de Sintaxis
    Abstracta (AST) que el intérprete ejecutará.

    Este módulo implementa la SEGUNDA FASE de la compilación/interpretación:
        Lista de tokens  →  [Parser]  →  AST (nodo Program)  →  [Intérprete]

Herramienta utilizada:
    PLY (Python Lex-Yacc) — módulo ply.yacc.

    PLY genera un parser LALR(1) a partir de las funciones cuyas docstrings
    contienen reglas de gramática en notación BNF.

GRAMÁTICA COMPLETA DEL LENGUAJE (notación BNF en español):

    programa      → lista_sentencias

    lista_sent    → lista_sentencias sentencia   (iteración a izquierda)
                  | sentencia

    sentencia     → declaracion
                  | asignacion
                  | mostrar_stmt
                  | leer_stmt
                  | si_stmt

    declaracion   → tipo ID ASIGNAR expr PUNTOCOM
    asignacion    → ID ASIGNAR expr PUNTOCOM
    mostrar_stmt  → MOSTRAR PAR_IZQ expr PAR_DER PUNTOCOM
    leer_stmt     → LEER PAR_IZQ ID PAR_DER PUNTOCOM
    si_stmt       → SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sent LLA_DER
                  | SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sent LLA_DER
                    SINO LLA_IZQ lista_sent LLA_DER

    tipo          → ENTERO | CADENA_TIPO | LOGICO_TIPO

    expr          → expr O expr_y | expr_y
    expr_y        → expr_y Y expr_no | expr_no
    expr_no       → NO expr_no | expr_rel
    expr_rel      → expr_arit OP_REL expr_arit | expr_arit
    expr_arit     → expr_arit MAS termino
                  | expr_arit MENOS termino
                  | termino
    termino       → termino POR factor
                  | termino ENTRE factor
                  | factor
    factor        → NUMERO | LITERAL_CADENA | VERDADERO | FALSO | ID
                  | PAR_IZQ expr PAR_DER
                  | MENOS factor   %prec UMENOS

La jerarquía expr → expr_y → expr_no → expr_rel → expr_arit → termino → factor
establece la PRECEDENCIA de operadores de menor a mayor:
    OR  <  AND  <  NOT  <  relacional  <  suma/resta  <  mult/div  <  átomo
=============================================================================
"""

import ply.yacc as yacc

# PLY requiere que 'tokens' esté en el scope de este módulo para construir
# el parser; por eso se importa directamente desde el lexer.
from lexer import tokens, lexer

# Importa todas las clases de nodos del AST para construirlas en las acciones
from ast_nodes import *


# =============================================================================
# 1. PRECEDENCIA Y ASOCIATIVIDAD DE OPERADORES
#    Resuelve los conflictos shift/reduce que surgen en gramáticas ambiguas.
#    Las reglas están ordenadas de MENOR a MAYOR precedencia (la última
#    tupla tiene la precedencia más alta).
#    La asociatividad determina cómo se agrupan operadores del mismo nivel:
#        'left'  → agrupa a la izquierda: a+b+c = (a+b)+c
#        'right' → agrupa a la derecha:   a=b=c = a=(b=c)
# =============================================================================
precedence = (
    ('left',  'O'),                                          # Menor precedencia: OR
    ('left',  'Y'),                                          # AND
    ('right', 'NO'),                                         # NOT (unario, agrupa a derecha)
    ('left',  'IGUAL', 'DISTINTO'),                          # Igualdad/desigualdad
    ('left',  'MENOR', 'MAYOR', 'MENOR_IG', 'MAYOR_IG'),    # Comparaciones
    ('left',  'MAS', 'MENOS'),                               # Suma y resta
    ('left',  'POR', 'ENTRE'),                               # Multiplicación y división
    ('right', 'UMENOS'),   # Mayor precedencia: menos unario (pseudo-token, no viene del lexer)
)
# Nota sobre UMENOS: no es un token real que produzca el lexer; es un
# marcador de precedencia que usamos en la regla del menos unario (%prec UMENOS)
# para decirle a PLY que esa producción tiene la misma precedencia que UMENOS.


# =============================================================================
# 2. REGLA RAÍZ — punto de entrada de la gramática
#    PLY comienza el análisis por la primera función p_* definida.
# =============================================================================

def p_programa(p):
    """programa : lista_sentencias"""
    # p[1] es la lista de nodos ASTNode construida por lista_sentencias
    # Empaqueta esa lista en el nodo raíz Program
    p[0] = Program(statements=p[1])


# =============================================================================
# 3. LISTA DE SENTENCIAS
#    Se implementa con recursión a izquierda para que PLY la maneje
#    eficientemente con LALR(1) y para que el orden de ejecución sea
#    el orden de aparición en el fuente.
# =============================================================================

def p_lista_sentencias_multiple(p):
    """lista_sentencias : lista_sentencias sentencia"""
    # Caso recursivo: la lista existente más una sentencia nueva
    # Se agrega la sentencia al final para preservar el orden de aparición
    p[0] = p[1] + [p[2]]

def p_lista_sentencias_unica(p):
    """lista_sentencias : sentencia"""
    # Caso base: una sola sentencia crea una lista de un elemento
    p[0] = [p[1]]


# =============================================================================
# 4. DISPATCHER DE SENTENCIAS
#    Esta regla actúa como punto de unión (junction) entre lista_sentencias
#    y los distintos tipos de sentencia. Su único trabajo es propagar el nodo.
# =============================================================================

def p_sentencia(p):
    """sentencia : declaracion
                 | asignacion
                 | mostrar_stmt
                 | leer_stmt
                 | si_stmt"""
    # p[1] ya es el nodo AST construido por la regla que se aplicó;
    # simplemente lo propagamos hacia arriba en el árbol
    p[0] = p[1]


# =============================================================================
# 5. DECLARACIÓN DE VARIABLE
#    Crea un nodo VarDecl con el tipo, el nombre y la expresión de valor.
#    Ejemplos válidos:
#        entero   a      = 5;
#        cadena   nombre = "Ana";
#        logico   activo = verdadero;
# =============================================================================

def p_declaracion(p):
    """declaracion : tipo ID ASIGNAR expr PUNTOCOM"""
    # p[1]=tipo, p[2]=nombre(str), p[3]='=', p[4]=nodo expr, p[5]=';'
    p[0] = VarDecl(var_type=p[1], name=p[2], value=p[4])

def p_tipo_entero(p):
    """tipo : ENTERO"""
    p[0] = 'entero'      # Retorna el string que usará la tabla de símbolos

def p_tipo_cadena(p):
    """tipo : CADENA_TIPO"""
    p[0] = 'cadena'

def p_tipo_logico(p):
    """tipo : LOGICO_TIPO"""
    p[0] = 'logico'


# =============================================================================
# 6. ASIGNACIÓN (reasignación de variable ya declarada)
#    Se distingue de VarDecl porque NO incluye el tipo; la variable ya
#    fue registrada en la tabla de símbolos durante su declaración.
#    Ejemplo: contador = contador + 1;
# =============================================================================

def p_asignacion(p):
    """asignacion : ID ASIGNAR expr PUNTOCOM"""
    # p[1]=nombre, p[2]='=', p[3]=nodo expr, p[4]=';'
    p[0] = Assign(name=p[1], value=p[3])


# =============================================================================
# 7. SENTENCIA MOSTRAR
#    Produce un PrintStmt con la expresión a imprimir.
#    Ejemplo: mostrar(a + b);
# =============================================================================

def p_mostrar_stmt(p):
    """mostrar_stmt : MOSTRAR PAR_IZQ expr PAR_DER PUNTOCOM"""
    # p[3] es la expresión dentro de los paréntesis
    p[0] = PrintStmt(expr=p[3])


# =============================================================================
# 8. SENTENCIA LEER
#    Produce un ReadStmt con el nombre de la variable destino.
#    Se almacena el nombre (str) en lugar de un nodo Identifier porque
#    la gramática requiere que el destino sea siempre una variable directa.
#    Ejemplo: leer(nombre);
# =============================================================================

def p_leer_stmt(p):
    """leer_stmt : LEER PAR_IZQ ID PAR_DER PUNTOCOM"""
    # p[3] es el string del nombre del identificador
    p[0] = ReadStmt(name=p[3])


# =============================================================================
# 9. SENTENCIA CONDICIONAL — SI / SINO
#    Dos producciones separadas: una sin 'sino' y otra con 'sino'.
#    PLY elige automáticamente la correcta según los tokens disponibles.
# =============================================================================

def p_si_stmt_con_sino(p):
    """si_stmt : SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sentencias LLA_DER SINO LLA_IZQ lista_sentencias LLA_DER"""
    # p[3]  = condición,         p[6]  = cuerpo del 'si',
    # p[10] = cuerpo del 'sino'
    p[0] = IfStmt(condition=p[3], then_body=p[6], else_body=p[10])

def p_si_stmt_sin_sino(p):
    """si_stmt : SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sentencias LLA_DER"""
    # else_body=None indica que no existe rama alternativa
    p[0] = IfStmt(condition=p[3], then_body=p[6], else_body=None)


# =============================================================================
# 10-12. EXPRESIONES LÓGICAS — jerarquía O → Y → NO
#    La estructura en cascada (O más externo, NO más interno) establece la
#    precedencia sin depender de la tabla 'precedence':
#        OR tiene menor precedencia que AND, que tiene menor que NOT.
#    Cada nivel "pasa" al siguiente mediante una regla de propagación.
# =============================================================================

# ── Nivel OR (menor precedencia lógica) ─────────────────────────────────────

def p_expr_o(p):
    """expr : expr O expr_y"""
    # Crea un nodo de operación lógica OR
    p[0] = LogicOp(op='o', left=p[1], right=p[3])

def p_expr_pasa_y(p):
    """expr : expr_y"""
    # Si no hay OR, propaga la expresión Y hacia arriba sin envolver
    p[0] = p[1]

# ── Nivel AND ────────────────────────────────────────────────────────────────

def p_expr_y_y(p):
    """expr_y : expr_y Y expr_no"""
    p[0] = LogicOp(op='y', left=p[1], right=p[3])

def p_expr_y_pasa_no(p):
    """expr_y : expr_no"""
    # Propagación hacia el nivel NOT
    p[0] = p[1]

# ── Nivel NOT (mayor precedencia lógica) ─────────────────────────────────────

def p_expr_no_no(p):
    """expr_no : NO expr_no"""
    # NOT es unario y asocia a la derecha, permitiendo: no no bandera
    p[0] = NotOp(operand=p[2])

def p_expr_no_pasa_rel(p):
    """expr_no : expr_rel"""
    # Propagación hacia el nivel relacional
    p[0] = p[1]


# =============================================================================
# 13. EXPRESIONES RELACIONALES
#    Comparaciones entre expresiones aritméticas.
#    Todos los operadores relacionales están en una sola regla con
#    alternativas (|), lo que es más compacto y equivalente a reglas separadas.
# =============================================================================

def p_expr_rel_op(p):
    """expr_rel : expr_arit MAYOR    expr_arit
                | expr_arit MENOR    expr_arit
                | expr_arit MAYOR_IG expr_arit
                | expr_arit MENOR_IG expr_arit
                | expr_arit IGUAL    expr_arit
                | expr_arit DISTINTO expr_arit"""
    # p[2] contiene el operador relacional como string (ej. '>', '<=', '==')
    p[0] = BinOp(op=p[2], left=p[1], right=p[3])

def p_expr_rel_pasa(p):
    """expr_rel : expr_arit"""
    # Si no hay operador relacional, propaga la expresión aritmética
    p[0] = p[1]


# =============================================================================
# 14. EXPRESIONES ARITMÉTICAS — suma y resta (izquierda-asociativas)
#    La recursión a izquierda hace que a+b+c se agrupe como (a+b)+c,
#    lo cual es el comportamiento matemático esperado.
# =============================================================================

def p_expr_arit_mas(p):
    """expr_arit : expr_arit MAS termino"""
    p[0] = BinOp(op='+', left=p[1], right=p[3])

def p_expr_arit_menos(p):
    """expr_arit : expr_arit MENOS termino"""
    p[0] = BinOp(op='-', left=p[1], right=p[3])

def p_expr_arit_pasa(p):
    """expr_arit : termino"""
    # Propagación hacia el nivel de términos (multiplicación/división)
    p[0] = p[1]


# =============================================================================
# 15. TÉRMINOS — multiplicación y división (mayor precedencia que suma/resta)
#    Al estar en un nivel gramatical inferior, * y / se evalúan antes que + y -,
#    replicando la precedencia matemática estándar.
# =============================================================================

def p_termino_por(p):
    """termino : termino POR factor"""
    p[0] = BinOp(op='*', left=p[1], right=p[3])

def p_termino_entre(p):
    """termino : termino ENTRE factor"""
    p[0] = BinOp(op='/', left=p[1], right=p[3])

def p_termino_pasa(p):
    """termino : factor"""
    # Propagación hacia el nivel de factores (átomos)
    p[0] = p[1]


# =============================================================================
# 16. FACTORES — átomos indivisibles de las expresiones
#    Son los nodos hoja del árbol de expresiones: literales, variables y
#    subexpresiones entre paréntesis.
# =============================================================================

def p_factor_numero(p):
    """factor : NUMERO"""
    p[0] = Number(value=p[1])           # p[1] ya es int (convertido por el lexer)

def p_factor_cadena(p):
    """factor : LITERAL_CADENA"""
    p[0] = StringLiteral(value=p[1])    # p[1] ya es str sin comillas (lexer lo limpió)

def p_factor_verdadero(p):
    """factor : VERDADERO"""
    p[0] = BoolLiteral(value=True)      # Literal booleano verdadero

def p_factor_falso(p):
    """factor : FALSO"""
    p[0] = BoolLiteral(value=False)     # Literal booleano falso

def p_factor_id(p):
    """factor : ID"""
    p[0] = Identifier(name=p[1])        # Referencia a variable; se resolverá en tiempo de ejecución

def p_factor_parentesis(p):
    """factor : PAR_IZQ expr PAR_DER"""
    # Los paréntesis no producen nodo propio; simplemente elevan la
    # precedencia al pasar la expresión interior directamente
    p[0] = p[2]

def p_factor_umenos(p):
    """factor : MENOS factor %prec UMENOS"""
    # '%prec UMENOS' le dice a PLY que use la precedencia de UMENOS (la más alta)
    # para esta regla, evitando conflictos con el MENOS binario de expr_arit.
    p[0] = UnaryMinus(operand=p[2])


# =============================================================================
# 17. MANEJO DE ERRORES SINTÁCTICOS
#    p_error() es invocada por PLY cuando encuentra un token que no encaja
#    en la gramática. Examina parser.symstack para inferir qué producción
#    estaba construyendo el parser y emite un mensaje específico del formato:
#
#        [Sintaxis] Error en linea X:
#          Encontrado: '<token>' (<tipo>)
#          Causa:      <qué está mal>
#          Sugerencia: <cómo corregirlo>
#
#    Casos detectados (en orden de especificidad):
#        1.  p is None              → EOF inesperado
#        2.  ASIGNAR + inicio-stmt  → falta ';' al final  (va antes que reservada)
#        3.  palabra reservada      → no puede usarse como variable
#        4.  tipo ID en pila        → falta '=' en declaración
#        5.  ID ID consecutivos     → posible tipo de dato no reconocido
#        6.  operador + operador    → doble operador consecutivo
#        7.  operador + ; o }       → operando faltante
#        8.  ASIGNAR en tope        → expresión faltante después de '='
#        9.  MOSTRAR + PAR_IZQ      → falta ')' en mostrar(...)
#       10.  LLA_IZQ en pila        → falta '}' para cerrar si
#       11.  PAR_DER sin PAR_IZQ    → paréntesis extra
#       12.  PAR_IZQ + ; o }        → paréntesis sin cerrar
#       13.  fallback               → contexto gramatical genérico
#       (leer(...) → falta ')': verificado dentro del caso 9, análogo a MOSTRAR)
# =============================================================================

# Mapa de tipo-de-token → palabra tal como aparece en el fuente.
# Permite construir mensajes de error más amigables que solo mostrar el tipo.
_PALABRAS_RESERVADAS = {
    'Y'          : 'y',
    'O'          : 'o',
    'NO'         : 'no',
    'SI'         : 'si',
    'SINO'       : 'sino',
    'ENTERO'     : 'entero',
    'CADENA_TIPO': 'cadena',
    'LOGICO_TIPO': 'logico',
    'VERDADERO'  : 'verdadero',
    'FALSO'      : 'falso',
    'LEER'       : 'leer',
    'MOSTRAR'    : 'mostrar',
}

def p_error(p):
    """
    Manejador de errores sintácticos invocado automáticamente por PLY.

    Usa parser.symstack y parser.statestack para inferir qué producción
    gramatical estaba en curso cuando se encontró el token inesperado,
    y emite un mensaje detallado con causa y sugerencia concreta.

    Parámetro:
        p: objeto LexToken donde se detectó el error, o None si es EOF
    """
    # ── Caso 1: fin de archivo inesperado ────────────────────────────────────
    if p is None:
        print("\n[Sintaxis] Error: el archivo termino inesperadamente. "
              "Verifica que todas las llaves { } y puntos y coma ; esten cerrados.")
        return

    # ── Extraer pila de símbolos del parser ──────────────────────────────────
    # parser.symstack contiene YaccSymbol con .type y .value para cada símbolo
    # (terminal o no-terminal) que el parser ha reconocido hasta este punto.
    # El marcador de fondo '$end' se filtra para trabajar solo con la gramática.
    _syms = [
        sym for sym in parser.symstack
        if hasattr(sym, 'type') and isinstance(sym.type, str) and sym.type != '$end'
    ]
    _sym_types = [s.type for s in _syms]

    # ── Helper de formato uniforme ───────────────────────────────────────────
    def _fmt(causa, sugerencia):
        print(f"\n[Sintaxis] Error en linea {p.lineno}:")
        print(f"  Encontrado: '{p.value}' ({p.type})")
        print(f"  Causa:      {causa}")
        print(f"  Sugerencia: {sugerencia}")

    # ── Constantes de diagnóstico ─────────────────────────────────────────────
    _OP_DISPLAY = {
        'MAS': '+', 'MENOS': '-', 'POR': '*', 'ENTRE': '/',
        'MAYOR': '>', 'MENOR': '<', 'MAYOR_IG': '>=', 'MENOR_IG': '<=',
        'IGUAL': '==', 'DISTINTO': '!=', 'Y': 'y', 'O': 'o',
    }
    _OPERADORES_BIN = set(_OP_DISPLAY)
    _STMT_STARTERS  = {'ENTERO', 'CADENA_TIPO', 'LOGICO_TIPO', 'MOSTRAR', 'LEER', 'SI', 'ID'}

    # ── Caso 2: ';' faltante al final de declaracion/asignacion ─────────────
    # Esta verificacion va ANTES del chequeo de palabra reservada porque cuando
    # falta ';' la siguiente sentencia empieza con una palabra clave (entero,
    # mostrar, si...) que de otro modo dispararía el caso de palabra reservada.
    # Patrón: ASIGNAR en pila (la expresion ya se redujo) + primer token de
    # una nueva sentencia como token inesperado.
    if 'ASIGNAR' in _sym_types and p.type in _STMT_STARTERS:
        _fmt(
            "Falta ';' al final de la declaracion o asignacion.",
            "Agrega ';' al final de la linea: tipo variable = valor;"
        )
        return

    # ── Caso 2b: llave faltante — bloque abierto sin cerrar o sin abrir ───────
    # Debe ir ANTES del Caso 3 para que palabras reservadas válidas como inicio
    # de sentencia no sean confundidas con errores de nombre de variable.
    if p.type in _PALABRAS_RESERVADAS or p.type in _STMT_STARTERS:

        # A28: hay un bloque { abierto → falta '}' (o falta '{' del sino)
        if 'LLA_IZQ' in _sym_types:
            if 'SINO' in _sym_types:
                lla_pos  = max(i for i, t in enumerate(_sym_types) if t == 'LLA_IZQ')
                sino_pos = max(i for i, t in enumerate(_sym_types) if t == 'SINO')
                if sino_pos > lla_pos:
                    _fmt(
                        "Falta '{' para abrir el bloque sino.",
                        "Usa: } sino { ... }"
                    )
                    return
            bloque = 'sino' if 'SINO' in _sym_types else 'si'
            _fmt(
                f"Falta '}}' para cerrar el bloque '{bloque}'.",
                "Agrega '}' antes de esta linea para cerrar el bloque abierto con '{'."
            )
            return

        # B02: SINO en pila sin LLA_IZQ → falta '{' para el cuerpo del sino
        if 'SINO' in _sym_types:
            _fmt(
                "Falta '{' para abrir el bloque sino.",
                "Usa: } sino { ... }"
            )
            return

        # B06: SI en pila, condicion ya reducida (PAR_DER en pila), sin LLA_IZQ
        if 'SI' in _sym_types and 'PAR_DER' in _sym_types and 'LLA_IZQ' not in _sym_types:
            _fmt(
                "Falta '{' para abrir el cuerpo del si.",
                "Usa: si (expr) { ... }"
            )
            return

        # B07: SI en pila sin PAR_IZQ → falta '(' para condicion del si
        if 'SI' in _sym_types and 'PAR_IZQ' not in _sym_types:
            _fmt(
                "Falta '(' para abrir la condicion del si.",
                "Usa: si (expr) { ... }"
            )
            return

        # B09: MOSTRAR en pila sin PAR_IZQ → falta '(' en mostrar
        if 'MOSTRAR' in _sym_types and 'PAR_IZQ' not in _sym_types:
            _fmt(
                "Falta '(' en mostrar.",
                "Usa: mostrar(expr);"
            )
            return

    # ── Caso 3: palabra reservada usada como nombre de variable ───────────────
    if p.type in _PALABRAS_RESERVADAS:
        if p.type == 'SINO':
            _fmt(
                "'sino' solo puede aparecer despues de un bloque si { ... }.",
                "Estructura correcta: si (expr) { ... } sino { ... }"
            )
        else:
            palabra = _PALABRAS_RESERVADAS[p.type]
            _fmt(
                f"'{palabra}' es una palabra reservada y no puede usarse como nombre de variable.",
                f"Elige un nombre diferente, por ejemplo '{palabra}_var' o '{palabra}1'."
            )
        return

    # ── Caso 4: falta '=' en declaración (tipo ID en pila) ───────────────────
    # Patrón de pila: [..., tipo, ID]  →  declaracion: tipo ID *ASIGNAR* expr PUNTOCOM
    if (len(_sym_types) >= 2
            and _sym_types[-1] == 'ID'
            and _sym_types[-2] == 'tipo'):
        var_name = _syms[-1].value
        _fmt(
            f"Se esperaba '=' o algun otro tipo de operador para asignar valor en la declaracion de '{var_name}' o concretar la operacion",
            f"Escribe: tipo {var_name} = <valor>;"
        )
        return

    # ── Caso 5: dos identificadores consecutivos ──────────────────────────────
    # Patrón: [..., ID] y p.type == 'ID'  →  posible tipo de dato no reconocido
    # Ejemplo: texto nombre = 5;  (donde 'texto' no es un tipo válido)
    if p.type == 'ID' and _sym_types and _sym_types[-1] == 'ID':
        _fmt(
            f"Se encontro '{p.value}' donde se esperaba '='.",
            "Si intentas declarar una variable usa un tipo valido: entero, cadena o logico."
        )
        return

    # ── Caso 5: operador doble consecutivo (a + * b, a ++ b) ─────────────────
    # Patrón: tope de pila es operador binario Y p.type también es operador binario
    if p.type in _OPERADORES_BIN and _sym_types and _sym_types[-1] in _OPERADORES_BIN:
        prev_op = _OP_DISPLAY[_sym_types[-1]]
        curr_op = _OP_DISPLAY.get(p.type, str(p.value))
        _fmt(
            f"Operadores consecutivos '{prev_op}' y '{curr_op}': falta el operando entre ellos.",
            f"Agrega una expresion (numero, variable o literal) entre '{prev_op}' y '{curr_op}'."
        )
        return

    # ── Caso 6: operando faltante (operador seguido de ; o } o )) ─────────────
    # Patrón: hay un operador binario en la pila y el token inesperado cierra la expresion
    if p.type in {'PUNTOCOM', 'LLA_DER', 'PAR_DER'} and any(op in _sym_types for op in _OPERADORES_BIN):
        op = next((s for s in reversed(_sym_types) if s in _OPERADORES_BIN), None)
        if op:
            op_sym = _OP_DISPLAY[op]
            _fmt(
                f"Falta el operando derecho despues del operador '{op_sym}'.",
                f"Agrega un numero, variable o expresion despues de '{op_sym}'."
            )
            return

    # ── Caso B11: '=' en condicion de si — confusion = vs == ─────────────────
    # Patron: ASIGNAR llega como token inesperado dentro de la condicion de si.
    # SI y PAR_IZQ en pila confirman que estamos dentro de si(expr).
    if p.type == 'ASIGNAR' and 'SI' in _sym_types and 'PAR_IZQ' in _sym_types:
        _fmt(
            "Usa '==' para comparar dentro de si(), no '='.",
            "Cambia '=' por '==': si (variable == valor) { ... }"
        )
        return

    # ── Caso 7: expresion faltante despues de '=' ─────────────────────────────
    # Patrón: ASIGNAR es el tope de la pila → tipo ID = <token_inesperado>
    if _sym_types and _sym_types[-1] == 'ASIGNAR':
        _fmt(
            "Se esperaba una expresion despues de '='.",
            "Agrega un valor o expresion: tipo variable = <valor>;"
        )
        return

    # ── Caso 8: ')' faltante en mostrar(...) ─────────────────────────────────
    # Patrón: MOSTRAR y PAR_IZQ en pila, y no hay PAR_DER DESPUÉS del PAR_IZQ.
    # Si PAR_DER ya aparece después de PAR_IZQ, el ')' fue consumido y el error
    # es otro (por ejemplo, ';' faltante o ')' extra).
    if 'MOSTRAR' in _sym_types and 'PAR_IZQ' in _sym_types:
        izq_pos = max(i for i, t in enumerate(_sym_types) if t == 'PAR_IZQ')
        if not any(t == 'PAR_DER' for t in _sym_types[izq_pos + 1:]):
            if p.type == 'COMA':
                _fmt(
                    "mostrar() solo acepta una expresion por llamada.",
                    "Para mostrar varios valores usa mostrar() por separado: mostrar(a); mostrar(b);"
                )
            else:
                _fmt(
                    "Falta ')' para cerrar el parentesis de mostrar(...).",
                    "Agrega ')' despues de la expresion: mostrar(expr);"
                )
            return

    # ── Caso 9: ')' faltante en leer(...) ─────────────────────────────────────
    # Mismo patrón que caso 8 pero para leer(...).
    if 'LEER' in _sym_types and 'PAR_IZQ' in _sym_types:
        izq_pos = max(i for i, t in enumerate(_sym_types) if t == 'PAR_IZQ')
        if not any(t == 'PAR_DER' for t in _sym_types[izq_pos + 1:]):
            if p.type == 'COMA':
                _fmt(
                    "leer() solo acepta un argumento.",
                    "Para leer varios valores usa leer() por separado: leer(a); leer(b);"
                )
            elif p.type in _OPERADORES_BIN:
                _fmt(
                    "leer() solo acepta un nombre de variable, no una expresion.",
                    "Escribe: leer(nombre_variable);"
                )
            elif p.type in {'NUMERO', 'LITERAL_CADENA', 'VERDADERO', 'FALSO'}:
                _fmt(
                    "leer() solo acepta un nombre de variable, no un literal.",
                    "Escribe: leer(nombre_variable);"
                )
            else:
                _fmt(
                    "Falta ')' para cerrar el parentesis de leer(...).",
                    "Agrega ')' despues del nombre de variable: leer(variable);"
                )
            return

    # ── Caso 10: '}' faltante al cerrar bloque si ─────────────────────────────
    # Patrón: LLA_IZQ en pila → si_stmt espera LLA_DER para cerrar el bloque
    if 'LLA_IZQ' in _sym_types:
        _fmt(
            "Falta '}' para cerrar el bloque 'si'.",
            "Agrega '}' para cerrar el bloque de codigo abierto con '{'."
        )
        return

    # ── Caso 11-b: ')' extra cuando el par ya fue cerrado (ej: mostrar(a))) ────
    if p.type == 'PAR_DER' and 'PAR_IZQ' in _sym_types:
        izq_pos = max(i for i, t in enumerate(_sym_types) if t == 'PAR_IZQ')
        if any(t == 'PAR_DER' for t in _sym_types[izq_pos + 1:]):
            _fmt(
                "Parentesis ')' extra: el parentesis ya fue cerrado.",
                "Elimina el ')' sobrante."
            )
            return

    # ── Caso 11: ')' extra sin '(' correspondiente ────────────────────────────
    if p.type == 'PAR_DER' and 'PAR_IZQ' not in _sym_types:
        _fmt(
            "Parentesis de cierre ')' inesperado: no hay '(' que le corresponda.",
            "Elimina el ')' sobrante o agrega '(' de apertura antes de la expresion."
        )
        return

    # ── Caso 11b: ')' extra cuando el par ya estaba cerrado ──────────────────
    # Patron: PAR_DER como token, PAR_IZQ en pila, pero ya hay un PAR_DER
    # despues del ultimo PAR_IZQ → el ')' fue consumido y este es un extra.
    if p.type == 'PAR_DER' and 'PAR_IZQ' in _sym_types:
        izq_pos = max(i for i, t in enumerate(_sym_types) if t == 'PAR_IZQ')
        if any(t == 'PAR_DER' for t in _sym_types[izq_pos + 1:]):
            _fmt(
                "Parentesis ')' extra: el parentesis ya fue cerrado.",
                "Elimina el ')' sobrante."
            )
            return

    # ── Caso 12: '(' sin cerrar dentro de expresion ───────────────────────────
    if 'PAR_IZQ' in _sym_types and p.type in {'PUNTOCOM', 'LLA_DER'}:
        _fmt(
            "Parentesis '(' sin cerrar dentro de la expresion.",
            "Agrega ')' para cerrar el parentesis de apertura."
        )
        return

    # ── Caso B08: falta ')' en condicion de si ───────────────────────────────
    # PAR_IZQ en pila sin PAR_DER aun (condicion no cerrada) y llega '{'.
    # LLA_IZQ como token no pasa por el guard del Fix1 ni por Caso 12,
    # por eso va aqui separado.
    if ('SI' in _sym_types
            and 'PAR_IZQ' in _sym_types
            and 'PAR_DER' not in _sym_types
            and p.type == 'LLA_IZQ'):
        _fmt(
            "Falta ')' para cerrar la condicion del si.",
            "Usa: si (expr) { ... }"
        )
        return

    # ── Caso C10: '}' sin bloque si abierto ──────────────────────────────────
    if p.type == 'LLA_DER' and 'LLA_IZQ' not in _sym_types:
        _fmt(
            "Llave de cierre '}' inesperada: no hay bloque si abierto.",
            "Elimina el '}' sobrante o agrega 'si (expr) {' antes."
        )
        return

    # ── Caso C11: '{' fuera de bloque si ─────────────────────────────────────
    if p.type == 'LLA_IZQ' and 'SI' not in _sym_types:
        _fmt(
            "Llave '{' inesperada fuera de un bloque si.",
            "Las llaves { } solo se usan en: si (expr) { ... }"
        )
        return

    # ── Caso C02/C09: ';' extra o fuera de lugar ─────────────────────────────
    # Caso 2 ya maneja PUNTOCOM cuando ASIGNAR esta en pila (falta ';').
    # Caso 6 ya maneja PUNTOCOM cuando hay operador pendiente (operando faltante).
    # Este caso captura el ';' genuinamente sobrante o al inicio del archivo.
    if p.type == 'PUNTOCOM':
        _fmt(
            "Punto y coma inesperado o extra.",
            "Elimina el ';' sobrante."
        )
        return

    # ── Caso 13: fallback genérico con contexto gramatical ────────────────────
    # Se activa solo si ningún patrón específico aplica.
    # Incluye el símbolo gramatical que estaba en construcción para orientar al usuario.
    _CONTEXT_NAMES = {
        'tipo':             "una declaracion de variable",
        'ID':               "una asignacion o declaracion",
        'MOSTRAR':          "una sentencia mostrar(expr);",
        'LEER':             "una sentencia leer(variable);",
        'SI':               "una sentencia si (...) { ... }",
        'LLA_IZQ':          "un bloque de codigo { ... }",
        'PAR_IZQ':          "una expresion entre parentesis",
        'PAR_DER':          "el cierre de un parentesis (posible ')' de mas)",
        'PUNTOCOM':         "el cierre de una sentencia ';' (posible ')' extra o token fuera de lugar)",
        'ASIGNAR':          "la asignacion de un valor (tipo variable = valor;)",
        'expr':             "una expresion",
        'expr_y':           "una expresion logica (y)",
        'expr_no':          "una expresion logica (no)",
        'expr_rel':         "una expresion relacional",
        'expr_arit':        "una expresion aritmetica",
        'termino':          "un termino aritmetico (*/)",
        'factor':           "un factor (literal, variable o subexpresion)",
        'declaracion':      "una declaracion de variable",
        'asignacion':       "una asignacion",
        'lista_sentencias': "una lista de sentencias",
        'sentencia':        "una sentencia",
    }
    simbolo = _sym_types[-1] if _sym_types else 'desconocido'
    contexto = _CONTEXT_NAMES.get(simbolo, f"la construccion '{simbolo}'")
    print(f"\n[Sintaxis] Error en linea {p.lineno}:")
    print(f"  Encontrado: '{p.value}' ({p.type})")
    print(f"  Causa:      Token inesperado mientras se construia {contexto}.")
    print(f"  Sugerencia: Verifica la sintaxis alrededor de la linea {p.lineno}.")


# =============================================================================
# 18. CONSTRUCCIÓN DEL PARSER
#    yacc.yacc() lee todas las funciones p_* del módulo, construye las
#    tablas LALR(1) y devuelve el objeto parser.
#
#    write_tables=False: no genera archivo parser.out en disco (evita
#    archivos innecesarios en el directorio de trabajo).
#    errorlog=NullLogger(): suprime los mensajes de advertencia de PLY
#    sobre conflictos shift/reduce que ya están resueltos por 'precedence'.
# =============================================================================
parser = yacc.yacc(write_tables=False, errorlog=yacc.NullLogger())


# =============================================================================
# 19. FUNCIÓN PÚBLICA — parse()
#    Punto de entrada para que main.py y otros módulos accedan al parser.
# =============================================================================

def parse(source_code: str) -> Program:
    """
    Analiza sintácticamente el código fuente y construye el AST.

    Usa un clon del lexer (lexer.clone()) por la misma razón que tokenize():
    para no consumir el estado del lexer global y permitir múltiples
    análisis independientes dentro de la misma sesión.

    Parámetros:
        source_code (str): texto completo del programa a analizar

    Retorna:
        Program: nodo raíz del AST si el análisis fue exitoso
        None   : si se encontraron errores sintácticos (PLY los reporta
                 llamando a p_error() y devuelve None al fallar)
    """
    return parser.parse(source_code, lexer=lexer.clone())
