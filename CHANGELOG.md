# Registro de cambios

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-23

### Agregado

- Paquete `app/` organizado por capas: `routers`, `servicios`, `repositorios`, `modelos`, `integraciones` y `db`.
- Capa de servicio (`app/servicios/pedidos.py`) con las reglas de negocio de pedidos, independiente de HTTP y de SQL.
- CRUD de productos: lectura pública; datos inválidos responden 422 (JSON mal formado, 400) y un nombre con la misma preparación repetido responde 409.
- Inicio de sesión `POST /login` que entrega un JWT (HS256) válido durante 30 minutos; las contraseñas se guardan con bcrypt.
- Roles `admin` y `cliente`: crear, reemplazar y eliminar productos exige `admin` (403 para otros roles, 401 sin token válido).
- Pedidos con dueño tomado del token: el cliente solo ve y elimina los suyos, y un pedido ajeno o inexistente responde 404; `admin` ve todos.
- Precio histórico: cada línea del pedido guarda el precio unitario de compra, y el pedido y sus detalles se crean en una sola transacción con bloqueo de los productos.
- Clasificación de comentarios con Gemini (`POST /pedidos/comentario`) mediante el cliente `app/integraciones/gemini.py`: espera máxima `EXTERNO_TIMEOUT` (5 s por omisión; un valor inválido usa 5), un reintento ante 429/5xx o fallo de conexión, y respuestas 503 (sin clave), 504 (tiempo agotado) y 502 (fallo o respuesta inesperada).
- Front web (`front/index.html`) con CORS limitado a la lista de orígenes de `CORS_ORIGENES`, sin comodín `*`.
- 252 pruebas automáticas con pytest.
- Contrato OpenAPI en `docs/openapi.json` (generado con `scripts/generar_contrato.py`), documentación en `docs/CONTRATO_API.md` y Swagger UI en `/docs`; los errores comparten el formato `{"error", "detalles"}`.
- `compose.yaml` con MySQL 8 publicado solo en `127.0.0.1`, con healthcheck y volumen persistente.

### Pendiente

- Códigos QR, pagos y caja.
- Revocación anticipada de JWT: hoy un token sigue siendo válido hasta que expira.
- Pruebas de concurrencia y de carga.
- Sustituir las contraseñas de desarrollo en `.env` por un gestor de secretos.
