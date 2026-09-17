"""
=============================================================================
semantic.py — Analizador Semántico
=============================================================================
Propósito general:
    Comprueba todo lo que la gramática NO puede comprobar. El análisis
    sintáctico sabe que "a + b" está bien FORMADO, pero no sabe si 'a' existe
    ni si sumar 'a' con 'b' tiene sentido. De eso se encarga esta fase.

    Es la TERCERA FASE del compilador:
        Texto → [Lexer] → Tokens → [Parser] → AST → [Semántico] → AST validado

    Si encuentra algún error, el programa NO se ejecuta: main.py cancela la
    fase de interpretación. Un programa con errores de tipo no debe correr.

=============================================================================
QUÉ COMPRUEBA (requisitos de la práctica)
=============================================================================
    1. Toda variable usada en el cuerpo del programa fue declarada antes,
       y se usa dentro de su ÁMBITO (alcance).
    2. Ninguna variable se declara dos veces en el mismo ámbito.
    3. En una asignación, el tipo de la variable de la izquierda y el tipo de
       la expresión de la derecha son el mismo.
    4. En un condicional 'si', la expresión es de tipo lógico y las sentencias
       de sus ramas no tienen errores de tipo.
    5. En un bucle 'mientras', la expresión es de tipo lógico y las sentencias
       de su cuerpo no tienen errores de tipo.
    6. El argumento de mostrar() tiene un tipo válido del lenguaje.
    7. Las expresiones que combinan una o dos subexpresiones respetan los tipos
       de cada operador (ver TABLA DE TIPOS más abajo).

=============================================================================
UNA SOLA PASADA
=============================================================================
    Todo el análisis se hace en UN ÚNICO recorrido del AST. No hay una pasada
    previa que recolecte declaraciones ni una posterior que verifique tipos:
    cada nodo se visita exactamente una vez, y al visitarlo se resuelven sus
    nombres, se calcula su tipo y se emiten sus errores.

    Consecuencia de diseño: una variable debe declararse ANTES de usarse en el
    texto del programa, igual que en C o Pascal.

    Para que una sola pasada pueda reportar TODOS los errores (y no solo el
    primero), el análisis nunca se detiene ante un error: marca la expresión
    culpable con el tipo especial TIPO_ERROR y continúa.

=============================================================================
TABLA DE TIPOS DE LAS EXPRESIONES
=============================================================================
    Operador        Operandos válidos              Resultado
    ------------------------------------------------------------------
    +               entero + entero                entero
                    cadena + (cualquier tipo)      cadena  (concatenación)
                    (cualquier tipo) + cadena      cadena  (concatenación)
                    entero + logico                ERROR E-S05
    - * /           entero, entero                 entero
    > < >= <=       ambos entero, o ambos cadena   logico
    == !=           ambos del MISMO tipo           logico
    y  o            logico, logico                 logico
    no              logico                         logico
    - (unario)      entero                         entero

    El caso 'entero + logico' es precisamente el ejemplo que da el enunciado
    de la práctica como error que debe detectar esta fase.

=============================================================================
ESTRUCTURAS DE DATOS QUE USA
=============================================================================
    - AST            (ast_nodes.py)    : estructura jerárquica que recorre.
    - Tabla de símbolos (symbol_table.py): la ALIMENTA con nombre, tipo,
                                          ámbito, línea y columna de cada
                                          variable declarada.
    - Pila semántica (PilaSemantica)   : pila de tipos que emula el
                                          funcionamiento de un traductor
                                          dirigido por sintaxis (ver clase).
=============================================================================
"""

from ast_nodes import *
from symbol_table import SymbolTable


# =============================================================================
# 1. CONSTANTES DE TIPOS
# =============================================================================

# Los tres tipos reales del lenguaje, tal como se escriben en el fuente.
TIPO_ENTERO = 'entero'
TIPO_CADENA = 'cadena'
TIPO_LOGICO = 'logico'

# Tipo especial que NO existe en el lenguaje: es un marcador interno que se
# asigna a una expresión que ya provocó un error.
#
# Su función es EVITAR ERRORES EN CASCADA. Sin él, un programa como:
#       entero x = "hola" + 1;      ← 1 error real
#       mostrar(x * 2);             ← x quedaría "sin tipo"
# generaría errores encadenados que confundirían al usuario. Con el marcador,
# cualquier operación sobre una expresión ya errónea se calla, porque su causa
# raíz ya fue reportada una vez.
TIPO_ERROR = 'error'

# Conjunto de tipos válidos del lenguaje, para validaciones rápidas
TIPOS_VALIDOS = {TIPO_ENTERO, TIPO_CADENA, TIPO_LOGICO}


# =============================================================================
# 2. REPRESENTACIÓN DE UN ERROR SEMÁNTICO
# =============================================================================

