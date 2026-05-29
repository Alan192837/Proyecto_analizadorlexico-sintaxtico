# Mini-Interprete — Calculadora Extendida con PLY
## Sintaxis completamente en Espanol

---

## Instalacion

```bash
pip install ply
```

---

## Uso

```bash
# Ejecutar los 12 ejemplos embebidos
python main.py

# Ejecutar tu propio archivo
python main.py ejemplo.txt

# Ver los tokens que genera el lexer
python main.py --tokens

# Ver el AST generado
python main.py --ast

# Ocultar la tabla de simbolos
python main.py --no-sym

# Combinar flags
python main.py ejemplo.txt --tokens --ast
```

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
mostrar(numero + 5);
```

### Condicional
```
si (numero > 10 y activo) {
    mostrar(numero);
} sino {
    mostrar(0);
}
```

### Operadores

| Tipo         | Operadores                          |
|--------------|-------------------------------------|
| Aritmeticos  | `+`  `-`  `*`  `/`                  |
| Relacionales | `>`  `<`  `>=`  `<=`  `==`  `!=`   |
| Logicos      | `y`  `o`  `no`                      |

### Comentarios
```
// esto es un comentario
```

---

## PALABRAS RESERVADAS — NO usar como nombres de variable

| Palabra      | Funcion                |
|--------------|------------------------|
| `entero`     | tipo de dato           |
| `cadena`     | tipo de dato           |
| `logico`     | tipo de dato           |
| `verdadero`  | valor booleano         |
| `falso`      | valor booleano         |
| `si`         | condicional            |
| `sino`       | rama alternativa       |
| `mostrar`    | salida en pantalla     |
| `leer`       | entrada del usuario    |
| `y`          | operador AND           |
| `o`          | operador OR            |
| `no`         | operador NOT           |

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
| `Variable 'x' no declarada` | Usaste una variable antes de declararla | Agrega `entero x = valor;` antes de usarla |
| `Division entre cero` | El divisor de una division es cero en tiempo de ejecucion | Verifica el valor del divisor |
| `fin de archivo inesperado` | Falta cerrar una llave `}` o un punto y coma `;` | Revisa que cada `{` tenga su `}` y cada sentencia termine en `;` |

---

## Estructura del proyecto

```
milenguaje/
├── main.py          <- Punto de entrada
├── lexer.py         <- Analizador lexico  (PLY lex)
├── parser.py        <- Analizador sintactico (PLY yacc)
├── ast_nodes.py     <- Nodos del AST
├── interpreter.py   <- Ejecutor del AST
├── symbol_table.py  <- Tabla de simbolos
├── ejemplo.txt      <- Programa de prueba
└── requirements.txt
```
