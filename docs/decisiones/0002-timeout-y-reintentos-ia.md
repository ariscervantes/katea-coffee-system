# ADR 0002: Timeout y reintentos en la llamada a la IA

- **Fecha:** 2026-11-23
- **Estado:** Aceptada

## Contexto

`POST /pedidos/comentario` clasifica el comentario de un cliente con Gemini, un servicio
externo que puede tardar, saturarse (429), fallar (5xx) o no aceptar conexiones. Mientras la
API espera a Gemini, el cliente también espera. Sin un límite, una petición podría quedarse
colgada indefinidamente. Si nunca se reintenta, un fallo pasajero llega al cliente como error;
si se reintenta todo, se alargan las esperas y se repiten peticiones que van a fallar igual.

## Decisión

En `app/integraciones/gemini.py`:

- **Timeout de 5 s por intento.** Se lee de `EXTERNO_TIMEOUT`. Si falta, no es número o no es
  positivo, se usan 5 s (`TIMEOUT_POR_OMISION`, función `_timeout_desde_entorno`).
- **Como máximo 2 intentos** (`for intento in range(2)`): el original y un reintento.
- **Solo se reintenta ante:**
  - un 429 o un 5xx de Gemini (`_fallo_transitorio`);
  - un fallo de conexión (`URLError` cuya causa no es un timeout).
- **No se reintenta ante:**
  - un timeout: responde 504 de inmediato;
  - un 400 u otro 4xx distinto de 429: responde 502;
  - una respuesta que no es el JSON esperado: responde 502.
- Si el reintento también falla, responde 502. Si falta `GEMINI_API_KEY` y la URL es la de
  Gemini, responde 503 sin hacer ninguna llamada.
- El reintento es inmediato, sin pausa entre intentos.

## Consecuencias

- **Peor caso de espera: unos 10 s.** Un primer intento contesta 5xx justo antes de los 5 s y
  el reintento agota sus 5 s, lo que da 504. Es un límite nominal, no garantizado: el timeout
  de `urllib` limita cada operación de red (conectar, cada lectura) y no la duración total, y
  no cubre la resolución DNS.
- **Si Gemini está caído, el comentario queda sin clasificar.** El cliente recibe 502, 503 o
  504 y tiene que reenviarlo: la ruta no guarda el comentario ni da una clasificación de
  respaldo.
- **No reintentar los timeouts deja un costo.** Una lentitud de un solo momento llega al
  cliente como 504 aunque un segundo intento habría funcionado. A cambio, la espera ante un
  timeout no pasa de 5 s, en lugar de 10 s.
- **El reintento inmediato rara vez resuelve un 429.** El código no espera ni lee
  `Retry-After`, así que un límite de cuota normalmente vuelve a fallar. Además, cada
  reintento es una petición más contra la cuota de la clave.
- **Reintentar es seguro aquí.** `generateContent` solo genera texto: no cambia nada en Gemini
  ni en nuestra base de datos, y la ruta no escribe nada antes ni después de la llamada.
  Repetirla no puede duplicar un pedido ni ningún otro dato. Como se usa `temperature: 0`, las
  dos respuestas deberían ser equivalentes.
- **Comprobación:** `tests/test_ia.py` prueba un reintento tras un 503, que no hay reintento
  ante un 400 ni ante un timeout, 502 tras dos fallos, el mismo timeout en cada intento y el
  valor de 5 s cuando `EXTERNO_TIMEOUT` falta o es inválido.
