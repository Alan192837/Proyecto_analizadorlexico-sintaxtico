"""
=============================================================================
main.py — Punto de Entrada Principal del Mini-Compilador
=============================================================================
Propósito general:
    Orquesta el pipeline completo de compilación e interpretación:
        1. Tokenización  (lexer.py)    → convierte texto en tokens
        2. Parsing       (parser.py)   → convierte tokens en AST
        3. Ejecución     (interpreter) → recorre el AST y produce resultados
        4. Reportes      (este módulo) → genera archivos de salida

    También actúa como interfaz de línea de comandos (CLI): parsea los
    argumentos de sys.argv para activar modos de depuración y seleccionar
    la fuente del programa (ejemplos embebidos o archivo externo).

Uso desde la terminal (dentro de la carpeta del proyecto):
    python main.py                       → ejecuta los ejemplos embebidos
    python main.py archivo.txt           → ejecuta un programa propio
    python main.py --tokens              → muestra los tokens del lexer
    python main.py --ast                 → muestra el AST del parser
    python main.py --no-sym              → oculta la tabla de símbolos
    python main.py archivo.txt --tokens --ast  → combinación de flags

Archivos generados automáticamente en cada ejecución:
    progfte.tok           → tokens generados (incluye errores léxicos)
    progfte.dep           → codigo fuente depurado (solo tokens válidos)
    progfte.tab           → tabla de símbolos en formato de texto (incluye errores)
=============================================================================
"""

import sys   # Para acceder a sys.argv (argumentos de línea de comandos)
import os    # Para os.path.isfile() al validar archivos pasados como argumentos

# Importa las tres fases del pipeline
from lexer       import tokenize    # Fase 1: análisis léxico
from parser      import parse       # Fase 2: análisis sintáctico
from interpreter import Interpreter # Fase 3: ejecución


# =============================================================================
# CONJUNTO DE TOKENS DE ERROR
# Centraliza los tipos de token que representan errores léxicos para que
# las funciones de reporte los identifiquen y los traten de forma especial
# (nota aclaratoria en lugar de simplemente omitirlos).
# =============================================================================
TOKENS_ERROR = {'ID_CON_ERROR', 'CADENA_ERROR', 'ERROR_LEXICO'}


# =============================================================================
# GENERADORES DE REPORTES
# =============================================================================

def generar_archivo_tokens(tokens, filename="progfte.tok"):
    """
    Genera el archivo .tok con la lista de tokens del programa fuente.

    Formato de salida para tokens normales:
        Renglon: <n>, Lexema: <valor>, Token: <tipo>, REF: <ref>

    Formato de salida para tokens de error:
        Renglon: <n>, Lexema: <valor>, Token: <tipo>, REF: <ref>  *** ERROR LEXICO ***

    La columna REF sigue las mismas reglas que en .tab:
        - Tokens fijos (palabras reservadas, operadores, etc.) → número asignado
        - Identificadores (ID) → número único incremental desde 300
        - Tokens de error → 900 / 901 / 902

    Parámetros:
        tokens   (list[LexToken]): lista de tokens generados por el lexer
        filename (str)           : nombre del archivo de salida
    """
    # Referencias fijas — mismas que en generar_tabla para consistencia
    referencias = {
        'MAIN'          : 100,
        'PAR_IZQ'       : 75,
        'PAR_DER'       : 76,
        'LLA_IZQ'       : 77,
        'LLA_DER'       : 78,
        'PUNTOCOM'      : 79,
        'MAS'           : 80,
        'MENOS'         : 81,
        'POR'           : 82,
        'ENTRE'         : 83,
        'ASIGNAR'       : 84,
        'MAYOR'         : 85,
        'MENOR'         : 86,
        'MAYOR_IG'      : 87,
        'MENOR_IG'      : 88,
        'IGUAL'         : 89,
        'DISTINTO'      : 90,
        'ENTERO'        : 101,
        'CADENA_TIPO'   : 102,
        'LOGICO_TIPO'   : 103,
        'SI'            : 104,
        'SINO'          : 105,
        'MOSTRAR'       : 106,
        'LEER'          : 107,
        'VERDADERO'     : 108,
        'FALSO'         : 109,
        'NUMERO'        : 201,
        'LITERAL_CADENA': 202,
        'ERROR_LEXICO'  : 900,
        'ID_CON_ERROR'  : 901,
        'CADENA_ERROR'  : 902,
    }

    # Tabla de IDs incremental — misma lógica que en generar_tabla
    id_refs    = {}
    id_counter = 300

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("LISTA DE TOKENS\n")
            f.write("-" * 40 + "\n")

            for t in tokens:
                lexema = str(t.value)
                token  = t.type

                # Calcula REF según el tipo de token
                if token == 'ID':
                    if lexema not in id_refs:
                        id_refs[lexema] = id_counter
                        id_counter += 1
                    ref = id_refs[lexema]
                else:
                    ref = referencias.get(token, 999)

                # Construye la línea con REF incluida
                linea = f"Renglon: {t.lineno}, Lexema: {lexema}, Token: {token}, REF: {ref}"

                # Agrega nota visual al final si es un error léxico
                if token in TOKENS_ERROR:
                    linea += "  *** ERROR LEXICO ***"

                f.write(linea + "\n")

        print(f"[Sistema] Archivo de tokens generado en: {filename}")

    except Exception as e:
        print(f"[Error] No se pudo generar el archivo .tok: {e}")


