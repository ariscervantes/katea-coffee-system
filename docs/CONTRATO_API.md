# Contrato de la API de Katea

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
| `POST /productos` | `201` | `400`, `401`, `403`, `409`, `422`, `500` |
| `PUT /productos/{id}` | `200` | `400`, `401`, `403`, `404`, `409`, `422`, `500` |
| `DELETE /productos/{id}` | `204` sin cuerpo | `401`, `403`, `404`, `409`, `422`, `500` |

- `400`: el cuerpo no es JSON válido.
- `401`: falta token Bearer válido o está vencido; incluye `WWW-Authenticate: Bearer`.
- `403`: token válido cuyo rol no es admin.
- `404`: el producto solicitado no existe.
- `409`: producto duplicado; al borrar, producto referenciado por un pedido.
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

## Autenticación y autorización (U3S4, etapas 1 y 2)

`POST /login` recibe `usuario` y `clave` como textos JSON. Responde 200 con
`access_token` y `token_type: bearer`; errores 400/401/422/500 con `RespuestaError`.
El 401 tiene el mismo mensaje para usuario desconocido o clave incorrecta.
Los tokens llevan identidad, rol y vencimiento de 30 minutos.

`exigir_admin` depende de `usuario_actual`: verifica primero el JWT y después
el rol. POST, PUT y DELETE de productos usan esta dependencia; los dos GET
siguen públicos. El contrato muestra BearerJWT y Authorize en Swagger, y
documenta 401/403 para las escrituras. `/login` permanece público.
Ver [AUTENTICACION.md](AUTENTICACION.md) para configuración y cuentas de prueba.

## Pedidos (U3S4, etapa 3)

| Método y ruta | Éxito | Errores documentados |
| --- | --- | --- |
| `GET /pedidos` | 200, lista | 401, 500 |
| `GET /pedidos/{id}` | 200 | 401, 404, 422, 500 |
| `POST /pedidos` | 201, pedido con ID | 400, 401, 409, 422, 500 |
| `POST /pedidos/comentario` | 200, sentimiento y respuesta | 400, 401, 422, 502, 503, 504, 500 |
| `DELETE /pedidos/{id}` | 204 sin cuerpo | 401, 404, 422, 500 |

Todas requieren BearerJWT. Cliente lista/consulta/elimina solo propios; admin
tiene acceso global. Un pedido ajeno o inexistente da el mismo 404. El 401
conserva WWW-Authenticate Bearer y todos los errores usan RespuestaError.

PedidoEntrada exige `productos`, lista no vacía de `{producto_id, cantidad}`,
ambos enteros estrictos positivos con máximo 4294967295. No admite productos
repetidos ni campos adicionales (incluidos dueño, precios, total o estado).
Lista vacía y datos inválidos dan 422; producto inexistente, 422; no disponible,
409. El total fuera de DECIMAL(65,2) da 422. JSON mal formado da 400.

Pedido devuelve id, usuario_id, estado pendiente, total y productos con cantidad
y precio_unitario histórico. Total y precio_unitario se anuncian como textos
decimales con dos posiciones. Ver [PEDIDOS.md](PEDIDOS.md) para transacción,
restricciones de borrado y preparación de los datos del script U3S4.

`POST /pedidos/comentario` también exige BearerJWT. Recibe únicamente
`{"comentario": "..."}` con 2–300 caracteres; rechaza campos extra. El nombre, ID
y rol del usuario se obtienen del token y del repositorio, nunca del cuerpo, y se
incluyen en el contexto de la IA. Responde `sentimiento` (positivo, neutral o
negativo) y `respuesta` (máximo 200 caracteres). Una respuesta inválida de la IA
da 502; la falta de configuración, 503; el timeout, 504.