class ErrorSemantico:
    """
    Un error semántico con toda la información para localizarlo y entenderlo.

    Se usa una clase en lugar de un simple string porque el reporte debe poder
    ordenarse, filtrarse y consultarse por línea o por código; las pruebas
    automatizadas, por ejemplo, comparan los códigos y las posiciones sin
    depender del texto exacto del mensaje.

    Atributos:
        codigo  (str): identificador estable del tipo de error, ej. 'E-S05'
        mensaje (str): explicación en lenguaje natural
        linea   (int): línea del fuente donde está el error
        columna (int): columna del fuente donde está el error
        ayuda   (str): sugerencia concreta de cómo corregirlo
    """

    def __init__(self, codigo: str, mensaje: str, linea: int, columna: int, ayuda: str = ""):
        self.codigo  = codigo
        self.mensaje = mensaje
        self.linea   = linea
        self.columna = columna
        self.ayuda   = ayuda

    def __str__(self):
        """Formato de una línea, el que se imprime en pantalla y en el reporte."""
        return (f"[Semantico] Error {self.codigo} en linea {self.linea}, "
                f"columna {self.columna}: {self.mensaje}")

    def detallado(self) -> str:
        """Formato de varias líneas, con la sugerencia de corrección incluida."""
        texto = str(self)
        if self.ayuda:
            texto += f"\n              Sugerencia: {self.ayuda}"
        return texto


# =============================================================================
# 3. PILA SEMÁNTICA
# =============================================================================

class PilaSemantica:
    """
    Pila de tipos usada durante la verificación de expresiones.

    Es la estructura clásica de un traductor dirigido por sintaxis: al analizar
    una expresión, el tipo de cada subexpresión se APILA, y cada operador
    DESAPILA los tipos de sus operandos y APILA el tipo del resultado.

    Traza de "a + b > 5" (con a y b enteros):

        analiza 'a'   → apila entero                    pila: [entero]
        analiza 'b'   → apila entero                    pila: [entero, entero]
        operador '+'  → desapila 2, apila entero        pila: [entero]
        analiza '5'   → apila entero                    pila: [entero, entero]
        operador '>'  → desapila 2, apila logico        pila: [logico]

    Al terminar queda un solo tipo en la pila: el de la expresión completa.
    Ese invariante es lo que hace comprobable el análisis, y por eso la pila
    se verifica con esta_vacia() al final de cada sentencia.
    """

    def __init__(self):
        self._pila: list[str] = []
        # Profundidad máxima alcanzada: dato de interés para el reporte, porque
        # refleja la complejidad de la expresión más anidada del programa.
        self._maxima = 0

    def apilar(self, tipo: str):
        """Coloca un tipo en la cima de la pila."""
        self._pila.append(tipo)
        self._maxima = max(self._maxima, len(self._pila))

    def desapilar(self) -> str:
        """
        Retira y devuelve el tipo de la cima.

        Si la pila estuviera vacía devuelve TIPO_ERROR en lugar de reventar:
        el analizador debe poder terminar su pasada aunque algo haya ido mal.
        """
        if not self._pila:
            return TIPO_ERROR
        return self._pila.pop()

    def cima(self) -> str:
        """Consulta el tipo de la cima sin retirarlo."""
        return self._pila[-1] if self._pila else TIPO_ERROR

    def esta_vacia(self) -> bool:
        """True si no queda ningún tipo pendiente."""
        return len(self._pila) == 0

    def vaciar(self):
        """Descarta todo el contenido (se llama al terminar cada sentencia)."""
        self._pila.clear()

    def profundidad_maxima(self) -> int:
        """Mayor número de tipos que llegaron a convivir en la pila."""
        return self._maxima

    def __len__(self):
        return len(self._pila)


# =============================================================================
# 4. ANALIZADOR SEMÁNTICO
# =============================================================================

