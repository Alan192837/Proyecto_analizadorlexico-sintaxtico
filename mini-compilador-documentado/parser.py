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
#    en la gramática. Se distinguen tres casos:
#        a) Fin de archivo inesperado (p es None)
#        b) Uso de palabra reservada donde se esperaba un identificador
#        c) Cualquier otro token inesperado
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

    Diferencia dos escenarios principales para dar mensajes útiles:
        1. p es None → el parser llegó al final del archivo antes de lo esperado
        2. p.type está en _PALABRAS_RESERVADAS → el usuario intentó usar
           una palabra reservada como nombre de variable

    Parámetro:
        p: objeto LexToken donde se detectó el error, o None si es EOF
    """
    if p is None:
        # El archivo terminó cuando aún se esperaban más tokens
        # (ej.: llave de cierre faltante)
        print("\n[Sintaxis] Error: el archivo termino inesperadamente. "
              "Verifica que todas las llaves { } y puntos y coma ; esten cerrados.")
        return

    if p.type in _PALABRAS_RESERVADAS:
        # El usuario usó una palabra reservada donde el parser esperaba un ID
        # Se da un mensaje específico que explica el problema
        palabra = _PALABRAS_RESERVADAS[p.type]
        print(f"\n[Sintaxis] Error en linea {p.lineno}:")
        print(f"  '{palabra}' es una palabra reservada y NO puede usarse como nombre de variable.")
    else:
        # Error genérico: token inesperado en ese punto de la gramática
        print(f"\n[Sintaxis] Error en linea {p.lineno}: "
              f"token inesperado '{p.value}' (tipo: {p.type})")
        print(f"  Verifica que la sintaxis sea correcta en esa linea.")


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
