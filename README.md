# Katea · API de menú digital y pedidos

API para una cafetería que publica su menú digital y recibe pedidos en línea. Cualquier persona puede consultar el menú; los clientes inician sesión para hacer y revisar **sus propios** pedidos y dejar comentarios que una IA (Gemini) clasifica por sentimiento. El administrador mantiene el catálogo de productos y puede ver todos los pedidos.

- **Versión:** v1.0.0 (ver [CHANGELOG.md](CHANGELOG.md))
- **Lenguaje:** Python · FastAPI, con MySQL 8
- **Arquitectura:** [docs/arquitectura.md](docs/arquitectura.md)
- **Decisiones de diseño:** [docs/decisiones/](docs/decisiones/)

## Cómo correrla

Requisitos: Python 3, Git y Docker (para MySQL). Todos los comandos se ejecutan **desde la raíz del repositorio**. Donde cambian, se muestra primero Windows (cmd) y luego bash (Linux/macOS).

1. Clonar el repositorio:
   ```
   git clone https://github.com/ariscervantes/katea-coffee-system.git
   cd katea-coffee-system
   ```

2. Crear un entorno virtual e instalar dependencias:
   ```
   :: Windows (cmd)
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```
   ```bash
   # bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

3. Configurar las variables de entorno. Copia la plantilla y reemplaza en `.env` cada valor `REEMPLAZAR_...` por uno propio (ver la [tabla de variables](#variables-de-entorno)):
   ```
   :: Windows (cmd)
   copy .env.example .env
   ```
   ```bash
   # bash
   cp .env.example .env
   ```
   Para `JWT_SECRETO` puedes generar un valor aleatorio con `python -c "import secrets; print(secrets.token_urlsafe(48))"` y pegarlo en `.env`. La API lee `.env` al arrancar; una variable definida en la terminal tiene prioridad sobre el archivo.

4. Levantar MySQL y crear los usuarios de desarrollo:
   ```
   docker compose up -d --wait mysql
   python scripts/crear_usuarios_desarrollo.py
   ```
   El script solo funciona con `KATEA_ENTORNO=desarrollo` (ya viene así en `.env.example`). Pide, sin mostrarlas en pantalla, las claves de tres cuentas: `dev_admin` (rol admin), `dev_cliente1` y `dev_cliente2` (rol cliente). No hay usuarios ni claves predeterminados. Las tablas se crean solas la primera vez que arranca la API.

5. Arrancar la API:
   ```
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

6. Abrir el contrato en http://127.0.0.1:8000/docs. Para el front, en **otra** terminal:
   ```
   cd front
   python -m http.server 5500 --bind 127.0.0.1
   ```
   y abrir http://127.0.0.1:5500. No abras `front/index.html` con doble clic: el navegador lo trataría como origen `null` y la API lo rechaza por CORS.

## Variables de entorno

Están todas en [.env.example](.env.example), con valores de ejemplo. **Ninguna clave real va en el repositorio**: `.env` está en `.gitignore`.

| Variable | Para qué sirve | Obligatoria |
|---|---|---|
| `DB_HOST` | Host donde escucha MySQL (`127.0.0.1`). | Sí |
| `DB_PORT` | Puerto de MySQL; `compose.yaml` lo publica en `13306`. | Sí |
| `DB_USER` | Usuario de MySQL que usa la API (sin privilegios de administrador). | Sí |
| `DB_PASSWORD` | Clave de ese usuario. | Sí |
| `DB_NAME` | Nombre de la base de datos (`katea`). | Sí |
| `MYSQL_ROOT_PASSWORD` | Clave de root de MySQL; solo la usa `compose.yaml` al crear el contenedor. | Sí, para Docker |
| `JWT_SECRETO` | Firma los tokens de sesión. Debe ser aleatorio y de al menos 32 bytes; con el valor de ejemplo no se puede iniciar sesión ni usar rutas protegidas. | Sí |
| `CORS_ORIGENES` | Páginas que pueden usar la API desde el navegador, separadas por comas (nunca `*`). Por omisión, el front en el puerto 5500. | No |
| `KATEA_ENTORNO` | Debe valer `desarrollo` para permitir `scripts/crear_usuarios_desarrollo.py`. | Solo para crear usuarios |
| `GEMINI_API_KEY` | Clave de la IA que clasifica comentarios. Sin ella, `POST /pedidos/comentario` responde 503. | Para comentarios |
| `GEMINI_MODELO` | Modelo de Gemini que se consulta. | No |
| `EXTERNO_URL` | A dónde se envía la petición de IA. Para las pruebas apunta al simulador (`http://127.0.0.1:9000`). | No |
| `EXTERNO_TIMEOUT` | Segundos máximos de espera por intento de IA (5 por omisión); si se agota, 504. | No |

