"""
=============================================================================
symbol_table.py — Tabla de Símbolos
=============================================================================
Propósito general:
    Implementa la "memoria" del compilador: un registro centralizado que
    almacena el nombre, tipo, ÁMBITO y valor actual de cada variable declarada.

    En teoría de compiladores, la tabla de símbolos es la estructura de
    datos que conecta los identificadores del código fuente con la
    información semántica asociada (tipo, valor, ámbito, posición, etc.).

    La usan DOS módulos, cada uno con su propia instancia:
        - semantic.py   la ALIMENTA con nombre, tipo, ámbito, línea y columna
                        durante el análisis (los valores aún no existen).
        - interpreter.py la usa con los valores reales durante la ejecución.

=============================================================================
ÁMBITOS (ALCANCE DE LAS VARIABLES)
=============================================================================
    La tabla NO es un diccionario plano, sino una PILA DE DICCIONARIOS.
    Cada bloque { } de un 'si', 'sino' o 'mientras' abre un ámbito nuevo que
    se apila, y al cerrar el bloque se desapila:

        entero a = 1;              ámbito 0 (global): {a}
        si (a > 0) {               ---- entra al ámbito 1 ----
            entero b = 2;          ámbito 1: {b}     (a sigue visible)
            mostrar(a + b);        OK: 'a' se busca hacia afuera
        }                          ---- sale del ámbito 1: 'b' desaparece ----
        mostrar(b);                ERROR: 'b' ya no está en ningún ámbito

    Reglas que esto implementa:
        - Buscar una variable recorre la pila de DENTRO HACIA FUERA, así que
          un bloque ve las variables de los bloques que lo contienen.
        - Declarar dos veces el mismo nombre EN EL MISMO ÁMBITO es un error.
        - Dos bloques hermanos pueden usar el mismo nombre sin conflicto,
          porque cada uno vive en su propio ámbito.

=============================================================================
HISTORIAL
=============================================================================
    Cuando un ámbito se cierra sus variables se pierden, pero el reporte de la
    práctica debe mostrar TODAS las variables del programa. Por eso, además de
    la pila, se mantiene '_historial': una lista que registra cada declaración
    y de la que nunca se borra nada. La pila sirve para RESOLVER nombres; el
    historial sirve para REPORTAR.
=============================================================================
"""