def generar_tabla(tokens, filename="progfte.tab"):
    """
    Genera el archivo .tab con tabla de símbolos en formato tabular.

    Formato de cada fila:
        No    LEXEMA    TOKEN    REF    NOTA

    REF para identificadores (ID):
        Cada variable recibe un número único incremental a partir de 300.
        Si la misma variable aparece más de una vez, conserva su REF original.
        Ejemplo:  llueve → 300,  frio → 301,  otra → 302 ...
        Esto replica el comportamiento mostrado en el ejemplo de la rúbrica
        donde cada ID tenía su propio número (300, 301, 303...).

    REF para tokens de error:
        ERROR_LEXICO  → 900
        ID_CON_ERROR  → 901
        CADENA_ERROR  → 902

    La columna NOTA aparece solo en filas de error: '(posible error)'.

    Parámetros:
        tokens   (list[LexToken]): lista de tokens generados por el lexer
        filename (str)           : nombre del archivo de salida
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:

            # Encabezado
            f.write(f"{'No':<5}{'LEXEMA':<40}{'TOKEN':<20}{'REF':<10}{'NOTA'}\n")
            f.write("-" * 80 + "\n")

<<<<<<< HEAD
            # Referencias fijas para tokens no-ID
=======
            # Referencias
>>>>>>> 53bcadde508435fc9f376317e9e30a6d92cab4bd
            referencias = {
                'MAIN'          : 100,
                'PAR_IZQ'       : 75,
                'PAR_DER'       : 76,
                'LLA_IZQ'       : 77,
                'LLA_DER'       : 78,
                'PUNTOCOM'      : 79,
                'MAS'           : 80,
                'MENOS'         : 81,
                'POR'           : 82,
                'ENTRE'         : 83,
                'ASIGNAR'       : 84,
                'MAYOR'         : 85,
                'MENOR'         : 86,
                'MAYOR_IG'      : 87,
                'MENOR_IG'      : 88,
                'IGUAL'         : 89,
                'DISTINTO'      : 90,
                'ENTERO'        : 101,
                'CADENA_TIPO'   : 102,
                'LOGICO_TIPO'   : 103,
                'SI'            : 104,
                'SINO'          : 105,
                'MOSTRAR'       : 106,
                'LEER'          : 107,
                'VERDADERO'     : 108,
                'FALSO'         : 109,
                'NUMERO'        : 201,
                'LITERAL_CADENA': 202,
                # Tokens de error
                'ERROR_LEXICO'  : 900,
                'ID_CON_ERROR'  : 901,
                'CADENA_ERROR'  : 902,
            }

            # Tabla de IDs: mapea nombre_variable → REF único asignado
            # Se llena dinámicamente conforme aparecen nuevos identificadores.
            # La primera variable recibe 300, la segunda 301, y así sucesivamente.
            id_refs   = {}   # { 'llueve': 300, 'frio': 301, ... }
            id_counter = 300  # Contador que se incrementa con cada ID nuevo

            for i, t in enumerate(tokens, start=1):
                lexema = str(t.value)
                token  = t.type

                if token == 'ID':
                    # Si este nombre de variable ya fue visto, reutiliza su REF.
                    # Si es nuevo, asígnale el siguiente número disponible.
                    if lexema not in id_refs:
                        id_refs[lexema] = id_counter
                        id_counter += 1
                    ref = id_refs[lexema]
                else:
                    ref = referencias.get(token, 999)

                # Columna NOTA: solo visible en tokens de error
                nota = "(posible error)" if token in TOKENS_ERROR else ""

                f.write(f"{i:<5}{lexema:<40}{token:<20}{ref:<10}{nota}\n")

        print(f"[Sistema] Archivo .tab generado correctamente")

    except Exception as e:
        print(f"[Error] No se pudo generar .tab: {e}")


def generar_codigo_depurado(tokens, filename="progfte.dep"):
    """
    Genera una versión depurada del código fuente a partir de los tokens.

    Elimina comentarios, espacios, tabuladores y saltos de línea,
    reconstruyendo el programa de forma compacta. Todos los lexemas
    aparecen en el archivo, incluyendo los tokens de error, tal como
    fueron escritos en el fuente original (sin etiquetas ni marcas).

    Casos especiales:
        - LITERAL_CADENA : se restauran las comillas dobles (el lexer las quita)
        - CADENA_ERROR   : se restaura solo la comilla de apertura, ya que
                           la de cierre nunca existió en el fuente
        - ID_CON_ERROR   : se escribe el lexema completo, ej: ent#ero
        - ERROR_LEXICO   : se escribe el carácter ilegal aislado, ej: @

    Parámetros:
        tokens   (list[LexToken]): lista de tokens generados por el lexer
        filename (str)           : nombre del archivo de salida
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:

            for t in tokens:
                if t.type == 'LITERAL_CADENA':
                    # Cadena válida: restaura las comillas que el lexer quitó
                    f.write(f'"{t.value.strip()}"')
                elif t.type == 'CADENA_ERROR':
                    # Cadena sin cerrar: restaura solo la comilla de apertura
                    # ya que nunca hubo comilla de cierre en el fuente original
                    f.write(f'"{t.value.strip()}')
                else:
                    # Todos los demás tokens (válidos y de error) se escriben
                    # con su lexema original, sin ninguna marca adicional
                    f.write(str(t.value).strip())

        print(f"[Sistema] Código fuente depurado generado en: {filename}")

    except Exception as e:
        print(f"[Error] No se pudo generar el código depurado: {e}")


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def run_source(source: str, show_tokens: bool = False, show_ast: bool = False,
               show_symbols: bool = True, label: str = ""):
    """
    Ejecuta el pipeline completo sobre un string de código fuente.

    Parámetros:
        source       (str) : código fuente completo del programa a ejecutar
        show_tokens  (bool): si True, imprime los tokens en pantalla (flag --tokens)
        show_ast     (bool): si True, imprime el AST en pantalla (flag --ast)
        show_symbols (bool): reservado para uso futuro
        label        (str) : texto descriptivo del programa
    """
    sep = "=" * 60
    print(f"\n{sep}")
    if label:
        print(f"  {label}")
    print(sep)

    # ── Fase 1: Análisis léxico ────────────────────────────────────────────
    tokens = tokenize(source, verbose=show_tokens)

    # ── Fase 2: Análisis sintáctico ────────────────────────────────────────
    ast = parse(source)

    if show_ast and ast is not None:
        print("\n-- AST --")
        print(ast)

    # ── Fase 3: Ejecución ─────────────────────────────────────────────────
    print("\n-- SALIDA --")
    interp = Interpreter()
    try:
        interp.run(ast)
    except RuntimeError as e:
        print(f"\n[Error de ejecucion] {e}")

    # ── Fase 4: Generación de reportes ────────────────────────────────────
    # CORRECCIÓN: los reportes .tok y .tab se generan SIEMPRE, incluso si
    # el parsing falló, para que los errores léxicos sean visibles.
    # Solo el .dep requiere ast válido (necesita el árbol para reconstruir).
    generar_archivo_tokens(tokens, "progfte.tok")
    generar_tabla(tokens, "progfte.tab")

    if ast is not None:
        generar_codigo_depurado(tokens, "progfte.dep")
