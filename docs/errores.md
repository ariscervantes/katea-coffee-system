# Catálogo de errores de la API

Referencia de los errores que puede devolver la API de Katea. El contrato
ejecutable está en [openapi.json](openapi.json) y la descripción de las rutas en
[CONTRATO_API.md](CONTRATO_API.md).

## Formato uniforme

Todas las respuestas de error usan el mismo objeto JSON:

```json
{
  "error": "Producto no encontrado",
  "detalles": []
}
```

- `error`: mensaje legible para la persona que consume la API.
- `detalles`: lista de errores de validación; queda vacía en los errores que no
  provienen de Pydantic.

En errores de validación, cada elemento de `detalles` tiene esta forma:

```json
{
  "campo": ["body", "precio"],
  "mensaje": "precio debe tener máximo dos decimales",
  "tipo": "value_error"
}
```

`campo` puede incluir índices de listas, por ejemplo
`["body", "productos", 0, "cantidad"]`. Los mensajes de Pydantic pueden variar
entre versiones; para programar un cliente conviene usar `tipo` y `campo`, no el
texto exacto, salvo en los mensajes propios documentados aquí.

## Cómo se construye la respuesta

| Situación | Código | `error` | `detalles` |
| --- | --- | --- | --- |
| El cuerpo no es JSON válido | 400 | `JSON mal formado` | Errores de validación, normalmente con tipo `json_invalid` |
| Datos o parámetros inválidos | 422 | `Datos inválidos` | Lista de errores de Pydantic |
| `HTTPException` controlada por la API | El de la excepción | El texto del `detail` | `[]` |
| Excepción no controlada | 500 | `Error interno del servidor` | `[]` |
| Ruta inexistente | 404 | `Not Found` | `[]` |
| Método no permitido en una ruta | 405 | `Method Not Allowed` | `[]` |

El manejador de errores conserva las cabeceras de las `HTTPException`. En
particular, las respuestas 401 incluyen `WWW-Authenticate: Bearer`. Los errores
500 se registran con traza en el log del servidor, pero el cliente solo recibe el
mensaje genérico.

## Códigos de estado

| Código | Significado en Katea |
| --- | --- |
| 400 | El cuerpo de la petición no es JSON válido. |
| 401 | Credenciales incorrectas, token ausente, inválido o vencido. |
| 403 | El token es válido, pero el rol no permite la operación. |
| 404 | El recurso no existe; en pedidos también cubre un pedido ajeno. |
| 405 | La ruta existe, pero no admite ese método HTTP. |
| 409 | Conflicto: producto duplicado, producto no disponible o producto referenciado por un pedido. |
| 422 | Datos o parámetros inválidos, producto inexistente en el cuerpo de un pedido o importe fuera de rango. |
| 500 | Error interno no controlado o fallo de infraestructura. |
| 502 | La IA externa respondió con error o con un contenido inesperado. |
| 503 | Falta configurar la IA. |
| 504 | La IA externa agotó el tiempo de espera. |

## Matriz por endpoint

Las celdas marcadas con `✓` indican que ese código está documentado para la
operación. No todos los errores aplican a todos los métodos.

