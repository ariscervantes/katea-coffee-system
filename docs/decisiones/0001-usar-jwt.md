# ADR 0001: Usar JWT para la autenticación

- **Fecha:** 2026-11-23
- **Estado:** Aceptada

## Contexto

HTTP no recuerda nada entre peticiones: cada petición llega sola y la API tiene que saber en
cada una quién la hace y con qué rol (`admin` o `cliente`), para decidir si puede escribir
productos o ver un pedido. Hay dos formas habituales de hacerlo:

1. **Sesiones en el servidor:** se guarda la sesión (en memoria o en una tabla) y el cliente
   envía un identificador que la API busca en cada petición.
2. **Token firmado:** al iniciar sesión, la API entrega un token con la identidad y el rol,
   firmado con un secreto. En cada petición basta con verificar la firma, sin guardar nada.

## Decisión

Usar un token firmado (JWT con PyJWT), implementado en `app/seguridad.py`:

- **Algoritmo HS256** (`ALGORITMO`). Al verificar solo se acepta ese algoritmo
  (`algorithms=[ALGORITMO]`).
- **Vencimiento de 30 minutos** (`DURACION = timedelta(minutes=30)`). El token lleva `sub`
  (id del usuario), `rol`, `iat` y `exp`, y se rechaza si falta alguno.
- **El secreto está en `JWT_SECRETO`, con mínimo 32 bytes y sin valor por omisión**
  (`secreto_desde_entorno`). Si falta, mide menos de 32 bytes en UTF-8 o empieza con
  `REEMPLAZAR` (el marcador de `.env.example`), se lanza `RuntimeError` en lugar de firmar con
  un valor inseguro.
- **Contraseñas con bcrypt, costo 12** (`bcrypt.gensalt(rounds=12)` en `proteger_clave`). Solo
  se guarda el hash. Cuando el usuario no existe, la clave se compara con un hash ficticio para
  que el tiempo de respuesta no revele qué usuarios existen.
- El cliente envía el token en `Authorization: Bearer`. Si falta o no es válido, la API
  responde 401. Si el rol no alcanza para la operación, responde 403.

## Consecuencias

- **No hay sesiones en el servidor.** La API no guarda estado de sesión y cualquier proceso
  que conozca `JWT_SECRETO` puede verificar el token.
- **Cualquiera que tenga el token puede leer su contenido.** La firma impide modificarlo, pero
  no lo cifra: `sub`, `rol`, `iat` y `exp` se leen decodificando Base64. Por eso el token no
  lleva claves ni datos sensibles.
- **Un token robado sirve hasta que vence.** Quien lo obtenga actúa como ese usuario durante
  los 30 minutos de vigencia.
- **No hay revocación anticipada ni cambio de rol inmediato.** Cerrar sesión, borrar al
  usuario o cambiarle el rol no invalida los tokens ya emitidos. El cambio solo se nota cuando
  se emite un token nuevo, es decir, con el siguiente login.
- **Si `JWT_SECRETO` está mal configurado, el error aparece tarde.** El secreto se valida al
  firmar o verificar un token, no al arrancar la API. Si está mal, el primer login o la primera
  petición que trae un token responde 500, aunque la API haya arrancado sin problemas.
- **Cambiar `JWT_SECRETO` invalida todos los tokens** vigentes a la vez.
