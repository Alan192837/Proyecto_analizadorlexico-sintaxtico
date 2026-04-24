# =============================================================================
# parser.py — Analizador Sintactico
# =============================================================================
# Responsabilidad: consumir los tokens del lexer y construir el AST.
#
# Herramienta: PLY (Python Lex-Yacc) -> modulo ply.yacc
#
# GRAMATICA COMPLETA (BNF, sintaxis en español):
#
#   programa      -> lista_sentencias
#   lista_sent    -> lista_sentencias sentencia | sentencia
#   sentencia     -> declaracion | asignacion | mostrar_stmt
#                  | leer_stmt   | si_stmt
#
#   declaracion   -> tipo ID ASIGNAR expr PUNTOCOM
#   asignacion    -> ID ASIGNAR expr PUNTOCOM
#   mostrar_stmt  -> MOSTRAR PAR_IZQ expr PAR_DER PUNTOCOM
#   leer_stmt     -> LEER PAR_IZQ ID PAR_DER PUNTOCOM
#   si_stmt       -> SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sent LLA_DER
#                  | SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sent LLA_DER
#                    SINO LLA_IZQ lista_sent LLA_DER
#
#   tipo          -> ENTERO | CADENA_TIPO | LOGICO_TIPO
#
#   expr          -> expr O   expr_y  | expr_y
#   expr_y        -> expr_y Y expr_no | expr_no
#   expr_no       -> NO expr_no       | expr_rel
#   expr_rel      -> expr_arit OP_REL expr_arit | expr_arit
#   expr_arit     -> expr_arit MAS    termino
#                  | expr_arit MENOS  termino
#                  | termino
#   termino       -> termino POR    factor
#                  | termino ENTRE  factor
#                  | factor
#   factor        -> NUMERO | LITERAL_CADENA | VERDADERO | FALSO | ID
#                  | PAR_IZQ expr PAR_DER
#                  | MENOS factor            (menos unario)
# =============================================================================

import ply.yacc as yacc
from lexer import tokens,lexer     # PLY necesita 'tokens' en el scope de este modulo
from ast_nodes import *


# ---------------------------------------------------------------------------
# 1. PRECEDENCIA Y ASOCIATIVIDAD
#    Resuelve conflictos shift/reduce.
#    Mayor profundidad en la tupla = mayor precedencia.
# ---------------------------------------------------------------------------
precedence = (
    ('left',  'O'),
    ('left',  'Y'),
    ('right', 'NO'),
    ('left',  'IGUAL', 'DISTINTO'),
    ('left',  'MENOR', 'MAYOR', 'MENOR_IG', 'MAYOR_IG'),
    ('left',  'MAS', 'MENOS'),
    ('left',  'POR', 'ENTRE'),
    ('right', 'UMENOS'),   # pseudo-token para el menos unario
)


# ---------------------------------------------------------------------------
# 2. REGLA RAIZ
# ---------------------------------------------------------------------------
def p_programa(p):
    """programa : lista_sentencias"""
    p[0] = Program(statements=p[1])


# ---------------------------------------------------------------------------
# 3. LISTA DE SENTENCIAS
# ---------------------------------------------------------------------------
def p_lista_sentencias_multiple(p):
    """lista_sentencias : lista_sentencias sentencia"""
    p[0] = p[1] + [p[2]]

def p_lista_sentencias_unica(p):
    """lista_sentencias : sentencia"""
    p[0] = [p[1]]


# ---------------------------------------------------------------------------
# 4. DISPATCHER DE SENTENCIAS
# ---------------------------------------------------------------------------
def p_sentencia(p):
    """sentencia : declaracion
                 | asignacion
                 | mostrar_stmt
                 | leer_stmt
                 | si_stmt"""
    p[0] = p[1]


# ---------------------------------------------------------------------------
# 5. DECLARACION DE VARIABLE
#    entero   a      = 5;
#    cadena   nombre = "Ana";
#    logico   activo = verdadero;
# ---------------------------------------------------------------------------
def p_declaracion(p):
    """declaracion : tipo ID ASIGNAR expr PUNTOCOM"""
    p[0] = VarDecl(var_type=p[1], name=p[2], value=p[4])

def p_tipo_entero(p):
    """tipo : ENTERO"""
    p[0] = 'entero'

def p_tipo_cadena(p):
    """tipo : CADENA_TIPO"""
    p[0] = 'cadena'

def p_tipo_logico(p):
    """tipo : LOGICO_TIPO"""
    p[0] = 'logico'


# ---------------------------------------------------------------------------
# 6. ASIGNACION
#    contador = contador + 1;
# ---------------------------------------------------------------------------
def p_asignacion(p):
    """asignacion : ID ASIGNAR expr PUNTOCOM"""
    p[0] = Assign(name=p[1], value=p[3])


# ---------------------------------------------------------------------------
# 7. MOSTRAR
#    mostrar(a + b);
# ---------------------------------------------------------------------------
def p_mostrar_stmt(p):
    """mostrar_stmt : MOSTRAR PAR_IZQ expr PAR_DER PUNTOCOM"""
    p[0] = PrintStmt(expr=p[3])


# ---------------------------------------------------------------------------
# 8. LEER
#    leer(nombre);
# ---------------------------------------------------------------------------
def p_leer_stmt(p):
    """leer_stmt : LEER PAR_IZQ ID PAR_DER PUNTOCOM"""
    p[0] = ReadStmt(name=p[3])


# ---------------------------------------------------------------------------
# 9. SI / SINO
# ---------------------------------------------------------------------------
def p_si_stmt_con_sino(p):
    """si_stmt : SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sentencias LLA_DER SINO LLA_IZQ lista_sentencias LLA_DER"""
    p[0] = IfStmt(condition=p[3], then_body=p[6], else_body=p[10])

