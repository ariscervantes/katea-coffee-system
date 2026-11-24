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

<!-- Pegar aquí lo que copia el botón "Copiar mi lista" del mapa interactivo. -->

```
[COMPLETAR: pegar la lista del botón "Copiar mi lista"]
```

## REST y SOAP en mi proyecto

Katea usa REST: expone recursos como `/productos` y `/pedidos`, intercambia JSON y usa los métodos HTTP (GET, POST, PUT, DELETE) y sus códigos de estado para expresar el resultado. Es sin estado: cada petición lleva su JWT, así que el servidor no guarda sesiones. SOAP, en cambio, es un protocolo con un contrato formal en WSDL y mensajes en XML; se usa donde se exige un contrato estricto entre sistemas, como el servicio de consulta del estado de un CFDI del SAT. Katea no implementa SOAP: esto es solo una propuesta. Si se agregara, viviría en `app/integraciones/` (por ejemplo, `sat_cfdi.py`) con el mismo patrón que `gemini.py`: timeout por intento, errores 502/504 cuando el servicio falla o tarda, y su configuración en variables de entorno.

## Equipo y reflexiones

| Integrante | Qué hizo |
|---|---|
| Arisbeth Cervantes | [COMPLETAR] |
| Diego Verduzco | [COMPLETAR] |
| Lorenzo Chávez | [COMPLETAR] |

**Arisbeth Cervantes:** [COMPLETAR: reflexión con sus propias palabras]

**Diego Verduzco:** [COMPLETAR: reflexión con sus propias palabras]

**Lorenzo Chávez:** [COMPLETAR: reflexión con sus propias palabras]

---

Más documentación: guías de [autenticación](docs/guias/autenticacion.md) y [pedidos](docs/guias/pedidos.md), y el historial de actividades del curso en [docs/guias/](docs/guias/).
