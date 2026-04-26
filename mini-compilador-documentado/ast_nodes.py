"""
=============================================================================
ast_nodes.py — Nodos del Árbol de Sintaxis Abstracta (AST)
=============================================================================
Propósito general:
    Define la jerarquía de clases que representan cada construcción válida
    del mini-lenguaje (declaraciones, expresiones, sentencias de control).

    El flujo de uso es el siguiente:
        1. El PARSER (parser.py) crea instancias de estas clases mientras
           reconoce la gramática del código fuente.
        2. El INTÉRPRETE (interpreter.py) recorre el árbol resultante nodo
           por nodo para ejecutar el programa.

    Estas clases son exclusivamente contenedores de datos (nodos del árbol);
    no contienen lógica de ejecución ni de análisis.

    Se usa @dataclass para generar automáticamente __init__, __repr__ y
    __eq__, reduciendo el código repetitivo (boilerplate).

Dependencias externas:
    - dataclasses: para la generación automática de constructores.
    - typing: para anotaciones de tipo más expresivas (List, Optional, Any).
=============================================================================
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


# =============================================================================
# CLASE BASE
# =============================================================================

@dataclass
class ASTNode:
    """
    Clase base vacía de la que heredan todos los nodos del AST.

    Propósito: permite usar isinstance(nodo, ASTNode) para verificar que
    cualquier objeto es un nodo válido del árbol, sin importar cuál.
    No define atributos ni métodos porque cada subclase los declara según
    su propia estructura.
    """
    pass


# =============================================================================
# NODOS DE DECLARACIÓN Y ASIGNACIÓN
# =============================================================================

@dataclass
class VarDecl(ASTNode):
    """
    Representa la declaración de una variable con tipo y valor inicial.

    Sintaxis en el lenguaje:
        entero  contador = 0;
        cadena  nombre   = "Ana";
        logico  activo   = verdadero;

    Atributos:
        var_type (str)   : tipo del dato declarado → 'entero' | 'cadena' | 'logico'
        name     (str)   : nombre de la variable tal como aparece en el fuente
        value    (ASTNode): sub-árbol que representa el valor inicial;
                            puede ser cualquier expresión válida (Number, BinOp, etc.)
    """
    var_type : str       # Tipo del dato: 'entero', 'cadena' o 'logico'
    name     : str       # Nombre de la variable (identificador)
    value    : ASTNode   # Expresión que provee el valor inicial


@dataclass
class Assign(ASTNode):
    """
    Representa la reasignación de valor a una variable ya declarada.

    Diferencia clave con VarDecl: aquí NO se especifica tipo porque la
    variable ya fue declarada previamente; solo se actualiza su valor.

    Sintaxis en el lenguaje:
        contador = contador + 1;
        nombre   = "Pedro";

    Atributos:
        name  (str)    : nombre de la variable destino de la asignación
        value (ASTNode): expresión cuyo resultado se asignará a la variable
    """
    name  : str       # Variable que recibirá el nuevo valor
    value : ASTNode   # Expresión que calcula el nuevo valor


# =============================================================================
# NODOS DE EXPRESIÓN — LITERALES
# =============================================================================

@dataclass
class Number(ASTNode):
    """
    Literal entero: un número escrito directamente en el fuente.

    Ejemplos:
        42, 0, 100

    Atributos:
        value (int): el valor entero ya convertido desde texto a Python int
    """
    value: int


@dataclass
class StringLiteral(ASTNode):
    """
    Literal de cadena: texto delimitado por comillas dobles en el fuente.

    Ejemplos:
        "hola mundo", "Ana"

    Nota: las comillas NO se almacenan; el lexer las elimina al tokenizar.

    Atributos:
        value (str): el contenido de la cadena sin las comillas delimitadoras
    """
    value: str


@dataclass
class BoolLiteral(ASTNode):
    """
    Literal lógico: los únicos dos valores booleanos del lenguaje.

    Ejemplos en el fuente:
        verdadero  →  almacenado como True  (Python bool)
        falso      →  almacenado como False (Python bool)

    Atributos:
        value (bool): True o False, según la palabra reservada reconocida
    """
    value: bool


# =============================================================================
# NODOS DE EXPRESIÓN — REFERENCIAS Y OPERACIONES
# =============================================================================

@dataclass
class Identifier(ASTNode):
    """
    Referencia a una variable en una expresión.

    Cuando el intérprete encuentra un Identifier, lo resuelve consultando
    la tabla de símbolos para obtener el valor actual de esa variable.

    Ejemplos:
        contador, nombre, activo

    Atributos:
        name (str): nombre exacto de la variable referenciada
    """
    name: str


@dataclass
class BinOp(ASTNode):
    """
    Operación binaria: aritmética o relacional entre dos sub-expresiones.

    Cubre tanto operadores aritméticos como de comparación, ya que ambos
    toman dos operandos y producen un único resultado.

    Operadores soportados:
        Aritméticos  → '+' '-' '*' '/'
        Relacionales → '>' '<' '>=' '<=' '==' '!='

    Atributos:
        op    (str)    : el operador como cadena (ej. '+', '>=')
        left  (ASTNode): sub-árbol del operando izquierdo
        right (ASTNode): sub-árbol del operando derecho

    Ejemplo de árbol para  a + b * 2:
        BinOp('+',
            Identifier('a'),
            BinOp('*', Identifier('b'), Number(2))
        )
        La precedencia ya está resuelta por el parser; el árbol refleja
        el orden correcto de evaluación.
    """
    op    : str       # Operador como cadena de texto
    left  : ASTNode   # Operando izquierdo
    right : ASTNode   # Operando derecho


@dataclass
class LogicOp(ASTNode):
    """
    Operación lógica binaria entre dos expresiones booleanas.

    Se distingue de BinOp porque su semántica incluye evaluación en
    cortocircuito (el intérprete puede omitir evaluar el operando derecho
    si el resultado ya es determinado por el izquierdo).

    Operadores soportados:
        'y'  →  AND lógico (ambos deben ser verdaderos)
        'o'  →  OR  lógico (al menos uno debe ser verdadero)

    Atributos:
        op    (str)    : 'y' o 'o'
        left  (ASTNode): sub-árbol del operando izquierdo
        right (ASTNode): sub-árbol del operando derecho
    """
    op    : str       # Operador lógico: 'y' (AND) o 'o' (OR)
    left  : ASTNode   # Expresión booleana izquierda
    right : ASTNode   # Expresión booleana derecha


@dataclass
class NotOp(ASTNode):
    """
    Negación lógica unaria: invierte el valor booleano de una expresión.

    Sintaxis en el lenguaje:
        no bandera         →  NOT bandera
        no (a > 5)         →  NOT (a > 5)

    Atributos:
        operand (ASTNode): la expresión cuyo resultado se niega
    """
    operand: ASTNode   # Expresión booleana a negar


@dataclass
class UnaryMinus(ASTNode):
    """
    Menos unario: cambia el signo de una expresión numérica.

    Sintaxis en el lenguaje:
        -contador
        -(a + b)

    Se modela como nodo separado (no como BinOp con 0) para que el
    intérprete lo evalúe directamente con 'return -valor'.

    Atributos:
        operand (ASTNode): expresión numérica cuyo signo se invierte
    """
    operand: ASTNode   # Expresión numérica a negar


# =============================================================================
# NODOS DE SENTENCIA
# =============================================================================

@dataclass
class PrintStmt(ASTNode):
    """
    Sentencia de salida: evalúa una expresión e imprime su resultado.

    Sintaxis en el lenguaje:
        mostrar(a + b);
        mostrar("Hola, mundo");

    Atributos:
        expr (ASTNode): expresión cuyo valor se imprimirá en pantalla
    """
    expr: ASTNode   # Expresión a evaluar e imprimir


@dataclass
class ReadStmt(ASTNode):
    """
    Sentencia de entrada: solicita un valor al usuario y lo almacena
    en la variable indicada.

    Sintaxis en el lenguaje:
        leer(edad);
        leer(nombre);

    Nota: a diferencia de PrintStmt, aquí se almacena el NOMBRE de la
    variable (un str), no un sub-árbol de expresión, porque el destino
    de la lectura siempre debe ser una variable existente, no una
    expresión arbitraria.

    Atributos:
        name (str): nombre de la variable donde se guardará el valor leído
    """
    name: str   # Nombre de la variable destino de la lectura


@dataclass
class IfStmt(ASTNode):
    """
    Sentencia condicional con rama 'si' obligatoria y 'sino' opcional.

    Sintaxis en el lenguaje:
        si (condicion) {
            // rama verdadera
        }

        si (condicion) {
            // rama verdadera
        } sino {
            // rama falsa
        }

    Atributos:
        condition (ASTNode)          : expresión booleana a evaluar
        then_body (List[ASTNode])    : lista de sentencias de la rama 'si'
        else_body (Optional[List[ASTNode]]): lista de sentencias de la rama
                                      'sino'; None si no existe rama alternativa
    """
    condition : ASTNode                    # Condición a evaluar (debe resultar en bool)
    then_body : List[ASTNode]             # Sentencias ejecutadas si la condición es verdadera
    else_body : Optional[List[ASTNode]] = None  # Sentencias ejecutadas si la condición es falsa


# =============================================================================
# NODO RAÍZ DEL PROGRAMA
# =============================================================================

@dataclass
class Program(ASTNode):
    """
    Nodo raíz del AST: representa el programa completo.

    Es el único nodo que el parser devuelve al nivel superior; todos
    los demás nodos son descendientes de éste.

    El intérprete comienza la ejecución iterando sobre 'statements'.

    Atributos:
        statements (List[ASTNode]): lista ordenada de todas las sentencias
                                    del programa, en el orden en que
                                    deben ejecutarse.

    Se usa field(default_factory=list) en lugar de statements=[] para
    evitar el problema de mutable default arguments en Python: si usáramos
    un literal [] como valor por defecto, todas las instancias de Program
    compartirían la misma lista, causando bugs difíciles de detectar.
    """
    statements: List[ASTNode] = field(default_factory=list)