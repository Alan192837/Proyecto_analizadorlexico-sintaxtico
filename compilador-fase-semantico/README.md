# Mini-Compilador — Calculadora Extendida con PLY
## Sintaxis completamente en Espanol

---

## Fases del compilador

| Fase | Archivo | Que hace |
|---|---|---|
| 1. Analisis lexico | `lexer.py` | Convierte el texto fuente en tokens |
| 2. Analisis sintactico | `parser.py` | Construye el AST a partir de los tokens |
| 3. Analisis semantico | `semantic.py` | Verifica tipos, ambitos y argumentos |
| 4. Ejecucion | `interpreter.py` | Recorre el AST y produce resultados |

Un programa con errores semanticos **no se ejecuta**: la fase 4 se cancela.

---

## Instalacion

```bash
pip install ply
```

---

## Uso

```bash
# Ejecutar los ejemplos embebidos
python main.py

# Ejecutar el programa fuente principal
python main.py progfte.txt

# Ejecutar tu propio archivo
python main.py ejemplo.txt

# Ver los tokens que genera el lexer
python main.py --tokens

# Ver el AST generado
python main.py --ast

# Omitir el analisis semantico
python main.py --no-sem

# Ocultar la tabla de simbolos
python main.py --no-sym

# Combinar flags
python main.py ejemplo.txt --tokens --ast
```

---

## Archivos que genera cada ejecucion

| Archivo | Contenido |
|---|---|
| `progfte.tok` | Lista de tokens, incluidos los de error lexico |
| `progfte.dep` | Codigo fuente depurado (sin comentarios ni espacios) |
| `progfte.tab` | Tabla de tokens con su referencia numerica |
| `progfte.sem` | Reporte del analisis semantico con linea y columna |
| `progfte.sim` | Tabla de simbolos: tipo, ambito, posicion y valor |

---

## Sintaxis del lenguaje

### Tipos de datos
```
entero   numero = 42;
cadena   texto  = "hola";
logico   activo = verdadero;
```

### Asignacion
```
numero = numero + 1;
```

### Entrada y salida
```
leer(numero);

mostrar(numero + 5);       // acepta entero, cadena o logico
mostrar(activo);
mostrar("Total: " + numero);
```

### Condicional
```
si (numero > 10 y activo) {
    mostrar(numero);
} sino {
    mostrar(0);
}
```

### Bucle
```
entero i = 0;
mientras (i < 10) {
    mostrar(i);
    i = i + 1;
}
```

### Ambitos (alcance de las variables)

Cada bloque `{ }` de un `si`, `sino` o `mientras` abre su propio ambito:

```
entero global = 1;

si (global > 0) {
    entero local = 2;
    mostrar(global);       // OK: un bloque ve las variables de fuera
}

mostrar(local);            // ERROR E-S01: 'local' murio al cerrar el bloque
```

Dos bloques hermanos pueden declarar el mismo nombre sin conflicto, porque
cada uno vive en un ambito distinto.

### Operadores y sus tipos

| Operador | Operandos validos | Resultado |
|---|---|---|
| `+` | entero + entero | entero |
| `+` | cadena + cualquier tipo | cadena (concatenacion) |
| `-` `*` `/` | entero, entero | entero |
| `>` `<` `>=` `<=` | ambos entero, o ambos cadena | logico |
| `==` `!=` | ambos del mismo tipo | logico |
| `y` `o` | logico, logico | logico |
| `no` | logico | logico |
| `-` (unario) | entero | entero |

Combinar un entero con un logico mediante `+` es un **error de tipo**.

### Comentarios
```
// esto es un comentario
```

---

## Codigos de error semantico

| Codigo | Significado |
|---|---|
| `E-S01` | Variable usada sin declarar, o fuera de su ambito |
| `E-S02` | Variable declarada dos veces en el mismo ambito |
| `E-S03` | El valor inicial no es del tipo declarado |
| `E-S04` | El valor asignado no es del tipo de la variable |
| `E-S05` | Operando de tipo incorrecto en una operacion aritmetica |
| `E-S06` | Comparacion entre tipos distintos, o entre logicos con `< >` |
| `E-S07` | Operando no logico en `y`, `o` o `no` |
| `E-S08` | La condicion de `si` no es de tipo logico |
| `E-S09` | La variable de `leer()` no fue declarada |
| `E-S10` | La condicion de `mientras` no es de tipo logico |
| `E-S11` | Division entre cero detectada en una expresion constante |
| `E-S12` | El signo `-` unario se aplico a algo que no es entero |
| `E-S13` | `mostrar()` recibio una expresion sin tipo valido |

---

## PALABRAS RESERVADAS — NO usar como nombres de variable

| Palabra         | Funcion                          |
|-----------------|----------------------------------|
| `entero`        | tipo de dato                     |
| `cadena`        | tipo de dato                     |
| `logico`        | tipo de dato                     |
| `verdadero`     | valor booleano                   |
| `falso`         | valor booleano                   |
| `si`            | condicional                      |
| `sino`          | rama alternativa                 |
| `mientras`      | bucle                            |
| `mostrar`       | salida en pantalla               |
| `leer`          | entrada del usuario              |
| `y`             | operador AND                     |
| `o`             | operador OR                      |
| `no`            | operador NOT                     |

### Error tipico

```
entero y = 20;   <- ERROR: 'y' es operador logico, no puede ser variable
```

### Solucion: usa nombres descriptivos

```
entero eje_y  = 20;   OK
entero val2   = 20;   OK
entero beta   = 20;   OK
```

---

## Errores comunes y sus soluciones

| Error | Causa | Solucion |
|---|---|---|
| `'y' es una palabra reservada` | Usaste `y`, `o` o `no` como nombre de variable | Renombra la variable |
| `E-S01 Variable 'x' no declarada` | Usaste una variable antes de declararla, o fuera de su bloque | Declarala antes de usarla, en el ambito correcto |
| `E-S05 entre 'entero' y 'logico'` | Sumaste un numero con un valor logico | Los operandos de `+` deben ser dos enteros, o incluir una cadena |
| `E-S08 / E-S10 condicion no logica` | Pusiste un numero o una cadena como condicion | Usa una comparacion: `si (x > 0)` |
| `E-S11 Division entre cero` | El divisor es una constante que vale 0 | Cambia el divisor |
| `fin de archivo inesperado` | Falta cerrar una llave `}` o un punto y coma `;` | Revisa que cada `{` tenga su `}` y cada sentencia termine en `;` |

---

## Estructura del proyecto

```
compilador/
├── main.py               <- Punto de entrada y orquestador de las 4 fases
├── lexer.py              <- Analizador lexico  (PLY lex)
├── parser.py             <- Analizador sintactico (PLY yacc)
├── ast_nodes.py          <- Nodos del AST, con linea y columna
├── semantic.py           <- Analizador semantico (tipos, ambitos, pila semantica)
├── interpreter.py        <- Ejecutor del AST
├── symbol_table.py       <- Tabla de simbolos con ambitos anidados
├── pruebas/              <- Casos de prueba (validos y con errores)
├── progfte.txt           <- Programa fuente principal
├── ejemplo.txt           <- Programa de prueba
└── requirements.txt
```