| Método y ruta | 400 | 401 | 403 | 404 | 409 | 422 | 500 | 502 | 503 | 504 |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `POST /login` | ✓ | ✓ | — | — | — | ✓ | ✓ | — | — | — |
| `GET /productos` | — | — | — | — | — | — | ✓ | — | — | — |
| `GET /productos/{id}` | — | — | — | ✓ | — | ✓ | ✓ | — | — | — |
| `POST /productos` | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — | — |
| `PUT /productos/{id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| `DELETE /productos/{id}` | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| `GET /pedidos` | — | ✓ | — | — | — | — | ✓ | — | — | — |
| `GET /pedidos/{id}` | — | ✓ | — | ✓ | — | ✓ | ✓ | — | — | — |
| `POST /pedidos` | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | — | — |
| `DELETE /pedidos/{id}` | — | ✓ | — | ✓ | — | ✓ | ✓ | — | — | — |
| `POST /pedidos/comentario` | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ | ✓ | ✓ |

## Mensajes por código

### 400 — JSON mal formado

| Mensaje | Cuándo |
| --- | --- |
| `JSON mal formado` | El cuerpo de la petición no se puede interpretar como JSON. Aplica a `POST /login`, `POST /productos`, `PUT /productos/{id}`, `POST /pedidos` y `POST /pedidos/comentario`. |

### 401 — No autenticado

Todas las respuestas 401 incluyen `WWW-Authenticate: Bearer`.

| Mensaje | Cuándo |
| --- | --- |
| `Usuario o clave incorrectos` | `POST /login` con un usuario inexistente o una clave incorrecta. Es el mismo mensaje en ambos casos para no revelar qué usuarios existen. |
| `Falta un token Bearer válido` | Una ruta protegida recibe la petición sin un token Bearer utilizable. |
| `El token no es válido o ya expiró` | Firma incorrecta, algoritmo no permitido, token vencido, claims obligatorios ausentes (`sub`, `rol`, `iat`, `exp`) o identidad/rol inválidos. |

### 403 — Sin permiso por rol

| Mensaje | Cuándo |
| --- | --- |
| `Tu rol no puede hacer esto` | Un usuario con rol `cliente` intenta `POST`, `PUT` o `DELETE` sobre productos. |

El orden es primero autenticación y después autorización: sin token se devuelve
401; con token de cliente se devuelve 403.

### 404 — No encontrado

| Mensaje | Cuándo |
| --- | --- |
| `Producto no encontrado` | `GET`, `PUT` o `DELETE` de un producto cuyo ID no existe. |
| `Pedido no encontrado` | `GET` o `DELETE` de un pedido inexistente o ajeno. Se usa el mismo mensaje y código para no revelar la existencia de pedidos de otros usuarios. |
| `Not Found` | La ruta solicitada no existe; lo genera el enrutador de FastAPI/Starlette. |

### 409 — Conflicto

| Mensaje | Cuándo |
| --- | --- |
| `Ya existe un producto con ese nombre y preparación` | `POST /productos` o `PUT /productos/{id}` con un nombre normalizado (`strip` y `casefold`) y una preparación ya registrados. En `PUT` se excluye el propio producto. |
| `El producto está asociado a un pedido` | `DELETE /productos/{id}` cuando un detalle de pedido referencia el producto y la clave foránea `RESTRICT` impide borrarlo. |
| `Producto no disponible` | `POST /pedidos` incluye un producto existente marcado como no disponible. |

### 422 — Datos inválidos

El error general es `Datos inválidos` y sus causas concretas aparecen en
`detalles`. Además, los pedidos pueden devolver estos mensajes propios:

| Mensaje | Cuándo |
| --- | --- |
| `Producto no encontrado` | El cuerpo de `POST /pedidos` referencia un `producto_id` que no existe. El código es 422 porque el problema está en el cuerpo, aunque el texto coincida con el 404 de productos. |
| `El total supera el importe máximo de un pedido` | La suma de cantidad por precio unitario excede `DECIMAL(65, 2)`. |

### 500 — Error interno

| Mensaje | Cuándo |
| --- | --- |
| `Error interno del servidor` | Excepción no controlada, fallo de conexión o consulta a MySQL, o falta de `JWT_SECRETO` al intentar emitir o verificar un token. |

El cliente no recibe la traza, el SQL ni detalles de la conexión. Esos datos
quedan únicamente en el log del servidor.

### 502 — Error de la IA externa

| Mensaje | Cuándo |
| --- | --- |
| `La IA no está disponible (respondió {código}). Intenta más tarde.` | Gemini respondió un error HTTP que no se reintenta o que persistió tras el reintento. |
| `No se pudo conectar con la IA.` | Fallo de red al contactar el servicio externo después del reintento. |
| `La IA respondió algo que no entendemos.` | La respuesta externa no es JSON o no tiene la estructura esperada. |
| `La IA respondió algo inesperado.` | El JSON externo no contiene un `sentimiento` válido o una `respuesta` no vacía. |

La API reintenta una vez los errores transitorios (429 y 5xx). No reintenta un
400, una respuesta inválida ni un timeout. El tiempo máximo por intento es de 5
segundos.

### 503 — IA sin configurar

| Mensaje | Cuándo |
| --- | --- |
| `Falta configurar la variable de entorno GEMINI_API_KEY` | `POST /pedidos/comentario` usa Gemini y no existe la clave. No aplica cuando `EXTERNO_URL` apunta al simulador local. |

### 504 — Tiempo de espera de la IA

| Mensaje | Cuándo |
| --- | --- |
| `La IA tardó demasiado en responder. Intenta en un momento.` | Se agotó el timeout de la llamada a la IA. |

## Validaciones de productos

`ProductoEntrada` prohíbe campos adicionales, incluido `id`. Todos los campos son
obligatorios.

| Campo | Regla | Mensajes propios |
| --- | --- | --- |
| `nombre` | Texto de 2 a 80 caracteres después de recortar extremos. | Los de Pydantic para longitud o tipo. |
| `descripcion` | Texto de 5 a 200 caracteres después de recortar extremos. | Los de Pydantic para longitud o tipo. |
| `precio` | Número JSON finito y mayor que cero, con máximo dos decimales. No acepta textos, booleanos ni notación que exceda dos decimales. | `precio debe ser un número, sin comillas`; `precio debe ser un número válido`; `precio debe ser finito y mayor que cero`; `precio debe tener máximo dos decimales`. |
| `imagen_url` | Texto no vacío, sin CR/LF, terminado en `.jpg`, `.jpeg`, `.png` o `.webp`, con un nombre antes de la extensión. No se descarga la imagen. | `imagen_url no debe contener saltos de línea`; `imagen_url debe terminar en .jpg, .jpeg, .png o .webp`; `imagen_url debe tener un nombre antes de la extensión`. |
| `disponible` | Booleano estricto; no acepta `"true"` ni `1`. | Los de Pydantic. |
| `preparacion` | Uno de `frio`, `caliente` o `no_aplica`. | Los de Pydantic. |
| Campos extra | Rechazados. | `extra_forbidden` en `detalles`. |

La combinación de nombre normalizado y preparación debe ser única. El conflicto
se informa como 409, no como error de validación.

## Validaciones de pedidos y comentarios

`PedidoEntrada` prohíbe campos adicionales, incluidos `usuario_id`, precios,
total y estado. El dueño se obtiene del token.

| Campo | Regla | Mensajes propios |
| --- | --- | --- |
| `productos` | Lista no vacía. | Los de Pydantic para lista vacía o tipo incorrecto. |
| `productos[].producto_id` | Entero estricto mayor que cero y menor o igual a 4294967295. No acepta textos ni decimales. | Los de Pydantic. |
| `productos[].cantidad` | Entero estricto mayor que cero y menor o igual a 4294967295. | Los de Pydantic. |
| Repetición de productos | Cada `producto_id` puede aparecer una sola vez. | `Cada producto debe aparecer una sola vez; usa cantidad` en `detalles`. |
| Campos extra | Rechazados. | `extra_forbidden` en `detalles`. |

`EntradaPedidosComentario` solo acepta `comentario`:

| Campo | Regla | Mensajes propios |
| --- | --- | --- |
| `comentario` | Texto de 2 a 300 caracteres después de recortar extremos. | Los de Pydantic para longitud o tipo. |
| Campos extra | Rechazados; la identidad no se acepta desde el cuerpo. | `extra_forbidden` en `detalles`. |

En las rutas con `{id}`, un valor que no sea un entero produce 422 antes de
consultar la base. Un entero inexistente produce 404. En el cuerpo de un pedido,
un `producto_id` inexistente produce 422.

## Ejemplos

Producto inexistente:

```json
{
  "error": "Producto no encontrado",
  "detalles": []
}
```

Producto duplicado:

```json
{
  "error": "Ya existe un producto con ese nombre y preparación",
  "detalles": []
}
```

Error de validación:

```json
{
  "error": "Datos inválidos",
  "detalles": [
    {
      "campo": ["body", "precio"],
      "mensaje": "precio debe tener máximo dos decimales",
      "tipo": "value_error"
    }
  ]
}
```

Comentario sin IA configurada:

```json
{
  "error": "Falta configurar la variable de entorno GEMINI_API_KEY",
  "detalles": []
}
```

## Notas de seguridad

- Un usuario inexistente y una clave incorrecta producen el mismo 401 en el
  login; un pedido ajeno y uno inexistente producen el mismo 404.
- Los mensajes 500 no exponen excepciones, SQL, credenciales ni rutas internas.
- Las respuestas de error nunca incluyen contraseñas, hashes ni tokens.
- El detalle de autenticación y autorización está en
  [ADR-002](decisiones/ADR-002-autenticacion-jwt-bcrypt.md).
