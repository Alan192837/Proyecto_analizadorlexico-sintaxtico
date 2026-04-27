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
    progfte.tok           → tokens generados
    progfte.dep           → codigo fuente depurado
    progfte.tab           → tabla de símbolos en formato de texto
=============================================================================
"""

import sys   # Para acceder a sys.argv (argumentos de línea de comandos)
import os    # Para os.path.isfile() al validar archivos pasados como argumentos

# Importa las tres fases del pipeline
from lexer       import tokenize    # Fase 1: análisis léxico
from parser      import parse       # Fase 2: análisis sintáctico
from interpreter import Interpreter # Fase 3: ejecución


# =============================================================================
# GENERADORES DE REPORTES
# Estas funciones producen archivos de salida con información del proceso
# de compilación; son independientes de la ejecución del programa fuente.
# =============================================================================

def generar_archivo_tokens(tokens, filename="progfte.tok"):
    """
    Genera un archivo de texto con la lista de tokens producidos por el lexer.

    Este archivo corresponde al formato requerido por la rúbrica para el
    análisis léxico en forma de lista, donde cada línea representa un token
    con su información básica.

    Formato de salida:
        Renglon: <número de línea>, Lexema: <valor>, Token: <tipo>

    Parámetros:
        tokens   (list[LexToken]): lista de tokens generados por el lexer
        filename (str)           : nombre del archivo de salida;
                                   por defecto "progfte.tok"

    No retorna valor. Efectos secundarios:
        - Crea o sobrescribe el archivo indicado.
        - Imprime un mensaje de confirmación o error en consola.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("LISTA DE TOKENS\n")
            f.write("-" * 40 + "\n")
            
            for t in tokens:
                f.write(f"Renglon: {t.lineno}, Lexema: {t.value}, Token: {t.type}\n")

        print(f"[Sistema] Archivo de tokens generado en: {filename}")

    except Exception as e:
        print(f"[Error] No se pudo generar el archivo .tok: {e}")

