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
# CATÁLOGO DE TOKENS
# Mapea cada tipo de token PLY a (número, nombre_descriptivo) para el reporte.
# El número 75 para PAR_IZQ es el identificador canónico del paréntesis.
# =============================================================================

TOKEN_CATALOG = {
    # Palabras reservadas (1-12)
    'ENTERO'      : (1,  'EnteroTipo'),
    'CADENA_TIPO' : (2,  'CadenaTipo'),
    'LOGICO_TIPO' : (3,  'LogicoTipo'),
    'SI'          : (4,  'Si'),
    'SINO'        : (5,  'Sino'),
    'LEER'        : (6,  'Leer'),
    'MOSTRAR'     : (7,  'Mostrar'),
    'VERDADERO'   : (8,  'Verdadero'),
    'FALSO'       : (9,  'Falso'),
    'Y'           : (10, 'Y'),
    'O'           : (11, 'O'),
    'NO'          : (12, 'No'),
    # Literales e identificadores (20-22)
    'NUMERO'        : (20, 'Numero'),
    'LITERAL_CADENA': (21, 'Cadena'),
    'ID'            : (22, 'Identificador'),
    # Operadores aritméticos (30-33)
    'MAS'   : (30, 'Suma'),
    'MENOS' : (31, 'Resta'),
    'POR'   : (32, 'Multiplicacion'),
    'ENTRE' : (33, 'Division'),
    # Operadores relacionales (40-45)
    'MAYOR_IG': (40, 'Mayor_Igual'),
    'MENOR_IG': (41, 'Menor_Igual'),
    'IGUAL'   : (42, 'Igual'),
    'DISTINTO': (43, 'Distinto'),
    'MAYOR'   : (44, 'Mayor'),
    'MENOR'   : (45, 'Menor'),
    # Asignación (50)
    'ASIGNAR': (50, 'Asignacion'),
    # Puntuación (60-61)
    'PUNTOCOM': (60, 'PuntoyComa'),
    'COMA'    : (61, 'Coma'),
    # Delimitadores — llaves (70-71), paréntesis (75-76)
    'LLA_IZQ': (70, 'LlaveIzq'),
    'LLA_DER': (71, 'LlaveDer'),
    'PAR_IZQ': (75, 'Paren'),
    'PAR_DER': (76, 'ParenDer'),
}


# =============================================================================
# GENERADORES DE REPORTES
# Estas funciones producen archivos de salida con información del proceso
# de compilación; son independientes de la ejecución del programa fuente.
# =============================================================================

def generar_tabla_simbolos(tabla_simbolos, tokens, filename="progfte.tab"):
    """
    Genera el reporte de la tabla de símbolos en formato .tab con cuatro columnas:
        No     — número de orden del símbolo
        LEXEMA — nombre de la variable tal como aparece en el fuente
        TOKEN  — número y nombre del token (siempre 22 Identificador para variables)
        REF    — renglón del fuente donde se declaró la variable

    Para obtener REF se escanean los tokens buscando el patrón TIPO→ID que
    corresponde a una declaración; el renglón del ID es la referencia.

    Se genera SIEMPRE, incluso cuando hay errores sintácticos, mostrando
    únicamente los símbolos declarados en enunciados válidos (el parser
    recupera errores y devuelve un AST parcial que el intérprete ejecuta).

    Parámetros:
        tabla_simbolos (SymbolTable)  : tabla de símbolos del intérprete
        tokens         (list[LexToken]): lista de tokens para extraer REF
        filename       (str)          : archivo de salida; por defecto "progfte.tab"
    """
    # Escanea los tokens para mapear nombre_variable → renglón de declaración.
    # Patrón de declaración: token TIPO (ENTERO/CADENA_TIPO/LOGICO_TIPO) seguido de ID.
    _tipos_decl = {'ENTERO', 'CADENA_TIPO', 'LOGICO_TIPO'}
    refs = {}
    for i, t in enumerate(tokens):
        if t.type in _tipos_decl and i + 1 < len(tokens):
            siguiente = tokens[i + 1]
            if siguiente.type == 'ID' and siguiente.value not in refs:
                refs[siguiente.value] = siguiente.lineno

    # Token canónico de todos los identificadores de variable
    num_id, nombre_id = TOKEN_CATALOG['ID']   # 22, 'Identificador'
    token_str = f"{num_id} {nombre_id}"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            if not tabla_simbolos._table:
                f.write("TABLA DE SÍMBOLOS VACÍA\n")
                f.write("(Sin variables declaradas o todos los enunciados tuvieron error)\n")
            else:
                # Encabezado de columnas
                f.write(f"{'No':<6} {'LEXEMA':<20} {'TOKEN':<22} {'REF'}\n")
                f.write("-" * 52 + "\n")
                for no, name in enumerate(tabla_simbolos._table, start=1):
                    ref = refs.get(name, '-')
                    f.write(f"{no:<6} {name:<20} {token_str:<22} {ref}\n")

        print(f"[Sistema] Tabla de símbolos generada en: {filename}")

    except Exception as e:
        print(f"[Error] No se pudo generar la tabla de símbolos: {e}")


