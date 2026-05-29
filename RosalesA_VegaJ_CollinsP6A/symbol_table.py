"""
=============================================================================
symbol_table.py — Tabla de Símbolos
=============================================================================
Propósito general:
    Implementa la "memoria" del intérprete: un registro centralizado que
    almacena el nombre, tipo y valor actual de cada variable declarada
    durante la ejecución del programa.

    En teoría de compiladores, la tabla de símbolos es la estructura de
    datos que conecta los identificadores del código fuente con la
    información semántica asociada (tipo, valor, scope, etc.).

    Este módulo implementa la VERIFICACIÓN SEMÁNTICA en tiempo de ejecución:
        - Impide declarar la misma variable dos veces.
        - Impide usar variables no declaradas.
        - Registra el tipo para que el intérprete pueda hacer coerción.

    Ciclo de vida:
        1. Se crea vacía al inicio de cada ejecución (en Interpreter.__init__).
        2. Se llena con declare() conforme el programa declara variables.
        3. Se consulta y actualiza con get()/assign() durante la ejecución.
        4. Se descarta al terminar (no hay persistencia entre ejecuciones).

    Relación con otros módulos:
        - Solo interpreter.py la usa directamente.
        - main.py accede a _table de forma directa para generar reportes
          (acoplamiento que podría reducirse con un método items() público).
=============================================================================
"""


