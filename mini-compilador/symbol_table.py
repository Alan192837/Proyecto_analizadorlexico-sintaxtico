# =============================================================================
# symbol_table.py — Tabla de Simbolos
# =============================================================================
# Responsabilidad: almacenar nombre, tipo y valor de cada variable declarada.
# Es la "memoria" del interprete durante la ejecucion del programa.
#
# IMPORTANTE: Esta tabla es completamente independiente del lexer y del parser.
# Solo el interprete (interpreter.py) la escribe y lee.
# Se crea vacia al inicio de cada ejecucion y desaparece al terminar.
# =============================================================================


class SymbolTable:
    """
    Tabla de simbolos basada en un diccionario Python.

    Estructura interna de cada entrada:
        nombre -> { 'type': <str>, 'value': <valor Python> }
    """

    def __init__(self):
        self._table: dict = {}

    # ── Operaciones principales ────────────────────────────────────────────

    def declare(self, name: str, var_type: str, value=None):
        """
        Registra una variable nueva con su tipo y valor inicial.
        Lanza RuntimeError si la variable ya fue declarada en este scope.
        """
        if name in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' ya fue declarada. "
                f"No se puede declarar dos veces la misma variable."
            )
        self._table[name] = {'type': var_type, 'value': value}

    def assign(self, name: str, value):
        """
        Actualiza el valor de una variable ya declarada.
        Lanza RuntimeError si la variable no existe.
        """
        if name not in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada. "
                f"Debes declararla primero con: entero {name} = valor;"
            )
        self._table[name]['value'] = value

    def get(self, name: str):
        """
        Devuelve el valor actual de una variable.
        Lanza RuntimeError si la variable no existe.
        """
        if name not in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada. "
                f"Debes declararla antes de usarla."
            )
        return self._table[name]['value']

    def get_type(self, name: str) -> str:
        """Devuelve el tipo declarado de una variable."""
        if name not in self._table:
            raise RuntimeError(
                f"[Semantica] La variable '{name}' no fue declarada."
            )
        return self._table[name]['type']

    def exists(self, name: str) -> bool:
        """True si la variable ya fue declarada."""
        return name in self._table

    # ── Utilidad de inspeccion ─────────────────────────────────────────────

    def dump(self):
        """Imprime el contenido de la tabla al final de la ejecucion."""
        if not self._table:
            print("\n[Tabla de Simbolos] (vacia — no se declaro ninguna variable)\n")
            return
        ancho_nombre = max(len(n) for n in self._table) + 2
        ancho_nombre = max(ancho_nombre, 12)
        print("\n" + "=" * 50)
        print("   TABLA DE SIMBOLOS — estado final del programa")
        print("=" * 50)
        print(f"  {'Variable':<{ancho_nombre}} {'Tipo':<12} Valor")
        print("  " + "-" * (ancho_nombre + 22))
        for name, info in self._table.items():
            valor = info['value']
            # Mostrar booleanos con la sintaxis del lenguaje
            if isinstance(valor, bool):
                valor_str = 'verdadero' if valor else 'falso'
            else:
                valor_str = str(valor)
            print(f"  {name:<{ancho_nombre}} {info['type']:<12} {valor_str}")
        print("=" * 50 + "\n")

    def __repr__(self):
        return f"SymbolTable({self._table})"
    
#--------------------------------------------------------------------------------------------------------------

    def save_to_file(self, filename="tabla_simbolos.txt"):
        """Genera un archivo de texto con el estado actual de la tabla."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                if not self._table:
                    f.write("TABLA DE SÍMBOLOS VACÍA\n")
                    return
                
                f.write("=" * 50 + "\n")
                f.write("   TABLA DE SÍMBOLOS — REPORTE GENERADO\n")
                f.write("=" * 50 + "\n")
                f.write(f"{'Variable':<20} {'Tipo':<15} {'Valor':<15}\n")
                f.write("-" * 50 + "\n")
                
                for name, info in self._table.items():
                    valor = info['value']
                    if isinstance(valor, bool):
                        valor_str = 'verdadero' if valor else 'falso'
                    else:
                        valor_str = str(valor)
                    
                    f.write(f"{name:<20} {info['type']:<15} {valor_str:<15}\n")
                
                f.write("=" * 50 + "\n")
            print(f"[Sistema] Tabla de símbolos guardada en: {filename}")
        except IOError as e:
            print(f"[Error] No se pudo escribir el archivo de símbolos: {e}")
