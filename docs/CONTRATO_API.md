# Contrato de la API de productos

El contrato se genera automáticamente desde FastAPI. El archivo
[`openapi.json`](openapi.json) es la versión exportada y verificable del esquema.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI en ejecución: `http://127.0.0.1:8000/openapi.json`
- Regenerar el archivo exportado:

```bash
python scripts/generar_contrato.py
```

## Códigos por operación

| Método y ruta | Éxito | Errores documentados |
| --- | --- | --- |
| `GET /productos` | `200` | `500` |
| `GET /productos/{id}` | `200` | `404`, `422`, `500` |
| `POST /productos` | `201` | `400`, `409`, `422`, `500` |
| `PUT /productos/{id}` | `200` | `400`, `404`, `409`, `422`, `500` |
| `DELETE /productos/{id}` | `204` sin cuerpo | `404`, `422`, `500` |

- `400`: el cuerpo no es JSON válido.
- `404`: el producto solicitado no existe.
- `409`: ya existe un producto con el mismo nombre y preparación.
- `422`: datos o parámetros inválidos.
- `500`: error interno, por ejemplo una falla de conexión con MySQL.

## Formato de error

```json
{
  "error": "Producto no encontrado",
  "detalles": []
}
```

En errores de validación, `detalles` contiene objetos con `campo`, `mensaje` y
`tipo`. Las respuestas de error están declaradas en las cinco operaciones con el
esquema `RespuestaError`, por lo que aparecen también en Swagger UI.
