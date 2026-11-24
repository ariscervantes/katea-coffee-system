# Errores de la API

## Formato único

Todas las respuestas de error tienen la misma forma, sin importar el código:

```json
{
  "error": "Mensaje para la persona que usa la API",
  "detalles": []
}
```

- `error`: texto corto que explica qué pasó.
- `detalles`: lista. Va vacía salvo en 400 y 422 por validación, donde cada elemento indica
  el campo que falló:

```json
{
  "error": "Datos inválidos",
  "detalles": [
    {"campo": ["body", "clave"], "mensaje": "Field required", "tipo": "missing"}
  ]
}
```

El formato lo garantizan los tres manejadores de `app/errores.py`:

| Manejador | Captura | Resultado |
|---|---|---|
| `error_validacion` | `RequestValidationError` (Pydantic) | 400 si el JSON no se puede leer, 422 en otro caso, con `detalles` |
| `error_http` | `HTTPException` (las que lanza el código y las de Starlette) | El código de la excepción, `detalles: []` y sus encabezados |
| `error_interno` | Cualquier otra excepción | 500 con un mensaje genérico; el detalle solo va al log |

Los 401 incluyen además el encabezado `WWW-Authenticate: Bearer`.

## Códigos

| Código | Cuándo | Ejemplo de mensaje |
|---|---|---|
| 400 | El cuerpo no es JSON válido, por ejemplo si le falta una llave o una coma (`app/errores.py`, `error_validacion`) | `JSON mal formado` |
| 401 | La ruta exige sesión y no llegó el encabezado `Authorization: Bearer` (`app/seguridad.py`, `usuario_actual`) | `Falta un token Bearer válido` |
| 401 | El token está alterado, vencido, firmado con otro secreto o le falta `sub`, `rol`, `iat` o `exp` (`app/seguridad.py`, `no_autorizado`) | `El token no es válido o ya expiró` |
| 401 | `POST /login` con un usuario que no existe o una clave incorrecta; las dos respuestas son iguales (`app/seguridad.py`, `iniciar_sesion`) | `Usuario o clave incorrectos` |
| 403 | Un `cliente` intenta `POST`, `PUT` o `DELETE` en `/productos` (`app/seguridad.py`, `exigir_admin`) | `Tu rol no puede hacer esto` |
| 404 | `GET`, `PUT` o `DELETE /productos/{id}` con un id que no existe (`app/routers/productos.py`, `MENSAJE_NO_ENCONTRADO`) | `Producto no encontrado` |
| 404 | `GET` o `DELETE /pedidos/{id}` de un pedido que no existe o que es de otro cliente; las dos respuestas son iguales (`app/routers/pedidos.py`) | `Pedido no encontrado` |
| 409 | Crear o reemplazar un producto con el mismo nombre y preparación que otro (`app/routers/productos.py`, `MENSAJE_DUPLICADO`) | `Ya existe un producto con ese nombre y preparación` |
| 409 | Borrar un producto que ya aparece en algún pedido (`app/routers/productos.py`, `eliminar_producto`) | `El producto está asociado a un pedido` |
| 409 | Crear un pedido con un producto marcado como no disponible (`app/routers/pedidos.py`, `crear`) | `Producto no disponible` |
| 422 | El JSON se pudo leer, pero un campo falta, sobra, tiene otro tipo o está fuera de rango; también un id de ruta que no es entero (`app/errores.py`, `error_validacion`) | `Datos inválidos` |
| 422 | Crear un pedido con un `producto_id` que no existe en el catálogo (`app/routers/pedidos.py`, `crear`) | `Producto no encontrado` |
| 422 | El total del pedido supera `MAX_IMPORTE`, lo máximo que cabe en `DECIMAL(65, 2)` (`app/routers/pedidos.py`, `crear`) | `El total supera el importe máximo de un pedido` |
| 500 | Una excepción no prevista, por ejemplo si se cae MySQL; la traza se registra en el log y no se envía al cliente (`app/errores.py`, `error_interno`) | `Error interno del servidor` |
| 502 | Gemini respondió con un código de error y no se reintenta, o volvió a fallar después del reintento (`app/integraciones/gemini.py`) | `La IA no está disponible (respondió 503). Intenta más tarde.` |
| 502 | No se pudo conectar con Gemini, ni al primer intento ni al reintento (`app/integraciones/gemini.py`) | `No se pudo conectar con la IA.` |
| 502 | Gemini respondió algo que no es el JSON esperado (`app/integraciones/gemini.py`) | `La IA respondió algo que no entendemos.` |
| 502 | El JSON de Gemini no trae un `sentimiento` válido o una `respuesta` con texto (`app/routers/pedidos.py`, con `validar_respuesta_ia` de `app/servicios/pedidos.py`) | `La IA respondió algo inesperado.` |
| 503 | Falta `GEMINI_API_KEY` y la URL apunta a Gemini; no se hace ninguna llamada (`app/integraciones/gemini.py`) | `Falta configurar la variable de entorno GEMINI_API_KEY` |
| 504 | Gemini no respondió dentro de `EXTERNO_TIMEOUT` (5 s por omisión) (`app/integraciones/gemini.py`) | `La IA tardó demasiado en responder. Intenta en un momento.` |

Notas:

- En los 422 de validación, `detalles[].mensaje` es el texto de Pydantic. Las reglas propias
  aparecen con el prefijo `Value error, `; por ejemplo:
  `Value error, precio debe ser un número, sin comillas` o
  `Value error, Cada producto debe aparecer una sola vez; usa cantidad`.
- En el 502 de Gemini, el número entre paréntesis es el código que devolvió Gemini.
- `app/integraciones/gemini.py` termina con `La IA no está disponible. Intenta más tarde.`
  como red de seguridad. Con la lógica actual no se alcanza, porque el segundo intento siempre
  regresa o lanza otra excepción antes.
- Las excepciones propias de Starlette también usan este formato. Una ruta inexistente da 404
  `Not Found` y un método no permitido da 405 `Method Not Allowed`.
- Pruebas automáticas que cubren los códigos que no se pueden provocar con curl sin
  credenciales ni Gemini:
  403 en `tests/test_permisos_productos.py`;
  409 en `tests/test_regresiones_productos.py` y `tests/test_pedidos.py`;
  500 en `tests/test_pedidos.py`;
  502, 503 y 504 en `tests/test_ia.py` y `tests/test_comentario.py`.

## Comprobación con curl

Con la API en marcha (`python -m uvicorn app.main:app`) y `BASE=http://127.0.0.1:8000`:

```console
$ curl -s -X POST $BASE/login -H 'Content-Type: application/json' -d '{"usuario": "x",'
{"error":"JSON mal formado","detalles":[{"campo":["body",16],"mensaje":"JSON decode error","tipo":"json_invalid"}]}
# HTTP 400

$ curl -s -X POST $BASE/login -H 'Content-Type: application/json' -d '{"usuario":"x"}'
{"error":"Datos inválidos","detalles":[{"campo":["body","clave"],"mensaje":"Field required","tipo":"missing"}]}
# HTTP 422

$ curl -s $BASE/pedidos
{"error":"Falta un token Bearer válido","detalles":[]}
# HTTP 401

$ curl -s $BASE/pedidos -H 'Authorization: Bearer abc.def.ghi'
{"error":"El token no es válido o ya expiró","detalles":[]}
# HTTP 401

$ curl -s $BASE/productos/999999
{"error":"Producto no encontrado","detalles":[]}
# HTTP 404
```

Para ver el código HTTP, agrega `-w '\n%{http_code}\n'` al comando.
