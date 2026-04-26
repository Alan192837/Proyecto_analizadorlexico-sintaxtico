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
    progfte.txt            → reporte léxico + tabla de símbolos
    prog_depurado.txt      → código fuente reconstruido sin comentarios
    resultado_simbolos.txt → tabla de símbolos en formato de texto
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

def generar_reporte_compilador(tokens, tabla_simbolos, filename="progfte.txt"):
    """
    Genera un reporte completo de la compilación en un archivo de texto.

    El reporte tiene dos secciones:
        1. Análisis léxico: lista de todos los tokens con línea, tipo y valor.
        2. Tabla de símbolos: estado final de todas las variables declaradas.

    Este archivo es útil para depuración y para entender cómo el compilador
    interpretó el programa fuente.

    Parámetros:
        tokens          (list[LexToken]) : lista de tokens producida por tokenize()
        tabla_simbolos  (SymbolTable)    : tabla de símbolos del intérprete
                                          tras la ejecución completa del programa
        filename        (str)            : nombre del archivo de salida;
                                          por defecto "progfte.txt"

    No retorna valor. Efectos secundarios:
        - Crea o sobreescribe el archivo indicado.
        - Imprime confirmación o error en stdout.

    """
    try:
        # Abre el archivo en escritura con UTF-8 para soportar acentos y ñ
        with open(filename, "w", encoding="utf-8") as f:

            # ── Encabezado del reporte ────────────────────────────────────
            f.write("="*60 + "\n")
            f.write("       REPORTE DE COMPILACIÓN - MINI-LENGUAJE\n")
            f.write("="*60 + "\n\n")

            # ── Sección 1: Análisis léxico ────────────────────────────────
            f.write("1. ANÁLISIS LÉXICO (LISTA DE TOKENS)\n")
            f.write("-" * 40 + "\n")
            # Encabezado de columnas con ancho fijo para alineación visual
            f.write(f"{'Línea':<8} {'Tipo de Token':<18} {'Valor':<15}\n")
            f.write("-" * 40 + "\n")
            # Una línea por token; repr() en el valor muestra las comillas
            # en cadenas y hace explícito el tipo del valor
            for t in tokens:
                f.write(f"{t.lineno:<8} {t.type:<18} {repr(t.value):<15}\n")
            f.write("\n\n")

            # ── Sección 2: Tabla de símbolos ──────────────────────────────
            f.write("2. TABLA DE SÍMBOLOS (ESTADO FINAL)\n")
            f.write("-" * 40 + "\n")

            # Caso especial: ninguna variable fue declarada
            if not tabla_simbolos._table:
                f.write("No se declararon variables.\n")
            else:
                f.write(f"{'Variable':<15} {'Tipo':<12} {'Valor Final':<15}\n")
                f.write("-" * 40 + "\n")
                for name, info in tabla_simbolos._table.items():
                    val = info['value']
                    # Convierte True/False a verdadero/falso del lenguaje
                    if isinstance(val, bool):
                        val = "verdadero" if val else "falso"
                    f.write(f"{name:<15} {info['type']:<12} {str(val):<15}\n")

            # ── Pie del reporte ────────────────────────────────────────────
            f.write("\n" + "="*60 + "\n")
            f.write("FIN DEL REPORTE\n")

        print(f"\n[Sistema] Reporte integral generado en: {filename}")

    except Exception as e:
        # Captura amplia porque pueden fallar tanto la apertura del archivo
        # como el formateo de algún token con valor inusual
        print(f"[Error] No se pudo generar el reporte: {e}")


def generar_codigo_depurado(tokens, filename="prog_depurado.txt"):
    """
    Reconstruye el código fuente a partir de los tokens, eliminando
    comentarios y normalizando espacios, luego lo escribe en un archivo.

    Esta técnica se conoce como "pretty-printing" o "source reconstruction":
    a partir de los tokens (que ya no contienen comentarios ni espacios
    irregulares) se reconstruye el código de forma limpia.

    La reconstrucción respeta los números de línea originales insertando
    saltos de línea cuando un token pertenece a una línea posterior a la
    última escrita, lo que preserva la estructura visual del programa.


    Parámetros:
        tokens   (list[LexToken]): lista de tokens del programa fuente
        filename (str)           : nombre del archivo de salida;
                                   por defecto "prog_depurado.txt"

    No retorna valor. Efectos secundarios:
        - Crea o sobreescribe el archivo indicado.
        - Imprime confirmación o error en stdout.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Rastrea la línea que se está escribiendo actualmente
            # para saber cuántos saltos de línea insertar antes del próximo token
            linea_actual = 1

            for i, t in enumerate(tokens):
                # Si el token pertenece a una línea posterior a la actual,
                # inserta los saltos de línea necesarios para posicionarse ahí
                if t.lineno > linea_actual:
                    f.write("\n" * (t.lineno - linea_actual))
                    linea_actual = t.lineno

                # Escribe el valor del token; para cadenas las rodea de comillas
                # ya que el lexer las quitó al tokenizar
                if t.type == 'CADENA':
                    f.write(f'"{t.value}"')
                else:
                    f.write(str(t.value))

                if i + 1 < len(tokens) and tokens[i+1].lineno == t.lineno:
                    f.write(" ")

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
        interp.save_symbols("resultado_simbolos.txt")
        generar_codigo_depurado(tokens, "prog_depurado.txt")

    # El reporte léxico + tabla de símbolos se genera siempre,
    # incluso si hubo errores, porque los tokens sí fueron producidos
    generar_reporte_compilador(tokens, interp.symbols, "progfte.txt")


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