## Ejemplos de uso

El flujo típico es: iniciar sesión, guardar el token y mandarlo en el encabezado `Authorization` de las rutas protegidas. Sustituye `TU_CLAVE` por la clave que diste al crear el usuario y `TOKEN` por el `access_token` recibido.

**1. Iniciar sesión y obtener el token** (responde `{"access_token": "...", "token_type": "bearer"}`, válido 30 minutos):
```
:: Windows (cmd)
curl -X POST http://127.0.0.1:8000/login -H "Content-Type: application/json" -d "{\"usuario\": \"dev_cliente1\", \"clave\": \"TU_CLAVE\"}"
set TOKEN=pega_aqui_el_access_token
```
```bash
# bash
curl -X POST http://127.0.0.1:8000/login -H 'Content-Type: application/json' -d '{"usuario": "dev_cliente1", "clave": "TU_CLAVE"}'
TOKEN=pega_aqui_el_access_token
```

**2. Usar una ruta protegida: ver mis pedidos** (un cliente solo ve los suyos; sin token responde 401):
```
:: Windows (cmd)
curl http://127.0.0.1:8000/pedidos -H "Authorization: Bearer %TOKEN%"
```
```bash
# bash
curl http://127.0.0.1:8000/pedidos -H "Authorization: Bearer $TOKEN"
```

**3. Crear un pedido** (el dueño sale del token y los precios de la base de datos; responde 201 con el total calculado):
```
:: Windows (cmd)
curl -X POST http://127.0.0.1:8000/pedidos -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json" -d "{\"productos\": [{\"producto_id\": 1, \"cantidad\": 2}]}"
```
```bash
# bash
curl -X POST http://127.0.0.1:8000/pedidos -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"productos": [{"producto_id": 1, "cantidad": 2}]}'
```
Para que funcione debe existir un producto disponible con ese `producto_id`; los crea el administrador con `POST /productos` (puedes hacerlo desde `/docs` con el botón **Authorize**).

## Contrato y errores

- Contrato OpenAPI interactivo: http://127.0.0.1:8000/docs (también `/redoc`).
- Contrato exportado: [docs/openapi.json](docs/openapi.json). Se regenera con `python scripts/generar_contrato.py`.
- Errores: todos responden `{"error": "...", "detalles": [...]}`. El catálogo de códigos (400, 401, 403, 404, 409, 422, 502, 503, 504, 500) está en [docs/errores.md](docs/errores.md).
- Seguridad: cómo responde la API a cada riesgo del OWASP API Security Top 10 (2023) y qué queda pendiente, en [docs/seguridad.md](docs/seguridad.md).

## Cómo probarla

**Pruebas automáticas (pytest).** No necesitan MySQL ni Gemini: usan repositorios en memoria y dobles de prueba.
```
python -m pytest -q
```
Resultado de la versión v1.0.0: **252 pruebas aprobadas** (`252 passed`).

**Pruebas de caja negra con `probar_api.py` y el simulador de IA.** Hablan por HTTP con la API real, así que necesitan MySQL y los usuarios de desarrollo del paso 4. Antes, copia `pruebas/profesor/prueba.example.json` como `pruebas/profesor/prueba.json` y complétalo con tus datos; esa copia es personal y Git la ignora. Usa tres terminales:
```
:: Terminal 1: simulador de la IA (puerto 9000)
python pruebas/profesor/simulador.py

:: Terminal 2: la API apuntando al simulador (Windows cmd)
set EXTERNO_URL=http://127.0.0.1:9000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

:: Terminal 3: las pruebas
python pruebas/profesor/probar_api.py pruebas/profesor/prueba.json
```
En bash, la terminal 2 queda en una línea: `EXTERNO_URL=http://127.0.0.1:9000 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. La prueba de persistencia queda pendiente en la primera corrida: reinicia solo la API (Ctrl+C y vuelve a arrancarla) y corre `probar_api.py` otra vez.

## Anatomía de mi API

```
Anatomía de mi API · lista de revisión (43 de 43)

0 · Cliente (2/2)
  [x] Mi proyecto tiene un cliente que consume la API: una página, una app o un script.
  [x] Puedo hacer una acción en el cliente y mostrar la petición y la respuesta en la pestaña Red (F12).
  En la presentación: Abran su front y hagan una acción en vivo. Con F12 → Red, muestren la petición que salió y la respuesta que llegó.

