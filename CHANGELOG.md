# Changelog

Todos los cambios relevantes de Katea se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
versionado semántico [SemVer](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-23

Primera versión estable de la API de productos y pedidos de Katea.

### Añadido

- CRUD de productos sobre MySQL 8, con validación estricta de nombre,
  descripción, precio, imagen, disponibilidad y preparación; detección de
  duplicados (409) y protección contra el borrado de productos referenciados por
  pedidos (409).
- Persistencia con PyMySQL: creación automática de las tablas ausentes al
  arrancar, SQL parametrizado con `%s` y transacciones con commit, rollback y
  cierre de conexión.
- Autenticación mediante `POST /login`, contraseñas almacenadas como hashes
  bcrypt (costo 12) y JWT HS256 con identidad, rol y vencimiento de 30 minutos.
- Autorización por rol: la escritura de productos requiere `admin`; la lectura de
  productos es pública. Las rutas de pedidos exigen sesión.
- Pedidos con control de dueño: el cliente solo lista, consulta y elimina los
  propios, mientras que el admin tiene acceso global. Creación transaccional con
  precios históricos, totales `DECIMAL` y estado inicial `pendiente`.
- Endpoint `POST /pedidos/comentario` para clasificar el sentimiento de un
  comentario y generar una respuesta con Gemini, con timeout, un reintento ante
  fallos transitorios y respuestas 502/503/504 según el caso.
- CORS configurable con `CORS_ORIGENES`, restringido a orígenes explícitos y sin
  comodín `*`.
- Front estático de ejemplo en `front/index.html` con login, listado de productos
  y alta con errores por campo.
- Formato uniforme de errores `{"error": "...", "detalles": [...]}` y manejadores
  para JSON mal formado (400), datos inválidos (422) y fallos internos (500).
- Contrato OpenAPI exportado en `docs/openapi.json`, Swagger UI en `/docs`, ReDoc
  en `/redoc` y regeneración con `scripts/generar_contrato.py`.
- Plantilla `.env.example` con todas las variables de entorno y `compose.yaml`
  para un MySQL 8 local publicado en el puerto 13306.
- Script manual `scripts/crear_usuarios_desarrollo.py` para crear `dev_admin`,
  `dev_cliente1` y `dev_cliente2`, habilitado solo con `KATEA_ENTORNO=desarrollo`.
- Suite de pruebas con pytest (230 casos) sobre repositorios aislados y un
  adaptador SQL en memoria, sin depender de un MySQL real.
- Documentación en `docs/` sobre autenticación, pedidos, contrato de la API,
  contexto del proyecto y preparación del equipo.

### Seguridad

- `JWT_SECRETO` es obligatorio, debe tener al menos 32 bytes aleatorios, no tiene
  valor predeterminado y debe conservarse entre reinicios.
- `.env` y las credenciales locales están fuera de Git; `.env.example` solo
  contiene marcadores.
- Las consultas SQL usan parámetros separados y las contraseñas se guardan
  únicamente como hashes bcrypt.
- CORS no permite `*`: solo los orígenes configurados explícitamente.

### Notas

- Requiere MySQL 8 y Python 3.14, la versión comprobada en el proyecto.
- Las variables de entorno y su descripción están en `.env.example` y en el
  [README](README.md#variables-de-entorno).
- QR, pagos, caja, registro público y edición de usuarios quedan fuera de esta
  versión.