class SymbolTable:
    """
    Tabla de símbolos basada en un diccionario Python.

    Cada entrada del diccionario interno tiene la forma:
        nombre_variable  →  { 'type': <str>, 'value': <valor Python> }

    Donde:
        'type'  es uno de: 'entero' | 'cadena' | 'logico'
        'value' es el valor Python correspondiente: int | str | bool

    Todos los métodos públicos lanzan RuntimeError con mensajes descriptivos
    ante condiciones de error, siguiendo el patrón fail-fast: es mejor
    detener la ejecución con un mensaje claro que continuar con datos
    inválidos que producirían errores crípticos más adelante.
    """

    def __init__(self):
        # Diccionario privado (prefijo _) que almacena todas las variables.
        # Se usa dict porque ofrece búsqueda O(1) por nombre de variable,
        # lo cual es crítico ya que cada referencia a variable implica una consulta.
        self._table: dict = {}

    # =========================================================================
    # OPERACIONES PRINCIPALES — escritura y lectura de variables
    # =========================================================================

    def declare(self, name: str, var_type: str, value=None):
        """
        Registra una variable nueva en la tabla con su tipo y valor inicial.

        Se llama UNA SOLA VEZ por variable, en el momento en que el intérprete
        procesa un nodo VarDecl. Intentar declarar la misma variable dos veces
        es un error semántico (no hay shadowing ni scopes anidados en este lenguaje).

        Parámetros:
            name     (str): nombre de la variable tal como aparece en el fuente
            var_type (str): tipo declarado → 'entero' | 'cadena' | 'logico'
            value    (any): valor inicial ya evaluado y verificado por el intérprete;
                            None solo si no se proveyó valor (no ocurre en la gramática actual)

        Lanza:
            RuntimeError: si la variable ya existe en la tabla (redeclaración)
        """
        # Verificación de redeclaración: en este lenguaje no existe el concepto
        # de shadowing, por lo que declarar dos veces la misma variable es error.
        if name in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' ya fue declarada. "
                f"No se puede declarar dos veces la misma variable."
            )
        # Crea la entrada con tipo y valor inicial
        self._table[name] = {'type': var_type, 'value': value}

    def assign(self, name: str, value):
        """
        Actualiza el valor de una variable ya existente en la tabla.

        Se llama en dos situaciones:
            1. Al procesar un nodo Assign (reasignación explícita: a = expr;)
            2. Al procesar un nodo ReadStmt después de leer la entrada del usuario.

        No verifica compatibilidad de tipos aquí; esa responsabilidad recae en
        el intérprete, que debe llamar a _verificar_tipo() antes de assign().

        Parámetros:
            name  (str): nombre de la variable a actualizar
            value (any): nuevo valor ya verificado y convertido al tipo correcto

        Lanza:
            RuntimeError: si la variable no fue declarada previamente
        """
        # Uso-antes-de-declaración: error semántico frecuente en principiantes
        if name not in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada. "
                f"Debes declararla primero con: entero {name} = valor;"
            )
        # Actualiza solo el valor; el tipo no cambia después de la declaración
        self._table[name]['value'] = value

    def get(self, name: str):
        """
        Devuelve el valor actual de una variable.

        Se llama cada vez que el intérprete evalúa un nodo Identifier,
        es decir, cada vez que el programa fuente referencia el nombre
        de una variable en una expresión.

        Parámetros:
            name (str): nombre de la variable a consultar

        Retorna:
            any: el valor Python actual de la variable (int, str o bool)

        Lanza:
            RuntimeError: si la variable no fue declarada previamente
        """
        if name not in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada. "
                f"Debes declararla antes de usarla."
            )
        # Accede al valor dentro del diccionario anidado
        return self._table[name]['value']

    def get_type(self, name: str) -> str:
        """
        Devuelve el tipo declarado de una variable, sin su valor.

        Útil para el intérprete cuando necesita saber cómo convertir el
        valor de entrada del usuario (en ReadStmt) o verificar compatibilidad
        de tipos en una asignación, sin necesidad de recuperar el valor actual.

        Parámetros:
            name (str): nombre de la variable

        Retorna:
            str: el tipo declarado → 'entero' | 'cadena' | 'logico'

        Lanza:
            RuntimeError: si la variable no fue declarada previamente
        """
        if name not in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada."
            )
        return self._table[name]['type']

    def exists(self, name: str) -> bool:
        """
        Comprueba si una variable ya fue declarada, sin lanzar excepciones.

        A diferencia de get() y get_type(), este método es seguro para usar
        en verificaciones previas sin necesidad de capturar excepciones.
        Actualmente no se usa en el intérprete principal, pero es útil para
        extensiones futuras (ej.: declaración condicional, scopes).

        Parámetros:
            name (str): nombre de la variable a verificar

        Retorna:
            bool: True si la variable existe, False en caso contrario
        """
        return name in self._table

    # =========================================================================
    # UTILIDADES DE INSPECCIÓN — para depuración y reportes
    # =========================================================================

    def dump(self):
        """
        Imprime el estado completo de la tabla en formato tabular legible.

        Se llama al finalizar la ejecución del programa para mostrar el
        valor final de todas las variables (equivalente al "watch" de un
        debugger). El ancho de las columnas se ajusta dinámicamente al
        nombre de variable más largo para que la tabla siempre se vea alineada.

        No recibe parámetros ni retorna valor; su único efecto es la salida
        a pantalla (stdout).
        """
        # Caso especial: ninguna variable fue declarada durante la ejecución
        if not self._table:
            print("\n[Tabla de Simbolos] (vacia — no se declaro ninguna variable)\n")
            return

        # Calcula el ancho de la columna de nombres de forma dinámica:
        # toma el nombre más largo y le suma 2 caracteres de margen.
        # max() de 12 evita que la columna sea demasiado estrecha con variables cortas.
        ancho_nombre = max(len(n) for n in self._table) + 2
        ancho_nombre = max(ancho_nombre, 12)

        # Encabezado de la tabla
        print("\n" + "=" * 50)
        print("   TABLA DE SIMBOLOS — estado final del programa")
        print("=" * 50)
        print(f"  {'Variable':<{ancho_nombre}} {'Tipo':<12} Valor")
        print("  " + "-" * (ancho_nombre + 22))

        # Itera en orden de inserción (Python 3.7+ garantiza este orden),
        # lo que significa que las variables aparecen en el orden en que
        # fueron declaradas en el programa fuente.
        for name, info in self._table.items():
            valor = info['value']
            # Convierte booleanos Python (True/False) a la sintaxis del lenguaje
            # (verdadero/falso) para que el reporte sea coherente con el fuente
            if isinstance(valor, bool):
                valor_str = 'verdadero' if valor else 'falso'
            else:
                valor_str = str(valor)
            print(f"  {name:<{ancho_nombre}} {info['type']:<12} {valor_str}")

        print("=" * 50 + "\n")

    def __repr__(self):
        """
        Representación de depuración del objeto, útil en el REPL de Python
        o al imprimir el objeto directamente con print().
        """
        return f"SymbolTable({self._table})"

    # ─────────────────────────────────────────────────────────────────────────
    # SUGERENCIA: El separador de línea larga (---) que aparece aquí en el
    # código original rompe la cohesión visual de la clase. Considera eliminarlo
    # o reemplazarlo por una sección con comentario descriptivo, como se hace
    # con los bloques de "Operaciones principales" y "Utilidades de inspección".
    # ─────────────────────────────────────────────────────────────────────────

    def save_to_file(self, filename="tabla_simbolos.txt"):
        """
        Serializa el estado actual de la tabla en un archivo de texto plano.

        Genera el mismo formato tabular que dump(), pero dirigido a un archivo
        en lugar de a pantalla. Es útil para guardar un registro persistente
        del estado final de las variables después de la ejecución.

        La escritura usa encoding UTF-8 para soportar caracteres especiales
        en nombres de variables o valores de cadena (acentos, ñ, etc.).

        Parámetros:
            filename (str): ruta y nombre del archivo de salida;
                            por defecto "tabla_simbolos.txt" en el directorio actual

        No retorna valor. Efectos secundarios:
            - Crea o sobreescribe el archivo indicado.
            - Imprime confirmación en pantalla si tuvo éxito.
            - Imprime mensaje de error en pantalla si falló (no lanza excepción,
              para no interrumpir el flujo principal por un error de I/O).

        SUGERENCIA: Considerar lanzar la excepción en lugar de solo imprimirla,
        o usar el módulo 'logging' para que el llamador pueda decidir cómo
        manejar el error de escritura.
        """
        try:
            # Abre en modo escritura ('w'); si el archivo ya existe, lo sobreescribe.
            # encoding='utf-8' es explícito para evitar errores en sistemas Windows
            # donde el encoding por defecto puede ser cp1252 o similar.
            with open(filename, "w", encoding="utf-8") as f:

                # Caso especial: tabla vacía → archivo con mensaje indicativo
                if not self._table:
                    f.write("TABLA DE SÍMBOLOS VACÍA\n")
                    return   # Termina aquí; el bloque with cierra el archivo limpiamente

                # Encabezado del reporte en archivo
                f.write("=" * 50 + "\n")
                f.write("   TABLA DE SÍMBOLOS — REPORTE GENERADO\n")
                f.write("=" * 50 + "\n")
                # Encabezado de columnas con ancho fijo para facilitar lectura
                f.write(f"{'Variable':<20} {'Tipo':<15} {'Valor':<15}\n")
                f.write("-" * 50 + "\n")

                # Escribe una fila por cada variable registrada
                for name, info in self._table.items():
                    valor = info['value']
                    # Mismo tratamiento de booleanos que en dump():
                    # True/False Python → verdadero/falso del lenguaje
                    if isinstance(valor, bool):
                        valor_str = 'verdadero' if valor else 'falso'
                    else:
                        valor_str = str(valor)

                    f.write(f"{name:<20} {info['type']:<15} {valor_str:<15}\n")

                f.write("=" * 50 + "\n")

            print(f"[Sistema] Tabla de símbolos guardada en: {filename}")

        except IOError as e:
            # IOError cubre errores de permisos, disco lleno, ruta inválida, etc.
            # Se captura específicamente (no Exception genérica) para no ocultar
            # bugs inesperados de otra naturaleza.
            print(f"[Error] No se pudo escribir el archivo de símbolos: {e}")