def p_si_stmt_sin_sino(p):
    """si_stmt : SI PAR_IZQ expr PAR_DER LLA_IZQ lista_sentencias LLA_DER"""
    p[0] = IfStmt(condition=p[3], then_body=p[6], else_body=None)


# ---------------------------------------------------------------------------
# 10-12. EXPRESIONES LOGICAS  (O → Y → NO, de menor a mayor precedencia)
# ---------------------------------------------------------------------------
def p_expr_o(p):
    """expr : expr O expr_y"""
    p[0] = LogicOp(op='o', left=p[1], right=p[3])

def p_expr_pasa_y(p):
    """expr : expr_y"""
    p[0] = p[1]

def p_expr_y_y(p):
    """expr_y : expr_y Y expr_no"""
    p[0] = LogicOp(op='y', left=p[1], right=p[3])

def p_expr_y_pasa_no(p):
    """expr_y : expr_no"""
    p[0] = p[1]

def p_expr_no_no(p):
    """expr_no : NO expr_no"""
    p[0] = NotOp(operand=p[2])

def p_expr_no_pasa_rel(p):
    """expr_no : expr_rel"""
    p[0] = p[1]


# ---------------------------------------------------------------------------
# 13. EXPRESIONES RELACIONALES
# ---------------------------------------------------------------------------
def p_expr_rel_op(p):
    """expr_rel : expr_arit MAYOR    expr_arit
                | expr_arit MENOR    expr_arit
                | expr_arit MAYOR_IG expr_arit
                | expr_arit MENOR_IG expr_arit
                | expr_arit IGUAL    expr_arit
                | expr_arit DISTINTO expr_arit"""
    p[0] = BinOp(op=p[2], left=p[1], right=p[3])

def p_expr_rel_pasa(p):
    """expr_rel : expr_arit"""
    p[0] = p[1]


# ---------------------------------------------------------------------------
# 14. EXPRESIONES ARITMETICAS — suma y resta
# ---------------------------------------------------------------------------
def p_expr_arit_mas(p):
    """expr_arit : expr_arit MAS termino"""
    p[0] = BinOp(op='+', left=p[1], right=p[3])

def p_expr_arit_menos(p):
    """expr_arit : expr_arit MENOS termino"""
    p[0] = BinOp(op='-', left=p[1], right=p[3])

def p_expr_arit_pasa(p):
    """expr_arit : termino"""
    p[0] = p[1]


# ---------------------------------------------------------------------------
# 15. TERMINOS — multiplicacion y division
# ---------------------------------------------------------------------------
def p_termino_por(p):
    """termino : termino POR factor"""
    p[0] = BinOp(op='*', left=p[1], right=p[3])

def p_termino_entre(p):
    """termino : termino ENTRE factor"""
    p[0] = BinOp(op='/', left=p[1], right=p[3])

def p_termino_pasa(p):
    """termino : factor"""
    p[0] = p[1]


# ---------------------------------------------------------------------------
# 16. FACTORES — atomos de expresion
# ---------------------------------------------------------------------------
def p_factor_numero(p):
    """factor : NUMERO"""
    p[0] = Number(value=p[1])

def p_factor_cadena(p):
    """factor : LITERAL_CADENA"""
    p[0] = StringLiteral(value=p[1])

def p_factor_verdadero(p):
    """factor : VERDADERO"""
    p[0] = BoolLiteral(value=True)

def p_factor_falso(p):
    """factor : FALSO"""
    p[0] = BoolLiteral(value=False)

def p_factor_id(p):
    """factor : ID"""
    p[0] = Identifier(name=p[1])

def p_factor_parentesis(p):
    """factor : PAR_IZQ expr PAR_DER"""
    p[0] = p[2]

def p_factor_umenos(p):
    """factor : MENOS factor %prec UMENOS"""
    p[0] = UnaryMinus(operand=p[2])


# ---------------------------------------------------------------------------
# 17. MANEJO DE ERRORES SINTACTICOS
#     Detecta si el error es por usar una palabra reservada como variable
#     y da un mensaje de ayuda especifico.
# ---------------------------------------------------------------------------

# Mapa de tipo-de-token -> palabra en el fuente (para mensajes de error)
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
    if p is None:
        print("\n[Sintaxis] Error: el archivo termino inesperadamente. "
              "Verifica que todas las llaves { } y puntos y coma ; esten cerrados.")
        return

    if p.type in _PALABRAS_RESERVADAS:
        palabra = _PALABRAS_RESERVADAS[p.type]
        print(f"\n[Sintaxis] Error en linea {p.lineno}:")
        print(f"  '{palabra}' es una palabra reservada y NO puede usarse como nombre de variable.")
    else:
        print(f"\n[Sintaxis] Error en linea {p.lineno}: "
              f"token inesperado '{p.value}' (tipo: {p.type})")
        print(f"  Verifica que la sintaxis sea correcta en esa linea.")


# ---------------------------------------------------------------------------
# 18. CONSTRUCCION DEL PARSER
# ---------------------------------------------------------------------------
parser = yacc.yacc(write_tables=False, errorlog=yacc.NullLogger())


# ---------------------------------------------------------------------------
# 19. FUNCION PUBLICA
# ---------------------------------------------------------------------------
def parse(source_code: str) -> Program:
    """
    Analiza source_code y devuelve el AST (nodo Program).
    Si hay errores sintacticos imprime mensajes descriptivos y devuelve None.
    """
    return parser.parse(source_code, lexer=lexer.clone())
