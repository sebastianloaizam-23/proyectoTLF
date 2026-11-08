# UAV-LANG – Analizador (Fase 3)

Analizador léxico, sintáctico y semántico para perfiles de configuración de drones FPV.
Solo usa la biblioteca estándar de Python (3.8+).

## Uso

```
python main.py ejemplos/01_valido_basico.uav            # árbol de derivación o lista de errores
python main.py ejemplos/01_valido_basico.uav --tokens   # además lista los tokens
python main.py ejemplos/01_valido_basico.uav --derivacion   # reglas (1)..(18) aplicadas
python main.py --teoria                                  # AFD, PRIMERO/SIGUIENTE, tabla LL(1)
python pruebas.py                                        # pruebas automáticas
```

Código de salida: 0 válido, 1 con errores, 2 archivo no encontrado.

## Arquitectura (cada módulo corresponde a una sección del documento)

| Módulo | Contenido | Documento |
|---|---|---|
| `tokens.py` | Tokens, diccionario de palabras reservadas, `Token`, `Error` | Fase 1, secs. 2 y 4.5 |
| `lexico.py` | Los 4 AFD con sus matrices de transición y el escáner | Fase 1, secs. 3 y 4 |
| `gramatica.py` | Reglas (1)–(18) como datos; calcula PRIMERO, SIGUIENTE y tabla LL(1) | Fase 2, secs. 7–9 |
| `sintactico.py` | Parser descendente recursivo, una función por no terminal | Fase 2, sec. 9 |
| `semantico.py` | RF04, RF05, RF06 (positivos) y RF12; tabla de símbolos | Fase 2, sec. 10 |
| `main.py` | Tubería léxico → sintáctico → semántico y línea de comandos | – |
| `pruebas.py` | AFD vs ER, conjuntos vs documento, 30 casos, prueba de estrés | – |

## Decisiones de diseño

- Las palabras reservadas no tienen autómata propio: se reconoce un identificador y se
  consulta el diccionario con el lexema en mayúsculas (RF11).
- Las líneas en blanco se colapsan en un solo `TK_SALTO_LINEA`; el `\r` se trata como espacio
  (archivos de Windows); si falta el salto final se agrega uno implícito antes de `$`.
- No hay comentarios en el lenguaje: cualquier `#`, `//`, etc. es un error léxico.
- Cada fase solo se ejecuta si la anterior no tuvo errores (evita errores en cascada falsos).
- Recuperación de errores sintácticos en modo pánico por líneas: se descarta la línea errónea
  y se sigue, para reportar varios errores en una sola ejecución.
- `⟨lista_config'⟩` se implementa con un ciclo en vez de recursión para soportar archivos largos.
- Las palabras reservadas compuestas se escriben con espacios (`SEGURIDAD FAILSAFE RETURN`);
  con guion bajo el léxico las lee como un único identificador (y el error lo sugiere).