<<<<<<< HEAD
=======
        generar_tabla(tokens, "progfte.tab")

    # SIEMPRE generar tokens
    generar_archivo_tokens(tokens, "progfte.tok")
    
>>>>>>> 53bcadde508435fc9f376317e9e30a6d92cab4bd


# =============================================================================
# EJEMPLOS DE PRUEBA EMBEBIDOS
# =============================================================================

EJEMPLOS = [

    # ── Ejemplo 12: operadores lógicos NO y O combinados ──────────────────
    (
        "EJEMPLO 12 — Logico con operador NO y O",
        """
        logico llueve = falso;
        logico frio   = verdadero;

        si (no llueve o frio) {
            mostrar(1);
        } sino {
            mostrar(0);
        }

        mostrar(llueve);
        mostrar(frio);
        """
    ),

    # ── Ejemplo de errores léxicos — para probar las correcciones ─────────
    (
        "EJEMPLO ERRORES — ID con caracter ilegal y cadena sin cerrar",
        """
        entero ent@ro = 5;
        mostrar("Hola mundo);
        entero val@r_x = 10;
        """
    ),
]


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """
    Punto de entrada del programa: parsea los argumentos de línea de comandos
    y decide si ejecutar un archivo externo o los ejemplos embebidos.
    """
    show_tokens  = '--tokens' in sys.argv
    show_ast     = '--ast'    in sys.argv
    hide_symbols = '--no-sym' in sys.argv

    source_file = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and os.path.isfile(arg):
            source_file = arg
            break

    if source_file:
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                source = f.read()
        except UnicodeDecodeError:
            with open(source_file, 'r', encoding='latin-1') as f:
                source = f.read()

        run_source(source,
                   show_tokens=show_tokens,
                   show_ast=show_ast,
                   show_symbols=not hide_symbols,
                   label=f"Archivo: {source_file}")
        return

    print("\n" + "#" * 60)
    print("  MINI-INTERPRETE — Calculadora Extendida con PLY")
    print("  Sintaxis en Espanol")
    print("#" * 60)

    for label, source in EJEMPLOS:
        run_source(source,
                   show_tokens=show_tokens,
                   show_ast=show_ast,
                   show_symbols=not hide_symbols,
                   label=label)

    print("\n" + "=" * 60)
    print("  Todos los ejemplos ejecutados.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
