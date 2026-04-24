# =============================================================================
# ast_nodes.py — Nodos del Arbol de Sintaxis Abstracta (AST)
# =============================================================================
# Define las clases que representan cada construccion del lenguaje.
# El parser construye estos objetos; el interprete los recorre y ejecuta.
# =============================================================================

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ASTNode:
    """Clase base de todos los nodos."""
    pass


# ---------------------------------------------------------------------------
# Nodos de declaracion / asignacion
# ---------------------------------------------------------------------------

@dataclass
class VarDecl(ASTNode):
    """entero a = 5;"""
    var_type : str      # 'entero' | 'cadena' | 'logico'
    name     : str
    value    : ASTNode


@dataclass
class Assign(ASTNode):
    """a = 10;"""
    name  : str
    value : ASTNode


# ---------------------------------------------------------------------------
# Nodos de expresion
# ---------------------------------------------------------------------------

@dataclass
class Number(ASTNode):
    """Literal entero: 42"""
    value: int


@dataclass
class StringLiteral(ASTNode):
    """Literal de cadena: "hola" """
    value: str


@dataclass
class BoolLiteral(ASTNode):
    """Literal logico: verdadero / falso"""
    value: bool


@dataclass
class Identifier(ASTNode):
    """Referencia a variable: miVar"""
    name: str


@dataclass
class BinOp(ASTNode):
    """Operacion binaria: a + b, x > 5, a == b"""
    op    : str      # '+' '-' '*' '/' '>' '<' '>=' '<=' '==' '!='
    left  : ASTNode
    right : ASTNode


@dataclass
class LogicOp(ASTNode):
    """Operacion logica binaria: a > 5 y b < 10"""
    op    : str      # 'y' | 'o'
    left  : ASTNode
    right : ASTNode


@dataclass
class NotOp(ASTNode):
    """Negacion logica: no bandera"""
    operand: ASTNode


@dataclass
class UnaryMinus(ASTNode):
    """Menos unario: -a"""
    operand: ASTNode


# ---------------------------------------------------------------------------
# Nodos de sentencia
# ---------------------------------------------------------------------------

@dataclass
class PrintStmt(ASTNode):
    """mostrar(expr);"""
    expr: ASTNode


@dataclass
class ReadStmt(ASTNode):
    """leer(variable);"""
    name: str


@dataclass
class IfStmt(ASTNode):
    """si (cond) { ... } sino { ... }"""
    condition : ASTNode
    then_body : List[ASTNode]
    else_body : Optional[List[ASTNode]] = None


@dataclass
class Program(ASTNode):
    """Nodo raiz: lista de sentencias del programa."""
    statements: List[ASTNode] = field(default_factory=list)
