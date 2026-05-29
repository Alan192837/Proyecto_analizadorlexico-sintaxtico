# =============================================================================
# interpreter.py — Ejecutor / Intérprete del AST
# =============================================================================
#
# PROPÓSITO GENERAL:
# Este módulo implementa un intérprete de árbol de sintaxis abstracta (AST)
# para el mini-lenguaje. Su función es recorrer el AST nodo por nodo y ejecutar
# cada instrucción, manteniendo el estado del programa en una tabla de símbolos
# (donde se registran las variables con sus tipos y valores actuales).
#
# ARQUITECTURA — Patrón Visitor implícito:
#   El método _execute() actúa como despachador: identifica el tipo concreto de
#   cada nodo usando isinstance() y llama al método especializado correspondiente.
#   Esta técnica es simple de implementar pero acumula lógica en un solo lugar;
#   una alternativa más escalable sería el patrón Visitor formal con doble despacho.
#
# FLUJO DE EJECUCIÓN:
#   run(program)
#     └── _execute(stmt)              ← itera y despacha cada sentencia
#           ├── _exec_decl / _exec_asign / ...   ← ejecutan la sentencia
#           └── _eval(expr)           ← evalúa expresiones dentro de la sentencia
#                 ├── _eval_binop / _eval_logica  ← sub-evaluadores especializados
#                 └── _verificar_tipo(...)        ← valida tipos antes de almacenar
#
# LIMITACIONES CONOCIDAS:
#   - No soporta funciones ni procedimientos definidos por el usuario.
#   - No hay ámbitos (scopes) anidados: solo existe un scope global.
#   - La división siempre es entera (//) porque el lenguaje no tiene tipo decimal.
# =============================================================================

from ast_nodes import *           # Importa todos los nodos del AST (VarDecl, BinOp, etc.)
from symbol_table import SymbolTable  # Tabla de símbolos: almacena nombre, tipo y valor de variables