def generar_reporte_compilador(tokens, errores_lexicos, filename="progfte.tok"):
    """
    Genera el reporte de lexemas y tokens en formato .tok.

    Cada entrada ocupa una línea con el formato:
        Renglón: X, Lexema: Y, Token: Z Nombre
    Los errores léxicos (caracteres no reconocidos) se intercalan según
    su número de línea con el formato:
        Renglón: X, Símbolo no identificado (char) (posible error)

    Parámetros:
        tokens         (list[LexToken])      : tokens producidos por tokenize()
        errores_lexicos(list[tuple[int,str]]): errores (lineno, char) de tokenize()
        filename       (str)                 : archivo de salida; por defecto "progfte.tok"
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Combina tokens y errores en una sola lista; ordena por (renglón, lexpos)
            # para respetar el orden exacto de aparición dentro de cada línea
            entradas = []
            for t in tokens:
                entradas.append(('token', t.lineno, t.lexpos, t))
            for lineno, lexpos, char in errores_lexicos:
                entradas.append(('error', lineno, lexpos, char))
            entradas.sort(key=lambda x: (x[1], x[2]))

            for entrada in entradas:
                if entrada[0] == 'token':
                    t = entrada[3]
                    num, nombre = TOKEN_CATALOG.get(t.type, (0, t.type))
                    lexema = f'"{t.value}"' if t.type == 'LITERAL_CADENA' else str(t.value)
                    f.write(f"Renglón: {t.lineno}, Lexema: {lexema}, Token: {num} {nombre}\n")
                else:
                    lineno, char = entrada[1], entrada[3]
                    f.write(f"Renglón: {lineno}, Símbolo no identificado ({char}) (posible error)\n")

        print(f"\n[Sistema] Reporte de tokens generado en: {filename}")

    except Exception as e:
        print(f"[Error] No se pudo generar el reporte: {e}")


def generar_codigo_depurado(tokens, errores_lexicos, filename="prog_depurado.dep"):
    """
    Reconstruye el código fuente a partir de los tokens en formato compacto:
    todos los tokens —incluidos los caracteres ilegales— concatenados en una
    sola línea sin espacios ni saltos de línea, eliminando comentarios.

    Los errores léxicos se insertan en su posición exacta (lexpos) dentro
    del stream, por lo que aparecen donde estaban en el fuente original.

    Ejemplo de salida: mostrar("Multiplicacion: "+(@ *b));

    Parámetros:
        tokens         (list[LexToken])           : tokens del programa fuente
        errores_lexicos(list[tuple[int,int,str]]) : errores (lineno, lexpos, char)
        filename       (str)                      : archivo de salida; por defecto "prog_depurado.dep"
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Mezcla tokens y caracteres ilegales ordenados por posición en el fuente
            entradas = []
            for t in tokens:
                entradas.append(('token', t.lexpos, t))
            for _, lexpos, char in errores_lexicos:
                entradas.append(('error', lexpos, char))
            entradas.sort(key=lambda x: x[1])

            for entrada in entradas:
                if entrada[0] == 'token':
                    t = entrada[2]
                    # Las cadenas recuperan sus comillas (el lexer las quitó al tokenizar)
                    if t.type == 'LITERAL_CADENA':
                        f.write(f'"{t.value}"')
                    else:
                        f.write(str(t.value))
                else:
                    f.write(entrada[2])   # escribe el carácter ilegal tal cual

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
    tokens, errores_lexicos = tokenize(source, verbose=show_tokens)

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
    # Todos los reportes se generan siempre:
    #  - progfte.tab : tabla con los símbolos declarados en enunciados válidos
    #                  (el parser recupera errores y el intérprete ejecuta lo que pudo)
    #  - prog_depurado.dep / progfte.tok : basados en tokens, independientes del AST
    generar_tabla_simbolos(interp.symbols, tokens, "progfte.tab")
    generar_codigo_depurado(tokens, errores_lexicos, "prog_depurado.dep")
    generar_reporte_compilador(tokens, errores_lexicos, "progfte.tok")


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
