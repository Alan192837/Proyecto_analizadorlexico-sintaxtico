# =============================================================================
# interpreter.py — Ejecutor / Interprete del AST
# =============================================================================
# Responsabilidad: recorrer el AST nodo por nodo y ejecutar cada instruccion,
# manteniendo el estado en la tabla de simbolos.
#
# Patron: Visitor implicito — el metodo execute() despacha segun el tipo
# de nodo usando isinstance().
# =============================================================================

from ast_nodes import *
from symbol_table import SymbolTable


class Interpreter:
    """
    Interprete arbol-walking para el mini-lenguaje.

    Uso:
        interp = Interpreter()
        interp.run(ast)
        interp.dump_symbols()
    """

    def __init__(self):
        self.symbols = SymbolTable()

    # =========================================================================
    # PUNTO DE ENTRADA
    # =========================================================================

    def run(self, program: Program):
        """Ejecuta el programa completo. Si el AST es None (hubo errores), no hace nada."""
        if program is None:
            print("[Interprete] No se ejecuto: hubo errores en el analisis.")
            return
        for stmt in program.statements:
            self._execute(stmt)

    # =========================================================================
    # DESPACHADOR DE SENTENCIAS
    # =========================================================================

    def _execute(self, node: ASTNode):
        """Ejecuta un nodo de sentencia."""
        if isinstance(node, VarDecl):
            self._exec_decl(node)
        elif isinstance(node, Assign):
            self._exec_asign(node)
        elif isinstance(node, PrintStmt):
            self._exec_mostrar(node)
        elif isinstance(node, ReadStmt):
            self._exec_leer(node)
        elif isinstance(node, IfStmt):
            self._exec_si(node)
        else:
            raise RuntimeError(f"[Interprete] Nodo de sentencia desconocido: {type(node).__name__}")

    # =========================================================================
    # EJECUCION DE SENTENCIAS
    # =========================================================================

    def _exec_decl(self, node: VarDecl):
        """Declara una variable y le asigna el valor inicial evaluado."""
        valor = self._eval(node.value)
        valor = self._verificar_tipo(node.var_type, valor, node.name)
        self.symbols.declare(node.name, node.var_type, valor)

    def _exec_asign(self, node: Assign):
        """Reasigna el valor de una variable ya declarada."""
        valor = self._eval(node.value)
        tipo_declarado = self.symbols.get_type(node.name)
        valor = self._verificar_tipo(tipo_declarado, valor, node.name)
        self.symbols.assign(node.name, valor)

    def _exec_mostrar(self, node: PrintStmt):
        """Evalua la expresion e imprime el resultado."""
        valor = self._eval(node.expr)
        # Booleanos se muestran con la sintaxis del lenguaje
        if isinstance(valor, bool):
            print("verdadero" if valor else "falso")
        else:
            print(valor)

    def _exec_leer(self, node: ReadStmt):
        """Lee un valor del usuario y lo guarda en la variable."""
        tipo = self.symbols.get_type(node.name)
        raw = input(f"[leer] '{node.name}' ({tipo}): ")
        try:
            if tipo == 'entero':
                valor = int(raw)
            elif tipo == 'logico':
                valor = raw.strip().lower() in ('verdadero', 'true', '1', 'si')
            else:
                valor = raw   # cadena: cualquier texto es valido
        except ValueError:
            print(f"[leer] Advertencia: '{raw}' no es un {tipo} valido. Se guarda como cadena.")
            valor = raw
        self.symbols.assign(node.name, valor)

    def _exec_si(self, node: IfStmt):
        """Evalua la condicion y ejecuta la rama correspondiente."""
        condicion = self._eval(node.condition)
        if condicion:
            for stmt in node.then_body:
                self._execute(stmt)
        elif node.else_body is not None:
            for stmt in node.else_body:
                self._execute(stmt)

    # =========================================================================
    # EVALUADOR DE EXPRESIONES
    # =========================================================================

    def _eval(self, node: ASTNode):
        """Evalua un nodo de expresion y devuelve su valor Python."""

        # Literales
        if isinstance(node, Number):
            return node.value
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, BoolLiteral):
            return node.value

        # Referencia a variable
        if isinstance(node, Identifier):
            return self.symbols.get(node.name)

        # Menos unario: -expr
        if isinstance(node, UnaryMinus):
            return -self._eval(node.operand)

        # Operacion binaria aritmetica o relacional
        if isinstance(node, BinOp):
            return self._eval_binop(node)

        # Operacion logica binaria (y / o)
        if isinstance(node, LogicOp):
            return self._eval_logica(node)

        # Negacion logica (no)
        if isinstance(node, NotOp):
            return not self._eval(node.operand)

        raise RuntimeError(f"[Interprete] Nodo de expresion desconocido: {type(node).__name__}")

    def _eval_binop(self, node: BinOp):
        """Evalua una operacion binaria aritmetica o relacional."""
        izq = self._eval(node.left)
        der = self._eval(node.right)
        op  = node.op

        # Aritmeticos
        if op == '+':
            # Si alguno es cadena, concatena
            if isinstance(izq, str) or isinstance(der, str):
                return str(izq) + str(der)
            return izq + der
        if op == '-':
            return izq - der
        if op == '*':
            return izq * der
        if op == '/':
            if der == 0:
                raise RuntimeError("[Interprete] Error: division entre cero.")
            return izq // der   # division entera

        # Relacionales
        if op == '>':  return izq >  der
        if op == '<':  return izq <  der
        if op == '>=': return izq >= der
        if op == '<=': return izq <= der
        if op == '==': return izq == der
        if op == '!=': return izq != der

        raise RuntimeError(f"[Interprete] Operador desconocido: '{op}'")

    def _eval_logica(self, node: LogicOp):
        """Evalua operaciones logicas 'y' / 'o' con cortocircuito."""
        if node.op == 'y':
            # Cortocircuito: si izquierdo es falso, no evalua el derecho
            return bool(self._eval(node.left)) and bool(self._eval(node.right))
        if node.op == 'o':
            # Cortocircuito: si izquierdo es verdadero, no evalua el derecho
            return bool(self._eval(node.left)) or bool(self._eval(node.right))
        raise RuntimeError(f"[Interprete] Operador logico desconocido: '{node.op}'")

    # =========================================================================
    # VERIFICACION DE TIPO
    # =========================================================================

    def _verificar_tipo(self, tipo_declarado: str, valor, nombre_var: str):
        """
        Intenta convertir 'valor' al tipo declarado de la variable.
        Lanza RuntimeError si la conversion no es posible.
        """
        try:
            if tipo_declarado == 'entero':
                if isinstance(valor, bool):
                    raise TypeError("No se puede asignar un logico a un entero.")
                return int(valor)
            if tipo_declarado == 'cadena':
                return str(valor)
            if tipo_declarado == 'logico':
                if isinstance(valor, bool):
                    return valor
                if isinstance(valor, int):
                    return bool(valor)
                raise TypeError("Valor no convertible a logico.")
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"[Interprete] Error de tipo en '{nombre_var}': "
                f"no se puede guardar '{valor}' ({type(valor).__name__}) "
                f"en una variable de tipo '{tipo_declarado}'. "
                f"Detalle: {exc}"
            )
        return valor

    # =========================================================================
    # ACCESO EXTERNO
    # =========================================================================

    def dump_symbols(self):
        """Imprime la tabla de simbolos (estado final del programa)."""
        self.symbols.dump()

    def save_symbols(self, filename="tabla_simbolos.txt"):
        """Ordena a la tabla de símbolos que se guarde en un archivo."""
        self.symbols.save_to_file(filename)