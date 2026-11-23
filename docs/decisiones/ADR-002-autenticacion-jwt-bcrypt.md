# ADR-002: Autenticación sin estado con JWT HS256 y bcrypt

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Decisores:** Equipo Katea
- **Ámbito:** Login, sesiones, roles y protección de rutas

## Contexto

La API necesita identificar usuarios, distinguir los roles `admin` y `cliente` y
proteger las escrituras de productos y todas las rutas de pedidos. El front es
una página estática que consume la API desde el navegador; por tanto, la sesión
no puede depender de variables de servidor ni de una cookie de sesión tradicional.
El sistema es académico y no requiere revocación inmediata de sesiones ni un
proveedor de identidad externo.

Las contraseñas nunca deben guardarse ni transportarse en claro. El login recibe
JSON con `usuario` y `clave`, y la autorización debe poder verificar tanto la
identidad como el rol sin consultar una tabla de sesiones en cada petición.

## Decisión

Usar **JWT firmados con HS256** para la sesión y **bcrypt** para las contraseñas:

- `POST /login` recibe `usuario` y `clave` como textos JSON y responde
  `access_token` y `token_type: bearer`.
- Las claves se guardan como hashes bcrypt con sal aleatoria y costo 12. Se usa
  la biblioteca `bcrypt` directamente, sin Passlib, y se admiten claves de 8 a 72
  bytes UTF-8 sin truncarlas.
- Los tokens se generan con PyJWT y el algoritmo HS256. Incluyen `sub` (ID del
  usuario como texto), `rol`, `iat` y `exp`; la vigencia es de 30 minutos.
- El token solo lleva identidad y rol. No contiene contraseñas, hashes ni el
  registro completo del usuario. Está firmado, no cifrado.
- `JWT_SECRETO` se obtiene del entorno o de `.env`, debe tener al menos 32 bytes
  aleatorios, no tiene valor predeterminado y debe conservarse entre reinicios.
- `usuario_actual` valida firma, algoritmo, claims obligatorios, identidad y rol.
  `exigir_admin` verifica primero el token (401) y después el rol (403).
- Las rutas de productos usan `exigir_admin` solo para POST, PUT y DELETE. Los
  dos GET son públicos. Todas las rutas de pedidos usan `usuario_actual`.
- No hay refresh tokens, revocación anticipada ni edición de usuarios en esta
  etapa. Un cambio de rol se refleja al emitir un token nuevo.

## Alternativas consideradas

### Sesiones de servidor con cookies

Permiten revocar sesiones de inmediato y no exponen un token al JavaScript del
front, pero requieren almacenamiento de sesiones, configuración de cookies,
protección CSRF y un modelo de despliegue más complejo. Tampoco encajan tan bien
con clientes que ya usan `Authorization: Bearer`.

### Tokens opacos guardados en la base

Permiten revocación y rotación con una consulta por petición, pero convierten la
autenticación en una sesión con estado y añaden una tabla y limpieza de tokens.
Para el alcance actual, JWT evita esa infraestructura.

### OAuth 2.0 u OpenID Connect

Sería la opción para delegar identidad a un proveedor externo, con un costo y una
complejidad innecesarios para un login local de tres cuentas de desarrollo.

### Argon2id en lugar de bcrypt

Argon2id es una alternativa moderna y resistente a memoria, pero bcrypt con costo
12 es suficiente para el proyecto, ya estaba disponible y su uso directo evita
otra dependencia y otra configuración.

## Consecuencias

### Positivas

- La API es sin estado: no hay tabla de sesiones ni consulta adicional por cada
  petición protegida.
- El front solo necesita guardar y enviar el token en la cabecera
  `Authorization: Bearer <token>`.
- La separación entre autenticación (401) y autorización por rol (403) es
  explícita y aparece en OpenAPI.
- Los hashes bcrypt no permiten recuperar la clave original y el login no
  distingue entre usuario inexistente y clave incorrecta.

### Negativas y riesgos

- No hay revocación anticipada: un token robado sigue siendo válido hasta su
  vencimiento, y un cambio de rol no afecta a tokens ya emitidos.
- Rotar `JWT_SECRETO` invalida todos los tokens emitidos; debe hacerse de forma
  coordinada y conservando el secreto entre reinicios.
- Si falta `JWT_SECRETO`, el login y las rutas protegidas fallan con un 500
  genérico; no se genera un secreto automático al arrancar.
- El token está firmado pero no cifrado: no debe incluir información sensible.
- No hay refresh token ni cierre de sesión del lado del servidor.

## Referencias

- [autenticacion.py](../../autenticacion.py): login, bcrypt, JWT y dependencias.
- [usuarios.py](../../usuarios.py): tabla de usuarios, roles y hashes.
- [main.py](../../main.py): `POST /login` y protección de productos.
- [rutas_pedidos.py](../../rutas_pedidos.py): rutas de pedidos autenticadas.
- [AUTENTICACION.md](../AUTENTICACION.md): flujo y configuración sensible.
- [errores.md](../errores.md): catálogo de respuestas 401 y 403.