class SymbolTable:
    """
    Tabla de símbolos con ámbitos anidados, implementada como pila de diccionarios.

    Cada entrada tiene la forma:
        nombre_variable  →  { 'type': <str>, 'value': <valor Python>,
                              'lineno': <int>, 'col': <int> }

    Donde:
        'type'   es uno de: 'entero' | 'cadena' | 'logico'
        'value'  es el valor Python correspondiente: int | str | bool
                 (el analizador semántico lo deja en None: aún no hay valores)
        'lineno' y 'col' son la posición de la declaración en el fuente

    Todos los métodos públicos lanzan RuntimeError con mensajes descriptivos
    ante condiciones de error, siguiendo el patrón fail-fast: es mejor
    detener la ejecución con un mensaje claro que continuar con datos
    inválidos que producirían errores crípticos más adelante.

    NOTA para el analizador semántico: en vez de capturar excepciones, conviene
    usar los métodos que NO lanzan (exists, resolve, declarable) para poder
    reportar el error con línea y columna y seguir analizando el resto del
    programa en la misma pasada.
    """

    def __init__(self):
        # Pila de ámbitos. El índice 0 es siempre el ámbito GLOBAL y nunca se
        # desapila; los bloques { } apilan y desapilan ámbitos encima de él.
        # Se usan dicts porque la búsqueda por nombre es O(1) y cada referencia
        # a una variable implica una consulta.
        self._scopes: list[dict] = [{}]

        # Registro acumulativo de TODA declaración vista, en orden de aparición.
        # No se borra nunca, ni siquiera al cerrar un ámbito, porque los
        # reportes deben mostrar todas las variables del programa.
        self._historial: list[dict] = []

    # =========================================================================
    # GESTIÓN DE ÁMBITOS
    # =========================================================================

    def enter_scope(self):
        """
        Abre un ámbito nuevo (se llama al entrar al cuerpo de si/sino/mientras).

        A partir de aquí, las variables declaradas viven en este ámbito y
        desaparecerán cuando se llame a exit_scope().
        """
        self._scopes.append({})

    def exit_scope(self):
        """
        Cierra el ámbito actual y descarta sus variables locales.

        El ámbito global (índice 0) nunca se cierra: la comprobación len > 1
        protege contra un desbalance de llamadas que dejaría la tabla inutilizable.
        """
        if len(self._scopes) > 1:
            self._scopes.pop()

    def scope_level(self) -> int:
        """
        Nivel del ámbito actual: 0 = global, 1 = dentro de un bloque,
        2 = dentro de un bloque anidado en otro, etc.

        Retorna:
            int: profundidad actual de la pila de ámbitos
        """
        return len(self._scopes) - 1

    # =========================================================================
    # OPERACIONES PRINCIPALES — escritura y lectura de variables
    # =========================================================================

    def declare(self, name: str, var_type: str, value=None, lineno: int = 0, col: int = 0):
        """
        Registra una variable nueva en el ÁMBITO ACTUAL.

        Se llama una vez por declaración, tanto desde el analizador semántico
        (con value=None) como desde el intérprete (con el valor ya evaluado).

        Parámetros:
            name     (str): nombre de la variable tal como aparece en el fuente
            var_type (str): tipo declarado → 'entero' | 'cadena' | 'logico'
            value    (any): valor inicial ya evaluado y verificado, o None
            lineno   (int): línea de la declaración en el fuente
            col      (int): columna de la declaración en el fuente

        Lanza:
            RuntimeError: si el nombre ya existe EN EL ÁMBITO ACTUAL.
                          Que exista en un ámbito exterior no es error: el
                          bloque interno simplemente lo oculta.
        """
        if name in self._scopes[-1]:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' ya fue declarada. "
                f"No se puede declarar dos veces la misma variable."
            )

        # Una sola entrada compartida: el ámbito y el historial apuntan al MISMO
        # diccionario. Así, cuando el intérprete actualiza el valor con assign(),
        # el historial refleja el cambio automáticamente y el reporte final
        # muestra el último valor que tuvo la variable, incluso si su ámbito ya
        # se cerró. El campo 'scope' permite al reporte distinguir una variable
        # global de una local a un bloque.
        entrada = {
            'name': name, 'type': var_type, 'value': value,
            'scope': self.scope_level(), 'lineno': lineno, 'col': col,
        }
        self._scopes[-1][name] = entrada
        self._historial.append(entrada)

    def declarable(self, name: str) -> bool:
        """
        Indica si el nombre puede declararse en el ámbito actual, sin lanzar.

        Lo usa el analizador semántico para detectar la redeclaración y
        reportarla con línea y columna en lugar de abortar con una excepción.

        Parámetros:
            name (str): nombre de la variable a declarar

        Retorna:
            bool: True si el nombre está libre en el ámbito actual
        """
        return name not in self._scopes[-1]

    def resolve(self, name: str):
        """
        Busca una variable recorriendo la pila de ámbitos de DENTRO HACIA FUERA.

        Ésta es la operación que implementa el alcance del lenguaje: se
        devuelve la declaración más interna que coincida con el nombre, de modo
        que un bloque ve sus propias variables y también las de los bloques que
        lo contienen, pero nunca las de bloques ya cerrados.

        Parámetros:
            name (str): nombre de la variable a buscar

        Retorna:
            dict | None: la entrada de la variable, o None si no es visible
        """
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def assign(self, name: str, value):
        """
        Actualiza el valor de una variable visible desde el ámbito actual.

        Se llama en dos situaciones:
            1. Al procesar un nodo Assign (reasignación explícita: a = expr;)
            2. Al procesar un nodo ReadStmt después de leer la entrada del usuario.

        No verifica compatibilidad de tipos aquí; esa responsabilidad recae en
        el intérprete, que debe llamar a _verificar_tipo() antes de assign().

        Parámetros:
            name  (str): nombre de la variable a actualizar
            value (any): nuevo valor ya verificado y convertido al tipo correcto

        Lanza:
            RuntimeError: si la variable no es visible desde el ámbito actual
        """
        entrada = self.resolve(name)
        # Uso-antes-de-declaración: error semántico frecuente en principiantes
        if entrada is None:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada. "
                f"Debes declararla primero con: entero {name} = valor;"
            )
        # Actualiza solo el valor; el tipo no cambia después de la declaración
        entrada['value'] = value

    def get(self, name: str):
        """
        Devuelve el valor actual de una variable visible desde el ámbito actual.

        Se llama cada vez que el intérprete evalúa un nodo Identifier,
        es decir, cada vez que el programa fuente referencia el nombre
        de una variable en una expresión.

        Parámetros:
            name (str): nombre de la variable a consultar

        Retorna:
            any: el valor Python actual de la variable (int, str o bool)

        Lanza:
            RuntimeError: si la variable no es visible desde el ámbito actual
        """
        entrada = self.resolve(name)
        if entrada is None:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada. "
                f"Debes declararla antes de usarla."
            )
        return entrada['value']

    def get_type(self, name: str) -> str:
        """
        Devuelve el tipo declarado de una variable, sin su valor.

        Lo usa el intérprete para saber cómo convertir la entrada del usuario
        (en ReadStmt) o verificar la compatibilidad de tipos en una asignación,
        y el analizador semántico para comprobar los tipos de las expresiones.

        Parámetros:
            name (str): nombre de la variable

        Retorna:
            str: el tipo declarado → 'entero' | 'cadena' | 'logico'

        Lanza:
            RuntimeError: si la variable no es visible desde el ámbito actual
        """
        entrada = self.resolve(name)
        if entrada is None:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada."
            )
        return entrada['type']

    def exists(self, name: str) -> bool:
        """
        Comprueba si una variable es visible desde el ámbito actual, sin lanzar.

        A diferencia de get() y get_type(), este método es seguro para usar
        en verificaciones previas sin necesidad de capturar excepciones; es el
        que usa el analizador semántico para detectar el uso de variables no
        declaradas o fuera de su alcance.

        Parámetros:
            name (str): nombre de la variable a verificar

        Retorna:
            bool: True si la variable es visible, False en caso contrario
        """
        return self.resolve(name) is not None

    def historial(self) -> list:
        """
        Devuelve el registro de todas las declaraciones vistas en el programa,
        incluidas las de ámbitos ya cerrados, en orden de aparición.

        Retorna:
            list[dict]: entradas con name, type, value, scope, lineno y col
        """
        return self._historial

    # =========================================================================
    # UTILIDADES DE INSPECCIÓN — para depuración y reportes
    # =========================================================================

    @staticmethod
    def _formato_valor(valor) -> str:
        """
        Convierte un valor Python al texto que usa el lenguaje fuente.

        Los booleanos de Python se imprimirían como True/False, pero el
        mini-lenguaje escribe verdadero/falso; y una variable que aún no tiene
        valor (porque solo pasó por el analizador semántico, que verifica tipos
        pero no calcula valores) se marca como '(sin evaluar)' en lugar de
        mostrar el 'None' de Python, que no significa nada en este lenguaje.

        Parámetros:
            valor (any): valor almacenado en la tabla

        Retorna:
            str: representación coherente con la sintaxis del lenguaje
        """
        if valor is None:
            return '(sin evaluar)'
        if isinstance(valor, bool):
            return 'verdadero' if valor else 'falso'
        return str(valor)

    @staticmethod
    def _formato_ambito(nivel: int) -> str:
        """
        Convierte el nivel numérico de ámbito en una etiqueta legible.

        Parámetros:
            nivel (int): 0 = global, 1+ = dentro de un bloque

        Retorna:
            str: 'global' o 'bloque N'
        """
        return 'global' if nivel == 0 else f'bloque {nivel}'

    def dump(self):
        """
        Imprime el contenido completo de la tabla en formato tabular legible.

        Se llama al finalizar la ejecución del programa para mostrar el
        valor final de todas las variables (equivalente al "watch" de un
        debugger). El ancho de las columnas se ajusta dinámicamente al
        nombre de variable más largo para que la tabla siempre se vea alineada.

        Recorre el HISTORIAL y no la pila de ámbitos, de modo que también
        aparecen las variables locales de bloques que ya se cerraron.

        No recibe parámetros ni retorna valor; su único efecto es la salida
        a pantalla (stdout).
        """
        # Caso especial: ninguna variable fue declarada durante la ejecución
        if not self._historial:
            print("\n[Tabla de Simbolos] (vacia - no se declaro ninguna variable)\n")
            return

        # Calcula el ancho de la columna de nombres de forma dinámica:
        # toma el nombre más largo y le suma 2 caracteres de margen.
        # max() de 12 evita que la columna sea demasiado estrecha con variables cortas.
        ancho_nombre = max(len(e['name']) for e in self._historial) + 2
        ancho_nombre = max(ancho_nombre, 12)

        # Encabezado de la tabla
        print("\n" + "=" * 72)
        print("   TABLA DE SIMBOLOS - estado final del programa")
        print("=" * 72)
        print(f"  {'Variable':<{ancho_nombre}} {'Tipo':<10} {'Ambito':<10} "
              f"{'Linea':<7} {'Col':<5} Valor")
        print("  " + "-" * (ancho_nombre + 44))

        # Itera en orden de declaración: las variables aparecen en el mismo
        # orden en que se declararon en el programa fuente.
        for info in self._historial:
            print(f"  {info['name']:<{ancho_nombre}} {info['type']:<10} "
                  f"{self._formato_ambito(info['scope']):<10} "
                  f"{info['lineno']:<7} {info['col']:<5} "
                  f"{self._formato_valor(info['value'])}")

        print("=" * 72 + "\n")

    def __repr__(self):
        """
        Representación de depuración del objeto, útil en el REPL de Python
        o al imprimir el objeto directamente con print().
        """
        return f"SymbolTable(ambitos={len(self._scopes)}, simbolos={len(self._historial)})"

    # =========================================================================
    # PERSISTENCIA — volcado de la tabla a un archivo de reporte
    # =========================================================================

    def save_to_file(self, filename="tabla_simbolos.txt"):
        """
        Serializa el estado actual de la tabla en un archivo de texto plano.

        Genera el mismo formato tabular que dump(), pero dirigido a un archivo
        en lugar de a pantalla. Es útil para guardar un registro persistente
        del estado final de las variables después de la ejecución.

        La escritura usa encoding UTF-8 para soportar caracteres especiales
        en nombres de variables o valores de cadena (acentos, ñ, etc.).

        Incluye la columna ÁMBITO y la posición (línea y columna) de cada
        declaración, que es la evidencia de que el analizador semántico alimentó
        la tabla con la información de alcance exigida por la práctica.

        Parámetros:
            filename (str): ruta y nombre del archivo de salida;
                            por defecto "tabla_simbolos.txt" en el directorio actual

        No retorna valor. Efectos secundarios:
            - Crea o sobreescribe el archivo indicado.
            - Imprime confirmación en pantalla si tuvo éxito.
            - Imprime mensaje de error en pantalla si falló (no lanza excepción,
              para no interrumpir el flujo principal por un error de I/O).
        """
        try:
            # Abre en modo escritura ('w'); si el archivo ya existe, lo sobreescribe.
            # encoding='utf-8' es explícito para evitar errores en sistemas Windows
            # donde el encoding por defecto puede ser cp1252 o similar.
            with open(filename, "w", encoding="utf-8") as f:

                # Encabezado del reporte en archivo
                f.write("=" * 78 + "\n")
                f.write("   TABLA DE SIMBOLOS - REPORTE GENERADO\n")
                f.write("=" * 78 + "\n")

                # Caso especial: tabla vacía → archivo con mensaje indicativo
                if not self._historial:
                    f.write("TABLA DE SIMBOLOS VACIA: el programa no declara variables.\n")
                    return   # Termina aquí; el bloque with cierra el archivo limpiamente

                # Encabezado de columnas con ancho fijo para facilitar lectura
                f.write(f"{'VARIABLE':<20}{'TIPO':<10}{'AMBITO':<12}"
                        f"{'LINEA':<8}{'COLUMNA':<10}{'VALOR'}\n")
                f.write("-" * 78 + "\n")

                # Escribe una fila por cada variable registrada, en orden de
                # declaración y sin omitir las locales de bloques ya cerrados
                for info in self._historial:
                    f.write(f"{info['name']:<20}{info['type']:<10}"
                            f"{self._formato_ambito(info['scope']):<12}"
                            f"{info['lineno']:<8}{info['col']:<10}"
                            f"{self._formato_valor(info['value'])}\n")

                f.write("=" * 78 + "\n")
                f.write(f"Total de simbolos declarados: {len(self._historial)}\n")

            print(f"[Sistema] Tabla de simbolos guardada en: {filename}")

        except IOError as e:
            # IOError cubre errores de permisos, disco lleno, ruta inválida, etc.
            # Se captura específicamente (no Exception genérica) para no ocultar
            # bugs inesperados de otra naturaleza.
            print(f"[Error] No se pudo escribir el archivo de simbolos: {e}")