1 · Petición HTTP (3/3)
  [x] Mis rutas nombran cosas (/tareas, /tareas/7), no acciones (/crearTarea).
  [x] Cada operación usa el método correcto: GET lee, POST crea, PUT o PATCH modifica, DELETE borra.
  [x] Tengo la ficha de endpoints: método, ruta, qué recibe y qué responde.
  En la presentación: Muestren su ficha de endpoints o /docs y expliquen en una frase qué hace cada ruta.

2 · CORS (3/3)
  [x] Configuré CORS con una lista de orígenes, no con *.
  [x] Authorization y Content-Type están en los encabezados permitidos.
  [x] CORS va antes de revisar el token.
  En la presentación: Abran su front desde su origen (por ejemplo, el puerto 5500) con F12 abierto: la consola sin errores de CORS.

3 · Autenticación (3/3)
  [x] Las contraseñas se guardan con hash (bcrypt o password_hash).
  [x] El login regresa un token JWT con vencimiento.
  [x] Sin token, o con un token alterado, la API responde 401.
  En la presentación: Hagan una petición a una ruta protegida sin token (401) y luego con token (200).

4 · Autorización (2/2)
  [x] Hay al menos dos roles y una acción que un rol no puede hacer (403).
  [x] Las consultas de recursos propios filtran por el usuario del token (WHERE id = ? AND usuario = ?).
  En la presentación: Con el usuario A pidan un recurso del usuario B: debe responder 404. Con un rol sin permiso intenten borrar: 403.

5 · Validación (3/3)
  [x] Valido campos obligatorios, tipo, formato y rango.
  [x] Un dato inválido responde 422 y dice qué campo falló.
  [x] Un duplicado o una regla rota responde 409.
  En la presentación: Manden un dato inválido desde su front y muestren que el error aparece en el campo correcto.

6 · Endpoint / controlador (2/2)
  [x] Tengo el CRUD completo de mi recurso principal.
  [x] Cada operación responde con su código: 200, 201, 204 o 404.
  En la presentación: Recorran el CRUD de su recurso principal en /docs, Postman o su front.

7 · Servicio / lógica de negocio (2/2)
  [x] Identifico al menos una regla de negocio propia de mi proyecto.
  [x] La regla está en una función aparte, no revuelta con el manejo de HTTP.
  En la presentación: Expliquen su regla de negocio y muestren el caso en que dice que no (409).

7b · Integraciones externas (5/5)
  [x] Mi API consume al menos un servicio externo.
  [x] La llamada tiene un tiempo máximo de espera (timeout).
  [x] Si el servicio falla o tarda, responde 502 o 504 con un mensaje claro.
  [x] La clave del servicio está en una variable de entorno.
  [x] Puedo explicar en qué caso se usaría SOAP en lugar de REST (por ejemplo, el SAT).
  En la presentación: Muestren la integración funcionando y luego la falla controlada: sin clave (503) o con el servicio caído (502 o 504).

8 · Persistencia (2/2)
  [x] Los datos se guardan en una base de datos y sobreviven al reinicio.
  [x] Todas mis consultas usan parámetros (?), ninguna pega datos al texto del SQL.
  En la presentación: Reinicien la API en vivo y muestren que los datos siguen ahí. Enseñen una de sus consultas con ?.

9 · Respuesta HTTP (2/2)
  [x] Todos mis errores salen en JSON con el mismo formato: {"error": ..., "detalles": [...]}.
  [x] Ningún error muestra trazas, rutas de archivos ni SQL.
  En la presentación: Provoquen dos errores distintos y muestren que ambos llegan con el mismo formato JSON.

Configuración base (3/3)
  [x] Secretos y claves (JWT, IA, base de datos) se leen de variables de entorno, no están escritos en el código.
  [x] En mi repositorio de GitHub no hay ninguna clave.
  [x] Mi README dice qué variables hay que configurar.
  En la presentación: Muestren dónde lee su código las variables de entorno y busquen en vivo en su repositorio que no haya ninguna clave.

Pruebas automáticas (2/2)
  [x] Tengo pruebas automáticas (probar_api.py, una colección de Postman o similar).
  [x] Las pruebas pasan antes de entregar.
  En la presentación: Corran sus pruebas en vivo y comenten el resultado.