def generar_tabla(tokens, filename="progfte.tab"):
    """
    Genera un archivo en formato tabla con los tokens del programa fuente.

    Este archivo cumple con el formato tabular solicitado por la rúbrica,
    donde cada token se representa en una fila con las siguientes columnas:
        - No     : número consecutivo del token
        - LEXEMA : valor textual del token
        - TOKEN  : tipo de token reconocido por el lexer
        - REF    : código numérico asociado al tipo de token

    La columna REF es definida mediante un diccionario interno que asigna
    un identificador numérico a cada tipo de token. Este valor no es generado
    por PLY, sino que es parte del formato académico requerido.

    Parámetros:
        tokens   (list[LexToken]): lista de tokens generados por el lexer
        filename (str)           : nombre del archivo de salida;
                                   por defecto "progfte.tab"

    No retorna valor. Efectos secundarios:
        - Crea o sobrescribe el archivo indicado.
        - Imprime un mensaje de confirmación o error en consola.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:

            # Encabezado tipo tabla
            f.write(f"{'No':<5}{'LEXEMA':<40}{'TOKEN':<20}{'REF':<10}\n")
            f.write("-" * 60 + "\n")

            # Referencias (puedes ajustar)
            referencias = {
                'MAIN': 100,
                'PAR_IZQ': 75,
                'PAR_DER': 76,
                'LLA_IZQ': 77,
                'LLA_DER': 78,
                'PUNTOCOM': 79,
                'MAS': 80,
                'MENOS': 81,
                'POR': 82,
                'ENTRE': 83,
                'ASIGNAR': 84,
                'MAYOR': 85,
                'MENOR': 86,
                'MAYOR_IG': 87,
                'MENOR_IG': 88,
                'IGUAL': 89,
                'DISTINTO': 90,
                'ENTERO': 101,
                'CADENA_TIPO': 102,
                'LOGICO_TIPO': 103,
                'SI': 104,
                'SINO': 105,
                'MOSTRAR': 106,
                'LEER': 107,
                'VERDADERO': 108,
                'FALSO': 109,
                'ID': 200,
                'NUMERO': 201,
                'LITERAL_CADENA': 202
            }

            # Llenado
            for i, t in enumerate(tokens, start=1):
                lexema = str(t.value)
                token = t.type
                ref = referencias.get(token, 999)

                f.write(f"{i:<5}{lexema:<40}{token:<20}{ref:<10}\n")

        print(f"[Sistema] Archivo .tab generado correctamente")

    except Exception as e:
        print(f"[Error] No se pudo generar .tab: {e}")

def generar_codigo_depurado(tokens, filename="progfte.dep"):
    """
    Genera una versión depurada del código fuente a partir de los tokens.

    Este proceso reconstruye el programa original eliminando:
        - Comentarios
        - Espacios innecesarios
        - Formato irregular

    El resultado es un código compacto donde los lexemas aparecen de forma
    continua, respetando únicamente el contenido esencial del programa.

    Consideraciones:
        - Las cadenas (LITERAL_CADENA) conservan su contenido original,
          incluyendo espacios internos, ya que forman parte del valor.
        - No se insertan saltos de línea ni espacios adicionales.

    Parámetros:
        tokens   (list[LexToken]): lista de tokens generados por el lexer
        filename (str)           : nombre del archivo de salida;
                                   por defecto "progfte.dep"

    No retorna valor. Efectos secundarios:
        - Crea o sobrescribe el archivo indicado.
        - Imprime un mensaje de confirmación o error en consola.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:

            for t in tokens:
                if t.type == 'LITERAL_CADENA':
                    f.write(f'"{t.value.strip()}"')
                else:
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

    Es el corazón de este módulo: coordina las tres fases de compilación
    e interpretación y genera los archivos de reporte. Tanto la ejecución
    de ejemplos embebidos como la de archivos externos pasan por aquí.

    Pipeline interno:
        1. tokenize()       → análisis léxico (siempre se ejecuta)
        2. parse()          → análisis sintáctico (construye el AST)
        3. Interpreter.run()→ ejecución del AST
        4. Reportes         → archivos de salida (progfte.txt, etc.)

    Parámetros:
        source       (str) : código fuente completo del programa a ejecutar
        show_tokens  (bool): si True, imprime los tokens en pantalla (flag --tokens)
        show_ast     (bool): si True, imprime el AST en pantalla (flag --ast)
        show_symbols (bool): reservado para uso futuro; actualmente los símbolos
                             se guardan siempre en archivo (no se usa en lógica)
        label        (str) : texto descriptivo del programa que se muestra
                             en el separador visual antes de la ejecución
    """
    sep = "=" * 60
    # Separador visual entre ejecuciones (útil cuando se corren varios ejemplos)
    print(f"\n{sep}")
    if label:
        print(f"  {label}")
    print(sep)

    # ── Fase 1: Análisis léxico ────────────────────────────────────────────
    # tokenize() siempre se ejecuta (para generar el reporte y el código depurado)
    # pero solo imprime en pantalla si show_tokens es True
    tokens = tokenize(source, verbose=show_tokens)

    # ── Fase 2: Análisis sintáctico ────────────────────────────────────────
    # parse() devuelve el AST o None si hay errores sintácticos
    ast = parse(source)

    # Imprime el AST completo solo si se activó el flag --ast y no hubo errores
    if show_ast and ast is not None:
        print("\n-- AST --")
        print(ast)

    # ── Fase 3: Ejecución ─────────────────────────────────────────────────
    print("\n-- SALIDA --")
    interp = Interpreter()
    try:
        interp.run(ast)
    except RuntimeError as e:
        # Captura errores en tiempo de ejecución (uso antes de declaración,
        # división por cero, error de tipo) sin detener el programa principal;
        # permite que los reportes se generen igualmente.
        print(f"\n[Error de ejecucion] {e}")

    # ── Fase 4: Generación de reportes ────────────────────────────────────
    # Solo genera los archivos si el parsing fue exitoso (ast no es None),
    # ya que sin AST la tabla de símbolos estará vacía y los archivos
    # no tendrían información útil.
    if ast is not None:
        generar_codigo_depurado(tokens, "progfte.dep")
        generar_tabla(tokens, "progfte.tab")

    # SIEMPRE generar tokens
        generar_archivo_tokens(tokens, "progfte.tok")
    


# =============================================================================
# EJEMPLOS DE PRUEBA EMBEBIDOS
# Cada elemento de la lista es una tupla (etiqueta, código_fuente).
# Los nombres de variable evitan las palabras reservadas del lenguaje:
#   y, o, no, si, sino, entero, cadena, logico, verdadero, falso, leer, mostrar
# =============================================================================

EJEMPLOS = [

    # ── Ejemplo 12: operadores lógicos NO y O combinados ──────────────────
    # Demuestra la evaluación de expresiones lógicas compuestas y la
    # precedencia entre NOT (mayor) y OR (menor).
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
]
   


# =============================================================================
# FUNCIÓN PRINCIPAL — lógica de arranque y parseo de argumentos CLI
# =============================================================================

def main():
    """
    Punto de entrada del programa: parsea los argumentos de línea de comandos
    y decide si ejecutar un archivo externo o los ejemplos embebidos.

    Flags reconocidos (pueden combinarse):
        --tokens  → activa verbose=True en tokenize() para ver cada token
        --ast     → imprime el AST completo tras el parsing
        --no-sym  → reservado; en la implementación actual no suprime la tabla
                    (la tabla siempre se guarda en archivo)

    Argumento posicional:
        Cualquier argumento que no empiece con '--' y sea un archivo existente
        se interpreta como el programa fuente a ejecutar.
    """
    # ── Detección de flags ─────────────────────────────────────────────────
    show_tokens  = '--tokens' in sys.argv   # Activa impresión de tokens
    show_ast     = '--ast'    in sys.argv   # Activa impresión del AST
    hide_symbols = '--no-sym' in sys.argv   # Flag registrado pero no usado actualmente

    # ── Búsqueda de archivo fuente en los argumentos ───────────────────────
    # Itera sobre todos los argumentos buscando el primero que sea un archivo
    # existente y no sea un flag (no empieza con '--').
    # Esto permite que el archivo se pase en cualquier posición relativa a los flags.
    source_file = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and os.path.isfile(arg):
            source_file = arg
            break   # Solo se procesa el primer archivo encontrado

    # ── Modo archivo: ejecuta el programa del archivo ──────────────────────
    if source_file:
        try:
            # Intenta leer con UTF-8 (encoding estándar moderno)
            with open(source_file, 'r', encoding='utf-8') as f:
                source = f.read()
        except UnicodeDecodeError:
            # Si falla UTF-8 (archivo guardado en encoding antiguo, común en Windows),
            # reintenta con latin-1 que acepta cualquier byte del rango 0-255
            with open(source_file, 'r', encoding='latin-1') as f:
                source = f.read()

        run_source(source,
                   show_tokens=show_tokens,
                   show_ast=show_ast,
                   show_symbols=not hide_symbols,
                   label=f"Archivo: {source_file}")
        return   # Termina aquí; no ejecuta los ejemplos embebidos

    # ── Modo demo: ejecuta todos los ejemplos embebidos ────────────────────
    print("\n" + "#" * 60)
    print("  MINI-INTERPRETE — Calculadora Extendida con PLY")
    print("  Sintaxis en Espanol")
    print("#" * 60)

    # Itera sobre los ejemplos: cada uno es una tupla (etiqueta, código_fuente)
    for label, source in EJEMPLOS:
        run_source(source,
                   show_tokens=show_tokens,
                   show_ast=show_ast,
                   show_symbols=not hide_symbols,
                   label=label)

    print("\n" + "=" * 60)
    print("  Todos los ejemplos ejecutados.")
    print("=" * 60 + "\n")


# =============================================================================
# PUNTO DE ENTRADA DEL SCRIPT
# Este bloque garantiza que main() solo se ejecute cuando el archivo se corre
# directamente (python main.py), no cuando se importa desde otro módulo.
# Es una convención estándar de Python para módulos ejecutables.
# =============================================================================
if __name__ == '__main__':
    main()