class SemanticAnalyzer:
    """
    Recorre el AST una sola vez verificando tipos, ámbitos y argumentos.

    Uso típico:
        analizador = SemanticAnalyzer()
        errores = analizador.analyze(ast)
        if not errores:
            interprete.run(ast)

    Atributos públicos:
        tabla    (SymbolTable)         : tabla de símbolos que alimenta y consulta
        pila     (PilaSemantica)       : pila de tipos de las expresiones
        errores  (list[ErrorSemantico]): errores encontrados, en orden de aparición
    """

    # Nombre legible de cada tipo de operador, para los mensajes de error
    _NOMBRE_OPERADOR = {
        '+': 'suma', '-': 'resta', '*': 'multiplicacion', '/': 'division',
        '>': 'mayor que', '<': 'menor que', '>=': 'mayor o igual',
        '<=': 'menor o igual', '==': 'igualdad', '!=': 'desigualdad',
        'y': 'conjuncion (y)', 'o': 'disyuncion (o)',
    }

    def __init__(self, verbose: bool = True):
        """
        Parámetros:
            verbose (bool): si es True imprime cada error en pantalla conforme
                            lo encuentra. Las pruebas automatizadas lo ponen en
                            False para leer la lista de errores sin ruido.
        """
        self.tabla   = SymbolTable()      # Se alimenta durante el recorrido
        self.pila    = PilaSemantica()    # Pila de tipos de las expresiones
        self.errores: list[ErrorSemantico] = []
        self._verbose = verbose

    # =========================================================================
    # PUNTO DE ENTRADA
    # =========================================================================

    def analyze(self, program: Program) -> list:
        """
        Analiza el programa completo en una sola pasada.

        Parámetros:
            program (Program): nodo raíz del AST. Puede ser None si el análisis
                               léxico o sintáctico falló antes.

        Retorna:
            list[ErrorSemantico]: lista vacía si el programa es correcto
        """
        if program is None:
            # El parser ya reportó el problema; aquí no hay nada que analizar.
            return self.errores

        # ── LA ÚNICA PASADA ───────────────────────────────────────────────
        # Se recorre la lista de sentencias del ámbito global en orden de
        # aparición. Cada sentencia se visita exactamente una vez.
        for stmt in program.statements:
            self._check_stmt(stmt)

        self._imprimir_resumen()
        return self.errores

    def _imprimir_resumen(self):
        """Muestra en pantalla el veredicto final del análisis."""
        if not self._verbose:
            return
        if self.errores:
            print(f"\n[Semantico] Se encontraron {len(self.errores)} error(es) semantico(s).")
            print("[Semantico] El programa no se ejecutara hasta que se corrijan.")
        else:
            print("[Semantico] Analisis semantico: OK - sin errores.")

    # =========================================================================
    # VERIFICACIÓN DE SENTENCIAS
    # =========================================================================

    def _check_stmt(self, node):
        """
        Despacha la verificación de una sentencia según su tipo concreto.

        Usa el mismo patrón de despacho por isinstance() que el intérprete,
        para que ambas fases sean fáciles de comparar entre sí.

        Parámetros:
            node (ASTNode): sentencia a verificar
        """
        if isinstance(node, VarDecl):
            self._check_declaracion(node)
        elif isinstance(node, Assign):
            self._check_asignacion(node)
        elif isinstance(node, PrintStmt):
            self._check_salida(node)
        elif isinstance(node, ReadStmt):
            self._check_lectura(node)
        elif isinstance(node, IfStmt):
            self._check_si(node)
        elif isinstance(node, WhileStmt):
            self._check_mientras(node)

        # Invariante de la pila semántica: al terminar una sentencia, todos los
        # tipos que se apilaron durante sus expresiones ya fueron consumidos.
        # Se vacía por seguridad para que un desbalance en una sentencia no
        # contamine el análisis de la siguiente.
        self.pila.vaciar()

    # ── Declaración: entero x = expr; ────────────────────────────────────────

    def _check_declaracion(self, node: VarDecl):
        """
        Verifica 'tipo nombre = expr;'.

        Comprueba dos cosas:
            1. Que el nombre no esté ya declarado EN EL ÁMBITO ACTUAL (E-S02).
            2. Que el tipo de la expresión coincida con el tipo declarado (E-S03).

        Orden importante: la expresión se analiza ANTES de registrar la
        variable, para que 'entero x = x + 1;' detecte que 'x' todavía no
        existe en vez de resolverse contra la variable que se está creando.
        """
        tipo_valor = self._tipo(node.value)

        # ── 1. Redeclaración en el mismo ámbito ──────────────────────────
        if not self.tabla.declarable(node.name):
            previa = self.tabla.resolve(node.name)
            self._error(
                'E-S02',
                f"La variable '{node.name}' ya fue declarada en este ambito "
                f"(linea {previa['lineno']}). No se puede declarar dos veces.",
                node.lineno, node.col,
                f"Usa otro nombre, o quita el tipo para asignarle un valor: "
                f"{node.name} = ...;"
            )
            # Aun con el error, NO se registra de nuevo: la declaración válida
            # sigue siendo la primera, y así el resto del programa se analiza
            # con el tipo original en lugar de acumular errores derivados.
            return

        # ── 2. Compatibilidad de tipos en la inicialización ──────────────
        # Un tipo_valor == TIPO_ERROR significa que la expresión ya reportó su
        # propio error; volver a quejarse aquí sería un error en cascada.
        if tipo_valor != TIPO_ERROR and tipo_valor != node.var_type:
            self._error(
                'E-S03',
                f"Tipo incompatible al declarar '{node.name}': se declaro como "
                f"'{node.var_type}' pero el valor asignado es de tipo '{tipo_valor}'.",
                node.lineno, node.col,
                f"Declara la variable como '{tipo_valor}', o asignale un valor "
                f"de tipo '{node.var_type}'."
            )

        # La variable se registra SIEMPRE con su tipo declarado, incluso si el
        # valor inicial tenía el tipo equivocado. Así el resto del programa se
        # verifica contra la intención del programador y no se llena de errores
        # derivados de una única línea mal escrita.
        self.tabla.declare(node.name, node.var_type,
                           value=None, lineno=node.lineno, col=node.col)

    # ── Asignación: x = expr; ────────────────────────────────────────────────

    def _check_asignacion(self, node: Assign):
        """
        Verifica 'nombre = expr;'.

        Comprueba:
            1. Que la variable exista y sea visible desde el ámbito actual (E-S01).
            2. Que el tipo de la expresión sea el mismo que el declarado (E-S04).
        """
        tipo_valor = self._tipo(node.value)

        entrada = self.tabla.resolve(node.name)

        # ── 1. La variable debe existir y estar en alcance ───────────────
        if entrada is None:
            self._error(
                'E-S01',
                f"La variable '{node.name}' no fue declarada, o ya no esta en "
                f"alcance, y no se le puede asignar un valor.",
                node.lineno, node.col,
                f"Declarala antes de usarla: {tipo_valor if tipo_valor in TIPOS_VALIDOS else 'entero'} "
                f"{node.name} = ...;"
            )
            return

        # ── 2. El tipo de la expresión debe ser exactamente el declarado ─
        tipo_declarado = entrada['type']
        if tipo_valor != TIPO_ERROR and tipo_valor != tipo_declarado:
            self._error(
                'E-S04',
                f"Tipo incompatible en la asignacion a '{node.name}': la variable "
                f"es de tipo '{tipo_declarado}' pero se le asigna un valor de "
                f"tipo '{tipo_valor}'.",
                node.lineno, node.col,
                f"Asigna un valor de tipo '{tipo_declarado}' a '{node.name}'."
            )

    # ── Salida: mostrar(expr); ───────────────────────────────────────────────

    def _check_salida(self, node: PrintStmt):
        """
        Verifica la sentencia de salida del lenguaje.

        mostrar() admite expresiones de cualquiera de los tres tipos del
        lenguaje (entero, cadena y logico), así que la comprobación se reduce a
        exigir que el argumento tenga un tipo VÁLIDO. Es la verificación de
        "funciones con su respectivo argumento válido" que pide la práctica.

        El caso en que el argumento no tenga tipo válido solo puede darse si la
        expresión ya falló antes, y esa situación se filtra arriba para no
        encadenar errores; el chequeo se mantiene como red de seguridad ante un
        nodo de expresión que el analizador no supiera clasificar.
        """
        tipo_arg = self._tipo(node.expr)

        # Una expresión que ya falló no vuelve a reportarse (sin cascadas)
        if tipo_arg == TIPO_ERROR:
            return

        if tipo_arg not in TIPOS_VALIDOS:
            self._error(
                'E-S13',
                f"El argumento de mostrar() no tiene un tipo valido "
                f"(se obtuvo '{tipo_arg}').",
                node.lineno, node.col,
                "mostrar() acepta expresiones de tipo entero, cadena o logico."
            )

    # ── Lectura: leer(x); ────────────────────────────────────────────────────

    def _check_lectura(self, node: ReadStmt):
        """
        Verifica 'leer(nombre);': la variable destino debe existir y estar
        en alcance, porque leer() escribe sobre ella.
        """
        if not self.tabla.exists(node.name):
            self._error(
                'E-S09',
                f"La variable '{node.name}' usada en leer() no fue declarada, "
                f"o ya no esta en alcance.",
                node.lineno, node.col,
                f"Declarala antes de leerla: entero {node.name} = 0;"
            )

    # ── Condicional: si (expr) { ... } sino { ... } ──────────────────────────

    def _check_si(self, node: IfStmt):
        """
        Verifica la sentencia condicional.

        Requisitos de la práctica:
            - La expresión de la condición debe ser de tipo lógico (E-S08).
            - Las sentencias de sus ramas no deben tener errores de tipo, lo
              que se consigue verificándolas recursivamente.

        Cada rama abre su propio ÁMBITO: una variable declarada dentro del
        'si' no existe fuera de él, ni tampoco en la rama 'sino'.
        """
        tipo_cond = self._tipo(node.condition)

        if tipo_cond != TIPO_ERROR and tipo_cond != TIPO_LOGICO:
            self._error(
                'E-S08',
                f"La condicion de 'si' debe ser de tipo 'logico', "
                f"pero es de tipo '{tipo_cond}'.",
                node.lineno, node.col,
                "Usa una comparacion o una variable logica: si (x > 0) { ... }"
            )

        # ── Rama verdadera, en su propio ámbito ──────────────────────────
        self.tabla.enter_scope()
        for stmt in node.then_body:
            self._check_stmt(stmt)
        self.tabla.exit_scope()

        # ── Rama falsa (opcional), en un ámbito independiente ────────────
        if node.else_body is not None:
            self.tabla.enter_scope()
            for stmt in node.else_body:
                self._check_stmt(stmt)
            self.tabla.exit_scope()

    # ── Bucle: mientras (expr) { ... } ───────────────────────────────────────

    def _check_mientras(self, node: WhileStmt):
        """
        Verifica la sentencia de bucle.

        Requisitos de la práctica:
            - La expresión debe ser de tipo lógico (E-S10).
            - Las sentencias del cuerpo no deben tener errores de tipo.

        El cuerpo abre su propio ámbito, igual que las ramas del 'si'.
        """
        tipo_cond = self._tipo(node.condition)

        if tipo_cond != TIPO_ERROR and tipo_cond != TIPO_LOGICO:
            self._error(
                'E-S10',
                f"La condicion de 'mientras' debe ser de tipo 'logico', "
                f"pero es de tipo '{tipo_cond}'.",
                node.lineno, node.col,
                "Usa una comparacion o una variable logica: mientras (i < 10) { ... }"
            )

        self.tabla.enter_scope()
        for stmt in node.body:
            self._check_stmt(stmt)
        self.tabla.exit_scope()

    # =========================================================================
    # VERIFICACIÓN DE EXPRESIONES — cálculo de tipos con pila semántica
    # =========================================================================

    def _tipo(self, node) -> str:
        """
        Calcula el tipo de una expresión COMPLETA y reporta sus errores.

        Lo usan las sentencias, que necesitan el tipo como un valor suelto:
        apila la expresión, la desapila y devuelve el tipo resultante. Al
        volver, la pila queda como estaba.

        Parámetros:
            node (ASTNode): nodo de expresión a analizar

        Retorna:
            str: 'entero', 'cadena', 'logico' o TIPO_ERROR si la expresión es
                 inválida (en cuyo caso el error correspondiente ya fue emitido)
        """
        self._apilar_tipo(node)
        return self.pila.desapilar()

    def _apilar_tipo(self, node):
        """
        Calcula el tipo de una expresión y lo DEJA en la cima de la pila.

        Es el método central de la fase y el que implementa el esquema de
        traducción dirigido por sintaxis: cada subexpresión deja su tipo
        apilado, y cada operador desapila los tipos de sus operandos y apila
        el del resultado.

        Los nodos hoja (literales y variables) apilan su tipo directamente;
        los nodos de operación delegan en el método de su regla, que es quien
        desapila los operandos y apila el resultado.

        Parámetros:
            node (ASTNode): nodo de expresión a analizar
        """
        # ── Literales: su tipo es inmediato, se apila sin más ────────────
        if isinstance(node, Number):
            self.pila.apilar(TIPO_ENTERO)
        elif isinstance(node, StringLiteral):
            self.pila.apilar(TIPO_CADENA)
        elif isinstance(node, BoolLiteral):
            self.pila.apilar(TIPO_LOGICO)

        # ── Variable: su tipo sale de la tabla de símbolos ───────────────
        elif isinstance(node, Identifier):
            self.pila.apilar(self._tipo_identificador(node))

        # ── Operaciones: cada una gestiona la pila según su regla ────────
        elif isinstance(node, BinOp):
            self._tipo_binop(node)
        elif isinstance(node, LogicOp):
            self._tipo_logicop(node)
        elif isinstance(node, NotOp):
            self._tipo_notop(node)
        elif isinstance(node, UnaryMinus):
            self._tipo_unary_minus(node)

        else:
            # Nodo de expresión no contemplado: indicaría una desincronización
            # entre el parser y esta fase, no un error del programa del usuario.
            self.pila.apilar(TIPO_ERROR)

    def _tipo_identificador(self, node: Identifier) -> str:
        """
        Resuelve el tipo de una referencia a variable.

        Aquí es donde se comprueba el requisito "todas las variables que se
        utilizan deberán haber sido declaradas", y además su ALCANCE: resolve()
        busca solo en los ámbitos abiertos, así que una variable declarada
        dentro de un bloque ya cerrado se reporta como no declarada.
        """
        entrada = self.tabla.resolve(node.name)
        if entrada is None:
            self._error(
                'E-S01',
                f"La variable '{node.name}' se usa pero no fue declarada, "
                f"o ya no esta en alcance.",
                node.lineno, node.col,
                f"Declarala antes de usarla, por ejemplo: entero {node.name} = 0;"
            )
            return TIPO_ERROR
        return entrada['type']

    # ── Operadores aritméticos y relacionales ────────────────────────────────

    def _tipo_binop(self, node: BinOp):
        """
        Calcula el tipo de una operación binaria aritmética o relacional y lo
        deja apilado.

        Aquí se ve el mecanismo de la pila semántica en estado puro:
            1. Se apila el tipo del operando izquierdo.
            2. Se apila el tipo del operando derecho.
            3. El operador DESAPILA los dos y APILA el tipo del resultado.

        El orden al desapilar es inverso al de apilado: el primero que sale es
        el operando derecho, porque fue el último en entrar.

        Ambos operandos se analizan siempre, aunque el izquierdo ya haya
        fallado, para que los errores del lado derecho también se reporten en
        esta misma pasada.
        """
        self._apilar_tipo(node.left)
        self._apilar_tipo(node.right)

        der = self.pila.desapilar()   # Ultimo en entrar, primero en salir
        izq = self.pila.desapilar()

        if node.op == '+':
            resultado = self._tipo_suma(node, izq, der)
        elif node.op in {'-', '*', '/'}:
            resultado = self._tipo_aritmetico(node, izq, der)
        elif node.op in {'>', '<', '>=', '<='}:
            resultado = self._tipo_relacional(node, izq, der)
        elif node.op in {'==', '!='}:
            resultado = self._tipo_igualdad(node, izq, der)
        else:
            resultado = TIPO_ERROR

        self.pila.apilar(resultado)

    def _tipo_suma(self, node: BinOp, izq: str, der: str) -> str:
        """
        Regla del operador '+', el único con doble significado:

            entero + entero            → entero  (suma aritmética)
            cadena + cualquier tipo    → cadena  (concatenación)
            cualquier tipo + cadena    → cadena  (concatenación)
            todo lo demás              → ERROR

        El caso prohibido más importante es 'entero + logico', que el enunciado
        de la práctica menciona explícitamente como error de tipo.
        """
        # Si algún lado ya falló, no se emite un segundo error
        if izq == TIPO_ERROR or der == TIPO_ERROR:
            return TIPO_ERROR

        # Concatenación: basta con que uno de los dos lados sea cadena
        if izq == TIPO_CADENA or der == TIPO_CADENA:
            return TIPO_CADENA

        # Suma aritmética
        if izq == TIPO_ENTERO and der == TIPO_ENTERO:
            return TIPO_ENTERO

        # Único caso restante: hay un lógico involucrado sin ninguna cadena
        self._error(
            'E-S05',
            f"No se puede aplicar el operador '+' entre '{izq}' y '{der}'. "
            f"La suma requiere dos enteros, y la concatenacion requiere que al "
            f"menos un operando sea cadena.",
            node.lineno, node.col,
            "Convierte el valor logico a texto usando una variable de tipo cadena, "
            "o compara los valores con 'y' / 'o' en vez de sumarlos."
        )
        return TIPO_ERROR

    def _tipo_aritmetico(self, node: BinOp, izq: str, der: str) -> str:
        """
        Regla de '-', '*' y '/': ambos operandos deben ser enteros.

        A diferencia de '+', estos operadores no tienen versión para cadenas:
        restar o multiplicar textos no significa nada en este lenguaje.

        Aprovecha para detectar la DIVISIÓN ENTRE CERO cuando el divisor es una
        expresión constante, es decir, calculable sin ejecutar el programa.
        """
        if izq == TIPO_ERROR or der == TIPO_ERROR:
            return TIPO_ERROR

        hay_error = False
        for lado, tipo in (('izquierdo', izq), ('derecho', der)):
            if tipo != TIPO_ENTERO:
                self._error(
                    'E-S05',
                    f"El operando {lado} de la {self._NOMBRE_OPERADOR[node.op]} "
                    f"('{node.op}') es de tipo '{tipo}' y se esperaba 'entero'.",
                    node.lineno, node.col,
                    f"El operador '{node.op}' solo funciona entre valores enteros."
                )
                hay_error = True

        if hay_error:
            return TIPO_ERROR

        # ── División entre cero detectable en tiempo de compilación ──────
        if node.op == '/':
            divisor = self._evaluar_constante(node.right)
            if divisor == 0:
                self._error(
                    'E-S11',
                    "Division entre cero: el divisor es una expresion constante "
                    "cuyo valor es 0.",
                    node.lineno, node.col,
                    "Cambia el divisor por un valor distinto de cero."
                )
                return TIPO_ERROR

        return TIPO_ENTERO

    def _tipo_relacional(self, node: BinOp, izq: str, der: str) -> str:
        """
        Regla de '>', '<', '>=' y '<=': ambos operandos del MISMO tipo, y ese
        tipo debe admitir orden (entero o cadena).

        Los valores lógicos no se ordenan: preguntar si verdadero > falso no
        tiene sentido en este lenguaje, así que se rechaza.
        """
        if izq == TIPO_ERROR or der == TIPO_ERROR:
            return TIPO_ERROR

        if izq != der:
            self._error(
                'E-S06',
                f"No se pueden comparar tipos distintos con '{node.op}': "
                f"el operando izquierdo es '{izq}' y el derecho es '{der}'.",
                node.lineno, node.col,
                "Compara valores del mismo tipo."
            )
            return TIPO_ERROR

        if izq == TIPO_LOGICO:
            self._error(
                'E-S06',
                f"El operador '{node.op}' no se puede aplicar a valores logicos: "
                f"verdadero y falso no tienen un orden definido.",
                node.lineno, node.col,
                "Para comparar valores logicos usa '==' o '!='."
            )
            return TIPO_ERROR

        return TIPO_LOGICO

    def _tipo_igualdad(self, node: BinOp, izq: str, der: str) -> str:
        """
        Regla de '==' y '!=': ambos operandos deben ser del mismo tipo.

        A diferencia de los relacionales, aquí sí se admiten valores lógicos,
        porque preguntar si dos booleanos son iguales sí tiene sentido.
        """
        if izq == TIPO_ERROR or der == TIPO_ERROR:
            return TIPO_ERROR

        if izq != der:
            self._error(
                'E-S06',
                f"No se pueden comparar tipos distintos con '{node.op}': "
                f"el operando izquierdo es '{izq}' y el derecho es '{der}'.",
                node.lineno, node.col,
                "Compara valores del mismo tipo; un entero nunca sera igual a una cadena."
            )
            return TIPO_ERROR

        return TIPO_LOGICO

    # ── Operadores lógicos ───────────────────────────────────────────────────

    def _tipo_logicop(self, node: LogicOp):
        """
        Regla de 'y' y 'o': ambos operandos deben ser de tipo lógico.

        El lenguaje no convierte números a booleanos automáticamente: escribir
        '5 y verdadero' es un error, no una expresión que valga verdadero.

        Usa la pila igual que _tipo_binop: apila los dos operandos, los
        desapila en orden inverso y apila el tipo del resultado.
        """
        self._apilar_tipo(node.left)
        self._apilar_tipo(node.right)

        der = self.pila.desapilar()
        izq = self.pila.desapilar()

        hay_error = False
        for lado, tipo in (('izquierdo', izq), ('derecho', der)):
            if tipo == TIPO_ERROR:
                hay_error = True
                continue
            if tipo != TIPO_LOGICO:
                self._error(
                    'E-S07',
                    f"El operando {lado} del operador logico '{node.op}' es de "
                    f"tipo '{tipo}' y se esperaba 'logico'.",
                    node.lineno, node.col,
                    f"Usa una comparacion o una variable logica a ambos lados de '{node.op}'."
                )
                hay_error = True

        self.pila.apilar(TIPO_ERROR if hay_error else TIPO_LOGICO)

    def _tipo_notop(self, node: NotOp):
        """
        Regla de 'no': su operando debe ser de tipo lógico.

        Al ser un operador UNARIO, desapila un solo tipo en vez de dos.

        Esta comprobación faltaba por completo en la versión anterior del
        analizador, que se limitaba a recorrer el operando sin verificarlo.
        """
        self._apilar_tipo(node.operand)
        tipo = self.pila.desapilar()

        if tipo == TIPO_ERROR:
            self.pila.apilar(TIPO_ERROR)
            return

        if tipo != TIPO_LOGICO:
            self._error(
                'E-S07',
                f"El operador 'no' solo se aplica a valores logicos, pero su "
                f"operando es de tipo '{tipo}'.",
                node.lineno, node.col,
                "Usa: no bandera   o bien:  no (x > 0)"
            )
            self.pila.apilar(TIPO_ERROR)
            return

        self.pila.apilar(TIPO_LOGICO)

    def _tipo_unary_minus(self, node: UnaryMinus):
        """
        Regla del menos unario: su operando debe ser entero.

        Cambiar el signo de una cadena o de un valor lógico no está definido.
        """
        self._apilar_tipo(node.operand)
        tipo = self.pila.desapilar()

        if tipo == TIPO_ERROR:
            self.pila.apilar(TIPO_ERROR)
            return

        if tipo != TIPO_ENTERO:
            self._error(
                'E-S12',
                f"El signo negativo solo se aplica a enteros, pero el operando "
                f"es de tipo '{tipo}'.",
                node.lineno, node.col,
                "Aplica '-' unicamente a numeros: -contador, -(a + b)"
            )
            self.pila.apilar(TIPO_ERROR)
            return

        self.pila.apilar(TIPO_ENTERO)

    # =========================================================================
    # EVALUACIÓN DE EXPRESIONES ARITMÉTICAS CONSTANTES
    # =========================================================================

    def _evaluar_constante(self, node):
        """
        Calcula el valor de una expresión aritmética SIN ejecutar el programa.

        Esto es plegado de constantes (constant folding): si una expresión está
        formada solo por números y operadores, su resultado ya se conoce en
        tiempo de compilación. Por ejemplo, en 'a / (3 - 3)' se puede saber que
        el divisor vale 0 antes siquiera de ejecutar, y avisar al programador.

        Parámetros:
            node (ASTNode): expresión a evaluar

        Retorna:
            int  : el valor si toda la expresión es constante
            None : si interviene alguna variable o algún tipo no numérico,
                   porque entonces el valor solo se conoce en ejecución
        """
        if isinstance(node, Number):
            return node.value

        if isinstance(node, UnaryMinus):
            valor = self._evaluar_constante(node.operand)
            return None if valor is None else -valor

        if isinstance(node, BinOp) and node.op in {'+', '-', '*', '/'}:
            izq = self._evaluar_constante(node.left)
            der = self._evaluar_constante(node.right)

            # Basta con que un lado dependa de una variable para que el
            # resultado no sea calculable aquí.
            if izq is None or der is None:
                return None

            if node.op == '+':
                return izq + der
            if node.op == '-':
                return izq - der
            if node.op == '*':
                return izq * der
            # División: si el divisor es 0 no se calcula nada, solo se informa
            # de que vale 0 para que _tipo_aritmetico emita el error E-S13.
            if der == 0:
                return None
            return izq // der

        # Identificadores, cadenas, booleanos y comparaciones no son constantes
        # aritméticas evaluables en esta fase.
        return None

    # =========================================================================
    # REGISTRO DE ERRORES
    # =========================================================================

    def _error(self, codigo: str, mensaje: str, linea: int, columna: int, ayuda: str = ""):
        """
        Registra un error semántico y, si verbose está activo, lo imprime.

        El análisis NUNCA se detiene al llamar a este método: eso es lo que
        permite reportar todos los errores del programa en una sola pasada,
        en lugar de obligar al usuario a corregirlos de uno en uno.
        """
        error = ErrorSemantico(codigo, mensaje, linea, columna, ayuda)
        self.errores.append(error)
        if self._verbose:
            print(error.detallado())

    # =========================================================================
    # REPORTES
    # =========================================================================

    def save_report(self, filename: str = "progfte.sem") -> None:
        """
        Escribe el resultado del análisis semántico en un archivo de texto.

        Parámetros:
            filename (str): ruta del archivo de salida

        No lanza excepciones: un fallo de escritura se informa por pantalla
        para no interrumpir el resto del pipeline.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 78 + "\n")
                f.write("   REPORTE DE ANALISIS SEMANTICO\n")
                f.write("=" * 78 + "\n\n")

                if not self.errores:
                    f.write("RESULTADO: SIN ERRORES SEMANTICOS.\n\n")
                    f.write("El programa cumple todas las reglas de tipos, de ambito\n")
                    f.write("y de argumentos, por lo que puede ejecutarse.\n\n")
                else:
                    f.write(f"RESULTADO: {len(self.errores)} ERROR(ES) SEMANTICO(S).\n")
                    f.write("El programa no se ejecuta hasta corregirlos.\n\n")
                    f.write(f"{'#':<4}{'CODIGO':<10}{'LINEA':<8}{'COLUMNA':<10}DESCRIPCION\n")
                    f.write("-" * 78 + "\n")

                    for i, err in enumerate(self.errores, start=1):
                        f.write(f"{i:<4}{err.codigo:<10}{err.linea:<8}"
                                f"{err.columna:<10}{err.mensaje}\n")
                        if err.ayuda:
                            f.write(f"{'':<32}Sugerencia: {err.ayuda}\n")
                        f.write("\n")

                # Datos del análisis, útiles para documentar la práctica
                f.write("=" * 78 + "\n")
                f.write("DATOS DEL ANALISIS\n")
                f.write("-" * 78 + "\n")
                f.write("Pasadas sobre el AST            : 1 (una sola pasada)\n")
                f.write(f"Simbolos declarados             : {len(self.tabla.historial())}\n")
                f.write(f"Profundidad max. de la pila sem.: {self.pila.profundidad_maxima()}\n")
                f.write("=" * 78 + "\n")

            print(f"[Sistema] Reporte semantico generado en: {filename}")

        except IOError as e:
            print(f"[Error] No se pudo generar el reporte semantico: {e}")
