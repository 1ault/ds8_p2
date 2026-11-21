# Convenciones del proyecto

## Obligatorio

- **Argumentos con nombre**: toda llamada a una función o constructor usa
  `param=valor` siempre que la firma lo permita. No se aceptan llamadas
  posicionales cuando el nombre aclara el significado.
- **Docstrings** en español con `Args`, `Returns` y `Raises` en las funciones
  públicas.
- **Constantes** en `UPPER_CASE` con `const()` para literales que no cambian
  (pines, tiempos, umbrales, cadenas). Los tópicos derivados se arman por
  concatenación y no llevan `const()`.
- **Sin números mágicos**: pines y umbrales viven en `firmware/config.py`.
- **PEP 8**: 4 espacios, máximo 100 columnas, dos líneas en blanco entre
  funciones de nivel superior, nombres en `snake_case`.
- **`__name__` es un dunder**: el bloque `if __name__ == "__main__":` es el
  punto de entrada del programa.
- **No subir** `.env`, `data/*.db`, `*.bin`, ZIPs ni credenciales.
- **Antes de cada commit**:

```bat
python -m pytest
python scripts\verificar_diagrama.py firmware\diagram.json
```

## Estructura

```text
firmware/   nodo ESP32 + MicroPython + diagram.json
backend/    servidor aiohttp, MQTT, SQLite, panel y ThingSpeak
sql/        schema.sql, seed.sql, consultas.sql
tests/      324 pruebas
scripts/    demo, empaquetado, verificación y generación de documentos
docs/       arquitectura, instalación, capturas, diagramas y manuales
```
