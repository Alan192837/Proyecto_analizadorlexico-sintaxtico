# =============================================================================
# main.py — Punto de entrada principal
# =============================================================================
# Uso desde la terminal (dentro de la carpeta milenguaje/):
#
#   python main.py                  -> ejecuta los 11 ejemplos embebidos
#   python main.py archivo.txt      -> ejecuta un programa propio
#   python main.py --tokens         -> muestra tokens generados por el lexer
#   python main.py --ast            -> muestra el AST generado por el parser
#   python main.py --no-sym         -> oculta la tabla de simbolos
#   python main.py archivo.txt --tokens --ast
# =============================================================================

import sys
import os

from lexer       import tokenize
from parser      import parse
from interpreter import Interpreter


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def generar_reporte_compilador(tokens, tabla_simbolos, filename="progfte.txt"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("="*60 + "\n")
            f.write("       REPORTE DE COMPILACIÓN - MINI-LENGUAJE\n")
            f.write("="*60 + "\n\n")

            # SECCIÓN 1: LISTA DE TOKENS
            f.write("1. ANÁLISIS LÉXICO (LISTA DE TOKENS)\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'Línea':<8} {'Tipo de Token':<18} {'Valor':<15}\n")
            f.write("-" * 40 + "\n")
            for t in tokens:
                f.write(f"{t.lineno:<8} {t.type:<18} {repr(t.value):<15}\n")
            f.write("\n\n")

            # SECCIÓN 2: TABLA DE SÍMBOLOS
            f.write("2. TABLA DE SÍMBOLOS (ESTADO FINAL)\n")
            f.write("-" * 40 + "\n")
            if not tabla_simbolos._table:
                f.write("No se declararon variables.\n")
            else:
                f.write(f"{'Variable':<15} {'Tipo':<12} {'Valor Final':<15}\n")
                f.write("-" * 40 + "\n")
                for name, info in tabla_simbolos._table.items():
                    val = info['value']
                    # Formato para booleanos en el lenguaje
                    if isinstance(val, bool): val = "verdadero" if val else "falso"
                    f.write(f"{name:<15} {info['type']:<12} {str(val):<15}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("FIN DEL REPORTE\n")
            
        print(f"\n[Sistema] Reporte integral generado en: {filename}")
    except Exception as e:
        print(f"[Error] No se pudo generar el reporte: {e}")
        
def generar_codigo_depurado(tokens, filename="prog_depurado.txt"):
    """
    Reconstruye el código fuente a partir de los tokens, 
    eliminando comentarios y normalizando espacios.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Mantendremos un registro de la línea actual para respetar los saltos de línea
            linea_actual = 1
            
            for i, t in enumerate(tokens):
                # Si el token está en una línea nueva, saltamos de línea en el archivo
                if t.lineno > linea_actual:
                    f.write("\n" * (t.lineno - linea_actual))
                    linea_actual = t.lineno
                
                # Escribimos el valor del token (o su representación para cadenas)
                if t.type == 'CADENA':
                    f.write(f'"{t.value}"')
                else:
                    f.write(str(t.value))
                
                # Añadimos un espacio entre tokens de la misma línea para que no se peguen
                # pero solo si el siguiente token está en la misma línea
                #if i + 1 < len(tokens) and tokens[i+1].lineno == t.lineno:
                 #   f.write(" ")
            
        print(f"[Sistema] Código fuente depurado generado en: {filename}")
    except Exception as e:
        print(f"[Error] No se pudo generar el código depurado: {e}")

def run_source(source: str, show_tokens: bool = False, show_ast: bool = False,
               show_symbols: bool = True, label: str = ""):
    """
    Ejecuta el pipeline completo sobre 'source':
      1. Tokenizacion  (lexer)
      2. Parsing       (parser -> AST)
      3. Ejecucion     (interpreter)
      4. Tabla final   (symbol_table)
    """
    sep = "=" * 60
    print(f"\n{sep}")
    if label:
        print(f"  {label}")
    print(sep)
    
    # Fase 1: mostrar tokens 
    tokens = tokenize(source, verbose=show_tokens) 

    # Fase 2: parsing
    ast = parse(source)

    if show_ast and ast is not None:
        print("\n-- AST --")
        print(ast)

    # Fase 3: ejecucion
    print("\n-- SALIDA --")
    interp = Interpreter()
    try:
        interp.run(ast)
    except RuntimeError as e:
        print(f"\n[Error de ejecucion] {e}")
     #impresion de la tabla de simbolos   
    if ast is not None:
        interp.save_symbols("resultado_simbolos.txt")
        generar_codigo_depurado(tokens, "prog_depurado.txt")
    #Generamos el archivo .tok, con la tabla de simbolos y la lista de tokens
    generar_reporte_compilador(tokens, interp.symbols, "progfte.txt")


# =============================================================================
# EJEMPLOS DE PRUEBA
# Todos los nombres de variable evitan las palabras reservadas:
#   y, o, no, si, sino, entero, cadena, logico, verdadero, falso, leer, mostrar
# =============================================================================

EJEMPLOS = [

    # 12 ────────────────────────────────────────────────────────────────────
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


def main():
    show_tokens  = '--tokens' in sys.argv
    show_ast     = '--ast'    in sys.argv
    hide_symbols = '--no-sym' in sys.argv

    # Busca un archivo .txt pasado como argumento
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
            # Fallback si el archivo no tiene encoding UTF-8
            with open(source_file, 'r', encoding='latin-1') as f:
                source = f.read()
        run_source(source,
                   show_tokens=show_tokens,
                   show_ast=show_ast,
                   show_symbols=not hide_symbols,
                   label=f"Archivo: {source_file}")
        return

    # Sin argumento: corre todos los ejemplos
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

