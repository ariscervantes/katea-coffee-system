# Katea — API de productos

Proyecto académico con FastAPI, MySQL 8 y PyMySQL. Pedidos, pagos, QR y autenticación quedan fuera de esta actividad.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

La aplicación lee DB_HOST, DB_PORT, DB_USER, DB_PASSWORD y DB_NAME desde el entorno o un archivo `.env` local, ignorado por Git. `.env.example` sirve como plantilla. No compartir contraseñas ni versionar `.env`.

Se incluye `compose.yaml` para un MySQL 8 dedicado. Usa el proyecto Docker `katea`, el volumen `katea_mysql_data` y publica el puerto solo en `127.0.0.1:13306`. No modifica los otros contenedores. El usuario `katea_app` accede únicamente a la base `katea`.

La configuración local `.env` contiene también `MYSQL_ROOT_PASSWORD`, usada solo para inicializar el contenedor. Con `.env` preparado:

```bash
docker compose up -d --wait mysql
docker compose ps
```

MySQL crea la base y el usuario al inicializar un volumen vacío. Cambiar las contraseñas en `.env` después no actualiza las cuentas de un volumen existente. Conservar el volumen para mantener los datos; no usar `docker compose down -v` si se necesitan. La API crea la tabla, no la base. El esquema también está en `sql/esquema.sql`.

```bash
python -m uvicorn main:app --reload
```

Al iniciar, `main.py` llama a `RepositorioProductos.inicializar()`. `basedatos.py` administra conexiones, commit, rollback y cierre. `repositorio.py` ejecuta las consultas y convierte filas a productos. Una conexión fallida al iniciar impide arrancar la API. Los datos sobreviven al reinicio de la API; el volumen configurado en Compose conserva los datos al recrear el contenedor, siempre que no se elimine dicho volumen.

Las consultas usan `cursor.execute(sql, parametros)` con marcadores `%s` de PyMySQL y valores separados. No se concatenan datos del cliente ni se usan marcadores `?`.

## Operaciones y reglas

| Método | Ruta | Éxito |
| --- | --- | --- |
| GET | `/productos` | 200, incluye no disponibles |
| GET | `/productos/{id}` | 200 |
| POST | `/productos` | 201, ID autoincremental |
| PUT | `/productos/{id}` | 200, reemplazo completo |
| DELETE | `/productos/{id}` | 204 sin cuerpo |

Los seis campos son obligatorios; se rechazan campos extra, incluido id. Nombre: 2–80 caracteres; descripción: 5–200; ambos se recortan. Precio: número positivo, máximo dos decimales, sin textos ni booleanos; permite ceros finales. Se convierte a Decimal después de la lectura JSON normal, sin preservar precisión arbitraria antes de validar. Imagen: sufijo literal .jpg, .jpeg, .png o .webp, nombre de archivo no vacío y sin CR/LF; no se descarga. Disponible: booleano estricto. Preparación: frio, caliente o no_aplica.

Los duplicados comparan nombre con strip/casefold y preparación; MySQL respalda la regla con una restricción única. PUT excluye al propio producto y permite repetir el reemplazo. Errores: 400 JSON mal formado, 404 inexistente, 409 duplicado, 422 datos inválidos. El formato es `{"error": "...", "detalles": [...]}`; el 500 lleva mensaje genérico.

## Contrato y pruebas propias

FastAPI publica `/docs`, `/redoc` y `/openapi.json`, con respuestas de éxito y errores aplicables. Precio de entrada se anuncia como número. Las reglas adicionales están descritas arriba; no todas están expresadas como restricciones del esquema.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
```

Las pruebas usan un repositorio aislado inyectado desde `tests/conftest.py`, sin puertos ni conexión real a MySQL. Cubren validaciones, CRUD, errores, duplicados, PUT repetido, documentación y ciclo de vida. La suite obtuvo **90 pruebas aprobadas**. Por separado se verificaron contra MySQL 8.0.46: valores con comillas guardados literalmente, conversión de DECIMAL y booleanos, duplicados, reemplazo repetido y rollback. Estas comprobaciones SQL adicionales se registraron en las evidencias de la sesión.

## Pruebas del profesor

`probar_api.py` conserva la versión de sesión 2, de 11 verificaciones. `probar_api_U3S3.py` contiene sin cambios la versión de 15 verificaciones de Aris.zip. Sus mensajes internos todavía usan el nombre probar_api.py; ejecutar en este proyecto:

```bash
python probar_api_U3S3.py prueba.json
```

La primera ejecución deja pendiente la prueba 15 y crea `.persistencia_U3S3_*.json`. Reiniciar únicamente la API y repetir el comando desde el mismo directorio y con la misma configuración, conservando MySQL y el archivo de estado. El script comprueba el registro anterior; el reinicio debe hacerse y documentarse manualmente. El asistente ejecutó ambas rondas contra MySQL 8.0.46: **14/15** inicialmente, con persistencia pendiente, y **15/15** después de detener la API y arrancar un proceso nuevo. MySQL permaneció activo. Antes de la segunda ronda se confirmó directamente en SQL que el registro de control existía.

La configuración compartida de `prueba.json` agrega la ruta de OpenAPI; la matrícula personal 20204413 se conserva únicamente como cambio local. Evitar incluir accidentalmente la matrícula personal en commits: añadir archivos por nombre y revisar `git diff --cached -- prueba.json`.

El script nuevo escribe reporte_U3S3 y el anterior reporte_U3S2. Respaldar cada reporte y capturas reales en `evidencias/<matrícula>/<fecha-hora>/` antes de repetir. Reportes, evidencias y estado temporal están ignorados. No atribuir ejecuciones del asistente al estudiante.

El estado y pendientes están en `docs/CONTEXTO_PROYECTO.md`.


## Verificación de esta integración (2026-11-06)

Evidencias del asistente: `evidencias/20204413/20261106-151600-persistencia-mysql/`. Incluyen reportes separados por ronda, configuración de prueba con puerto 18000, registros de API, comprobación SQL y constancia de los procesos reiniciados. No se generaron capturas ni son una ejecución personal de Aris.

Resultado final: `U3S3;20204413;http://127.0.0.1:18000/productos;111111111111111;E3B12A3F`.

La API temporal se detuvo al terminar. El MySQL dedicado permanece activo, con su volumen conservado. Para ejecutar personalmente, iniciar la API en el puerto habitual 8000 y usar `prueba.json`, sin cambiar la matrícula. El primer resultado será 14/15 si no existe un estado anterior; repetir después del reinicio para completar la prueba 15.

Aris confirmó su ejecución personal después de reiniciar la API con **15 de 15**. Se revisó el reporte local en el puerto 8000; el reporte y las evidencias personales no se versionan.