Documentación (6/6)
  [x] Mi README explica qué es, cómo correrla en pocos pasos, qué variables configurar y cómo probarla.
  [x] Mi API publica su contrato (OpenAPI en /docs u openapi.yaml).
  [x] Tengo .env.example con las variables de entorno, sin valores secretos.
  [x] Tengo docs/arquitectura.md con el diagrama C4 de contenedores: página, API, base de datos y servicio externo.
  [x] Tengo CHANGELOG.md con lo que trae la versión v1.0.0.
  [x] Recomendado: 2 decisiones explicadas (ADR) en docs/decisiones/ y el catálogo de errores en docs/errores.md.
  En la presentación: Abran su repositorio en GitHub: el README y el diagrama de arquitectura. Con el diagrama expliquen qué parte de su sistema está distribuida y cómo se comunican las piezas.

Timeout e idempotencia (2/2)
  [x] Sé qué operaciones de mi API se pueden repetir sin riesgo y cuáles no.
  [x] Si reintento llamadas externas, solo es ante fallas pasajeras (429, 5xx o timeout).
  En la presentación: Expliquen qué pasaría en su proyecto si el usuario le da doble clic a "Guardar".

Seguridad en capas (1/1)
  [x] Puedo decir qué riesgo del OWASP API Top 10 evita cada capa de mi API.
  En la presentación: Cierren la presentación con la tabla “riesgo → cómo lo evita mi API”.
```

## REST y SOAP en mi proyecto

Katea usa REST: expone recursos como `/productos` y `/pedidos`, intercambia JSON y usa los métodos HTTP (GET, POST, PUT, DELETE) y sus códigos de estado para expresar el resultado. Es sin estado: cada petición lleva su JWT, así que el servidor no guarda sesiones. SOAP, en cambio, es un protocolo con un contrato formal en WSDL y mensajes en XML; se usa donde se exige un contrato estricto entre sistemas, como el servicio de consulta del estado de un CFDI del SAT. Katea no implementa SOAP: esto es solo una propuesta. Si se agregara, viviría en `app/integraciones/` (por ejemplo, `sat_cfdi.py`) con el mismo patrón que `gemini.py`: timeout por intento, errores 502/504 cuando el servicio falla o tarda, y su configuración en variables de entorno.

## Equipo y reflexiones

| Integrante | Qué hizo |
|---|---|
| Arisbeth Cervantes | Reorganizó el proyecto en la estructura app/ por capas y escribió la documentación de entrega (README, arquitectura C4, errores, decisiones, seguridad y CHANGELOG). En la presentación explica el cliente, el CRUD, la regla de negocio, la persistencia, las pruebas y el cierre. |
| Diego Verduzco | Explica y defiende la autenticación (bcrypt y JWT), la autorización por rol, la validación de datos y el formato único de errores. |
| Lorenzo Chávez | Explica y defiende CORS y la integración con Gemini (timeout, reintento y errores 502, 503 y 504). |

**Arisbeth Cervantes:** Durante el proyecto me costó identificar los códigos de error de una API REST y entender el CRUD de la API. Gracias a eso ahora puedo explicar el flujo completo de crear un producto o un pedido. Para crear un producto se manda un POST a `/productos` con nombre, descripción, precio, `imagen_url`, disponible y preparación; el `id` lo asigna la base de datos, y se necesita el token de un usuario con rol admin. Si tuviera más tiempo, puliría el login para limitar los intentos de sesión repetidos.

**Diego Verduzco:** Con lo anterior visto vemos que la seguridad no es un agregado más, sino la base de la API: separar quién eres de qué puedes hacer, exigir tokens cortos y bien estructurados, aislar los datos por usuario y devolver respuestas de error claras y consistentes (como el formato de "error" y "detalles" y los códigos HTTP adecuados) hace que el sistema sea más fácil de mantener y difícil de atacar.

**Lorenzo Chávez:** La API no solo responde a quien la usa, también tiene que saber comunicarse con lo que no controla: limitar con CORS qué páginas pueden usarla desde el navegador, sin abrirla a cualquier origen, y tratar a un servicio externo como Gemini con desconfianza y ponerle un tiempo máximo de espera, reintentar solo cuando el error es temporal y es seguro repetir la petición, validar lo que responde y devolver errores claros (502, 503 o 504) cuando algo falla, esto lo hace confiable aunque haya cosas por fuera que no lo son.

---

Más documentación: guías de [autenticación](docs/guias/autenticacion.md) y [pedidos](docs/guias/pedidos.md), y el historial de actividades del curso en [docs/guias/](docs/guias/).