class Interpreter:
    """
    Intérprete de árbol (tree-walking interpreter) para el mini-lenguaje.

    Recorre el AST producido por el parser y ejecuta cada nodo directamente,
    sin compilar a código intermedio ni bytecode. Es sencillo de implementar
    y depurar, aunque menos eficiente que una VM o compilador para programas
    de gran tamaño.

    Uso típico:
        interp = Interpreter()
        interp.run(ast)          # Ejecuta el programa completo
        interp.dump_symbols()    # Muestra el estado final de las variables
    """

    def __init__(self):
        """
        Inicializa el intérprete con una tabla de símbolos vacía.

        La tabla de símbolos es el único estado interno persistente del intérprete:
        acumula todas las variables declaradas durante la ejecución con su tipo y valor.
        """
        # SymbolTable actúa como el "heap" simplificado de este intérprete.
        # Todo el estado del programa vive aquí durante la ejecución.
        self.symbols = SymbolTable()

    # =========================================================================
    # PUNTO DE ENTRADA
    # =========================================================================

    def run(self, program: Program):
        """
        Ejecuta el programa completo recorriendo su lista de sentencias en orden.

        Parámetros:
            program (Program): nodo raíz del AST que contiene la secuencia de
                               sentencias del programa. Puede ser None si el
                               análisis sintáctico o léxico encontró errores previos.

        Retorna:
            None. La ejecución produce efectos secundarios: salida en consola
            y modificaciones en la tabla de símbolos.
        """
        # Si el AST es None, el parser no pudo construirlo por errores en el código
        # fuente. No tiene sentido intentar ejecutar un árbol inválido o inexistente.
        if program is None:
            print("[Interprete] No se ejecuto: hubo errores en el analisis.")
            return

        # Cada elemento de program.statements es un nodo de sentencia completa.
        # Se ejecutan en el mismo orden en que aparecen en el código fuente,
        # garantizando ejecución secuencial y determinista.
        for stmt in program.statements:
            self._execute(stmt)

    # =========================================================================
    # DESPACHADOR DE SENTENCIAS
    # =========================================================================

    def _execute(self, node: ASTNode):
        """
        Despacha la ejecución de un nodo de sentencia al método correcto según su tipo.

        Implementa el patrón Visitor de forma simplificada: en lugar de un método
        visit() polimórfico, usa isinstance() para identificar el tipo concreto y
        delegar al método especializado. Este enfoque centraliza el despacho y facilita
        agregar nuevos tipos de sentencia en un solo lugar.

        Parámetros:
            node (ASTNode): nodo de sentencia del AST. Se espera que sea una instancia
                            de VarDecl, Assign, PrintStmt, ReadStmt o IfStmt.

        Retorna:
            None. La ejecución real ocurre en los métodos _exec_* invocados.

        Lanza:
            RuntimeError si el tipo de nodo no está contemplado, lo que indicaría
            un fallo de sincronía entre el parser y el intérprete.
        """
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
            # Este caso solo debería ocurrir si el parser genera un nodo nuevo
            # que el intérprete aún no implementa. Es un error de desarrollo,
            # no del usuario final.
            raise RuntimeError(f"[Interprete] Nodo de sentencia desconocido: {type(node).__name__}")

    # =========================================================================
    # EJECUCION DE SENTENCIAS
    # =========================================================================

    def _exec_decl(self, node: VarDecl):
        """
        Ejecuta una declaración de variable con valor inicial (ej: entero x = 5).

        Evalúa la expresión del lado derecho, verifica la compatibilidad de tipo
        y registra la nueva variable en la tabla de símbolos.

        Parámetros:
            node (VarDecl): nodo AST que representa la declaración, con campos:
                - name (str)     : nombre de la variable a declarar.
                - var_type (str) : tipo declarado ('entero', 'cadena' o 'logico').
                - value (ASTNode): expresión que produce el valor inicial.

        Retorna:
            None. El efecto es añadir la variable a self.symbols.
        """
        # Paso 1: evaluar la expresión del lado derecho para obtener el valor bruto
        valor = self._eval(node.value)

        # Paso 2: verificar y convertir al tipo declarado antes de almacenar.
        # Esto garantiza que la tabla de símbolos nunca contenga un valor de tipo incorrecto.
        valor = self._verificar_tipo(node.var_type, valor, node.name)

        # Paso 3: registrar la variable con su tipo y valor inicial en la tabla
        self.symbols.declare(node.name, node.var_type, valor)

    def _exec_asign(self, node: Assign):
        """
        Ejecuta una reasignación de valor a una variable ya existente (ej: x = x + 1).

        A diferencia de _exec_decl, no crea la variable: asume que ya fue declarada
        previamente. La verificación de tipo usa el tipo original de la declaración,
        ya que el lenguaje es estáticamente tipado (el tipo no cambia).

        Parámetros:
            node (Assign): nodo AST de la asignación, con campos:
                - name (str)     : nombre de la variable destino.
                - value (ASTNode): expresión que produce el nuevo valor.

        Retorna:
            None. El efecto es actualizar el valor de la variable en self.symbols.
        """
        # Evaluar el nuevo valor antes de consultar el tipo, para detectar
        # errores de evaluación independientemente de errores de tipo.
        valor = self._eval(node.value)

        # Recuperar el tipo declarado originalmente para aplicar la misma restricción
        # de tipo que en la declaración. El tipo es inmutable tras la declaración.
        tipo_declarado = self.symbols.get_type(node.name)
        valor = self._verificar_tipo(tipo_declarado, valor, node.name)

        self.symbols.assign(node.name, valor)

    def _exec_mostrar(self, node: PrintStmt):
        """
        Ejecuta una instrucción de impresión en consola (ej: mostrar(x + 1)).

        Evalúa la expresión y muestra el resultado adaptando la representación
        de los booleanos a la sintaxis del mini-lenguaje (verdadero/falso)
        en lugar de la representación Python (True/False).

        Parámetros:
            node (PrintStmt): nodo AST con el campo:
                - expr (ASTNode): expresión cuyo valor se imprimirá.

        Retorna:
            None. El efecto es escribir una línea en stdout.
        """
        valor = self._eval(node.expr)

        # Los booleanos de Python se mostrarían como "True"/"False", pero el
        # mini-lenguaje usa "verdadero"/"falso" en su sintaxis. Se adapta aquí
        # para que la salida sea coherente con el lenguaje que el usuario escribe.
        if isinstance(valor, bool):
            print("verdadero" if valor else "falso")
        else:
            print(valor)

    def _exec_leer(self, node: ReadStmt):
        """
        Ejecuta una instrucción de lectura desde la entrada estándar (ej: leer(x)).

        Lee una cadena cruda desde stdin y la convierte al tipo declarado de la
        variable destino. Consulta la tabla de símbolos para conocer el tipo esperado
        antes de intentar la conversión.

        Parámetros:
            node (ReadStmt): nodo AST con el campo:
                - name (str): nombre de la variable donde se almacenará la entrada.

        Retorna:
            None. El efecto es actualizar el valor de la variable en self.symbols.

        Advertencia:
            Si la conversión falla (ej: el usuario escribe "abc" para un entero),
            el valor se guarda como cadena con una advertencia en consola. Esto puede
            causar errores de tipo en operaciones posteriores del programa.

        # SUGERENCIA: Sería más robusto lanzar RuntimeError en el except en lugar de
        # degradar silenciosamente el tipo. El lenguaje es estáticamente tipado, y
        # guardar un str en una variable 'entero' viola esa restricción.
        """
        # Consultar el tipo declarado para saber cómo parsear la entrada del usuario
        tipo = self.symbols.get_type(node.name)

        # input() siempre devuelve str. El mensaje entre corchetes orienta al usuario
        # indicando qué variable se está leyendo y qué tipo se espera.
        raw = input(f"[leer] '{node.name}' ({tipo}): ")

        try:
            if tipo == 'entero':
                # int() lanza ValueError si el texto no representa un entero válido
                valor = int(raw)
            elif tipo == 'logico':
                # Se acepta un conjunto amplio de representaciones de "verdadero"
                # para mayor comodidad. Todo lo demás se interpreta como falso.
                # Esta comparación nunca lanza excepción, por lo que el except
                # solo aplica al caso 'entero'.
                valor = raw.strip().lower() in ('verdadero', 'true', '1', 'si')
            else:
                # Para 'cadena', cualquier texto es válido sin conversión
                valor = raw
        except ValueError:
            # Solo se llega aquí si int(raw) falló para tipo 'entero'.
            # Se notifica al usuario y se guarda el valor como cadena como fallback.
            print(f"[leer] Advertencia: '{raw}' no es un {tipo} valido. Se guarda como cadena.")
            valor = raw

        self.symbols.assign(node.name, valor)

    def _exec_si(self, node: IfStmt):
        """
        Ejecuta una sentencia condicional (ej: si (condicion) { ... } sino { ... }).

        Evalúa la condición exactamente una vez y ejecuta secuencialmente las
        sentencias de la rama que corresponda al resultado.

        Parámetros:
            node (IfStmt): nodo AST del condicional, con campos:
                - condition (ASTNode)      : expresión lógica que decide la rama.
                - then_body (list[ASTNode]): sentencias de la rama verdadera.
                - else_body (list[ASTNode] | None): sentencias de la rama falsa,
                  o None si el usuario no escribió una cláusula 'sino'.

        Retorna:
            None. El efecto es ejecutar las sentencias de la rama seleccionada.
        """
        # Evaluar la condición una sola vez; el resultado determina qué rama ejecutar.
        condicion = self._eval(node.condition)

        if condicion:
            # Rama verdadera ('entonces'): se ejecutan sus sentencias en orden
            for stmt in node.then_body:
                self._execute(stmt)
        elif node.else_body is not None:
            # Rama falsa ('sino'): solo se entra si la condición fue falsa
            # Y si existe una cláusula sino (else_body no es None).
            # La comprobación de None es necesaria porque 'sino' es opcional en la gramática.
            for stmt in node.else_body:
                self._execute(stmt)

    # =========================================================================
    # EVALUADOR DE EXPRESIONES
    # =========================================================================

    def _eval(self, node: ASTNode):
        """
        Evalúa recursivamente un nodo de expresión y devuelve su valor Python.

        Es el núcleo del intérprete: convierte cada tipo de nodo de expresión en
        su valor calculado. Usa recursión natural para manejar expresiones compuestas;
        por ejemplo, (a + b) * c se evalúa de adentro hacia afuera a través de
        llamadas recursivas anidadas.

        Parámetros:
            node (ASTNode): nodo de expresión del AST. Puede ser Number,
                StringLiteral, BoolLiteral, Identifier, UnaryMinus,
                BinOp, LogicOp o NotOp.

        Retorna:
            El valor Python del nodo evaluado: int para Number, str para
            StringLiteral, bool para BoolLiteral o comparaciones, etc.

        Lanza:
            RuntimeError si el nodo no corresponde a ningún tipo de expresión
            conocido, lo que indicaría un fallo en el parser o una expresión
            no implementada en el intérprete.
        """

        # --- Literales: ya tienen su valor final; simplemente se extrae ---

        if isinstance(node, Number):
            # El lexer ya convirtió el texto a int/float; aquí solo se retorna.
            return node.value

        if isinstance(node, StringLiteral):
            return node.value

        if isinstance(node, BoolLiteral):
            return node.value

        # --- Identificador: resolución de nombre en la tabla de símbolos ---
        if isinstance(node, Identifier):
            # get() se encarga de lanzar un error claro si la variable no existe,
            # evitando exponer KeyError de Python al usuario.
            return self.symbols.get(node.name)

        # --- Negación aritmética unaria: invierte el signo de la expresión ---
        if isinstance(node, UnaryMinus):
            # La recursión permite manejar casos como -(-x) o -(a + b) correctamente.
            return -self._eval(node.operand)

        # --- Operación binaria aritmética o relacional (ej: a + b, x >= 0) ---
        if isinstance(node, BinOp):
            # Se delega a un método especializado para mantener _eval legible
            return self._eval_binop(node)

        # --- Operación lógica binaria con cortocircuito (ej: a y b, x o y) ---
        if isinstance(node, LogicOp):
            return self._eval_logica(node)

        # --- Negación lógica unaria (ej: no condicion) ---
        if isinstance(node, NotOp):
            # 'not' de Python aplica la negación booleana directamente sobre
            # el valor evaluado del operando.
            return not self._eval(node.operand)

        # Si llegamos aquí, el parser generó un nodo de expresión no implementado.
        raise RuntimeError(f"[Interprete] Nodo de expresion desconocido: {type(node).__name__}")

    def _eval_binop(self, node: BinOp):
        """
        Evalúa una operación binaria aritmética o relacional.

        Aplica evaluación ansiosa (eager): evalúa ambos operandos antes de aplicar
        el operador. Esto es correcto para aritmética y comparaciones, pero no para
        operaciones lógicas (que requieren cortocircuito y se manejan en _eval_logica).

        Parámetros:
            node (BinOp): nodo AST con los campos:
                - left (ASTNode) : operando izquierdo.
                - right (ASTNode): operando derecho.
                - op (str)       : operador como cadena de texto.
                  Aritméticos  : '+', '-', '*', '/'
                  Relacionales : '>', '<', '>=', '<=', '==', '!='

        Retorna:
            int o str para operadores aritméticos (+ puede concatenar cadenas).
            bool para operadores relacionales.

        Lanza:
            RuntimeError si se intenta dividir entre cero o si el operador es desconocido.
        """
        # Evaluar ambos operandos primero; en operaciones aritméticas y relacionales
        # siempre necesitamos los dos valores antes de calcular el resultado.
        izq = self._eval(node.left)
        der = self._eval(node.right)
        op  = node.op

        # --- Operadores aritméticos ---

        if op == '+':
            # Sobrecarga del '+': si algún operando es cadena, se realiza concatenación
            # en lugar de suma. Permite expresiones como: "Resultado: " + x
            if isinstance(izq, str) or isinstance(der, str):
                return str(izq) + str(der)
            return izq + der

        if op == '-':
            return izq - der

        if op == '*':
            return izq * der

        if op == '/':
            # Verificación explícita de división por cero para dar un mensaje de error
            # en el idioma del mini-lenguaje, en lugar de exponer ZeroDivisionError de Python.
            if der == 0:
                raise RuntimeError("[Interprete] Error: division entre cero.")

            # Se usa división entera (//) porque el mini-lenguaje solo tiene tipo 'entero'.
            # SUGERENCIA: Si en el futuro se agrega un tipo 'decimal' o 'flotante',
            # habría que distinguir entre // y / según el tipo de los operandos.
            return izq // der

        # --- Operadores relacionales: producen un resultado booleano ---

        if op == '>':  return izq >  der
        if op == '<':  return izq <  der
        if op == '>=': return izq >= der
        if op == '<=': return izq <= der
        if op == '==': return izq == der
        if op == '!=': return izq != der

        # Operador no reconocido: implica que el parser generó un BinOp con un
        # operador que el intérprete no implementa. Es un error de desarrollo.
        raise RuntimeError(f"[Interprete] Operador desconocido: '{op}'")

    def _eval_logica(self, node: LogicOp):
        """
        Evalúa operaciones lógicas binarias 'y' / 'o' con evaluación de cortocircuito.

        El cortocircuito (short-circuit evaluation) evita evaluar el operando derecho
        cuando el izquierdo ya determina el resultado. Esto no solo optimiza, sino que
        también permite patrones seguros como: "x != 0 y (100 / x > 2)", donde la
        división nunca se ejecuta si x es 0.

        Parámetros:
            node (LogicOp): nodo AST con los campos:
                - op (str)       : operador lógico ('y' u 'o').
                - left (ASTNode) : operando izquierdo.
                - right (ASTNode): operando derecho.

        Retorna:
            bool: resultado de la operación lógica.

        Lanza:
            RuntimeError si el operador no es 'y' ni 'o'.
        """
        if node.op == 'y':
            # 'and' de Python implementa cortocircuito nativamente:
            # si el lado izquierdo es False, el lado derecho no se evalúa.
            # El cast explícito a bool garantiza que el resultado sea siempre
            # True o False, incluso si los operandos son enteros (0 o distinto de 0).
            return bool(self._eval(node.left)) and bool(self._eval(node.right))

        if node.op == 'o':
            # Análogamente, 'or' omite la evaluación del derecho si el izquierdo es True.
            return bool(self._eval(node.left)) or bool(self._eval(node.right))

        raise RuntimeError(f"[Interprete] Operador logico desconocido: '{node.op}'")

    # =========================================================================
    # VERIFICACION DE TIPO
    # =========================================================================

    def _verificar_tipo(self, tipo_declarado: str, valor, nombre_var: str):
        """
        Verifica y convierte 'valor' al tipo declarado de la variable.

        Implementa el sistema de tipos en tiempo de ejecución: garantiza que la
        tabla de símbolos solo almacene valores del tipo correcto. Es el equivalente
        a un cast fuertemente tipado que falla con un mensaje descriptivo si la
        conversión no es posible.

        Parámetros:
            tipo_declarado (str): tipo esperado para la variable;
                                  valores posibles: 'entero', 'cadena', 'logico'.
            valor (any)         : valor a verificar/convertir, producido por _eval().
            nombre_var (str)    : nombre de la variable, usado solo en el mensaje de error.

        Retorna:
            El valor convertido al tipo correcto:
                'entero' → int | 'cadena' → str | 'logico' → bool

        Lanza:
            RuntimeError con un mensaje descriptivo si la conversión no es posible
            (ej: intentar asignar "hola" a una variable de tipo 'entero').
        """
        try:
            if tipo_declarado == 'entero':
                # Se bloquea explícitamente la conversión bool → int porque en Python
                # bool es subclase de int (True == 1, False == 0). Sin este chequeo,
                # asignar 'verdadero' a una variable entera pasaría silenciosamente.
                if isinstance(valor, bool):
                    raise TypeError("No se puede asignar un logico a un entero.")
                return int(valor)

            if tipo_declarado == 'cadena':
                # str() nunca lanza excepción: todo objeto Python tiene representación textual.
                return str(valor)

            if tipo_declarado == 'logico':
                # Caso más común: el valor ya es bool, se retorna directamente
                if isinstance(valor, bool):
                    return valor
                # Conversión entero → lógico: semánticamente equivalente a verificar si
                # el número es distinto de cero, convención estándar en muchos lenguajes.
                if isinstance(valor, int):
                    return bool(valor)
                # Cadenas u otros tipos no tienen conversión lógica definida
                raise TypeError("Valor no convertible a logico.")

        except (TypeError, ValueError) as exc:
            # Se capturan ambos tipos porque int() puede lanzar ValueError (ej: int("abc"))
            # y las verificaciones manuales lanzan TypeError.
            raise RuntimeError(
                f"[Interprete] Error de tipo en '{nombre_var}': "
                f"no se puede guardar '{valor}' ({type(valor).__name__}) "
                f"en una variable de tipo '{tipo_declarado}'. "
                f"Detalle: {exc}"
            )

        # SUGERENCIA: Esta línea es código muerto (dead code). Los tres bloques 'if'
        # anteriores siempre retornan explícitamente o lanzan excepción, por lo que
        # 'return valor' nunca llega a ejecutarse. Debería eliminarse o reemplazarse
        # por un bloque 'else' que maneje tipos no reconocidos con un RuntimeError.
        return valor

    # =========================================================================
    # ACCESO EXTERNO
    # =========================================================================

    def dump_symbols(self):
        """
        Imprime en consola el estado final de la tabla de símbolos.

        Útil para depuración: muestra todas las variables declaradas, sus tipos
        y sus valores en el momento en que se llama (normalmente al terminar
        la ejecución del programa).

        Retorna:
            None. El efecto es escribir en stdout.
        """
        self.symbols.dump()

    def save_symbols(self, filename="tabla_simbolos.txt"):
        """
        Persiste el contenido de la tabla de símbolos en un archivo de texto.

        Parámetros:
            filename (str): ruta y nombre del archivo destino.
                            Por defecto: "tabla_simbolos.txt" en el directorio actual.
                            Si el archivo ya existe, será sobreescrito.

        Retorna:
            None. El efecto es crear o sobreescribir el archivo indicado.
        """
        self.symbols.save_to_file(filename)
