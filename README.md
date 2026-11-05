# katea-coffee-system
Katea es un proyecto académico de cafetería cuyo objetivo es ofrecer menú digital, pedidos y consulta mediante QR para pago en caja. Estas funcionalidades todavía no están implementadas.

## Estado actual

La API de productos tiene cinco rutas CRUD, modelo validado, errores uniformes, almacenamiento en memoria y generación de identificadores. POST y PUT comprueban duplicados por nombre y preparación. Las pruebas propias del proyecto corresponden a Aris con el asistente; el compañero se encarga únicamente de preparar y ejecutar las pruebas del profesor. Las pruebas propias incluyen regresiones HTTP de validación, conflictos 409, CRUD y PUT repetido.

## Instalación

Comandos desde la raíz del repositorio, en Bash. El entorno se comprobó con Python 3.14.4:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Si `.venv` ya existe, basta con activarlo e instalar las dependencias. Actívalo en cada terminal nueva. `requirements.txt` fija las versiones de la API y de las herramientas de prueba; `.gitignore` excluye el entorno y los archivos temporales.

## Comprobación del entorno

```bash
python -c "import fastapi, uvicorn, pydantic, pytest, httpx; print('Importaciones correctas')"
python -m pip check
```

Estas comprobaciones verifican importaciones y compatibilidad declarada entre paquetes; no prueban el funcionamiento del CRUD.

## Ejecutar la API

Con el entorno activo, desde la raíz:

```bash
python -m uvicorn main:app --reload
```

`main:app` señala el objeto FastAPI del archivo `main.py`. La documentación de las operaciones está en http://127.0.0.1:8000/docs. La memoria y la secuencia de IDs son locales a un proceso y se reinician al recargar o detener el servidor. Para esta práctica se usará un solo proceso.

| Método y ruta | Comportamiento | Éxito |
| --- | --- | --- |
| GET /productos | Lista todos, incluidos los no disponibles | 200 |
| GET /productos/{id} | Consulta un producto | 200 |
| POST /productos | Valida los seis campos y genera el ID | 201 |
| PUT /productos/{id} | Reemplaza los seis campos conservando el ID | 200 |
| DELETE /productos/{id} | Elimina el producto | 204 sin cuerpo |

POST y PUT reciben los seis campos obligatorios sin `id`. No se permiten nombres duplicados con la misma preparación, comparando sin mayúsculas ni espacios exteriores (409). PUT excluye al propio producto de esa comparación. Un producto inexistente devuelve 404; datos inválidos, 422; JSON mal formado, 400. Los errores tienen formato `{"error": "...", "detalles": [...]}`. El filtro del menú público y la autenticación se definirán después.

## Comprobar las validaciones

```bash
python -m pytest -q
```

Las pruebas de `tests/test_base_api.py` comprueban el modelo, IDs y errores. Una ruta `/validar` existe únicamente en la aplicación temporal de pruebas, no en `main:app`. HTTPX usa transporte ASGI en memoria, sin abrir un puerto. No se requiere instalar paquetes adicionales.

Última ejecución de pruebas propias: **90 aprobadas en 0.86 s**. La suite cubre modelo, campos obligatorios, límites, IDs, rutas y regresiones HTTP de POST/PUT, errores uniformes, duplicados, CRUD y PUT repetido. Los errores comprobados devuelven 400/404/409/422, sin respuestas 500.

El precio conserva la validación original: número obligatorio mayor que cero, con máximo dos decimales, sin aceptar textos ni booleanos. Se convierte de int/float a `Decimal` dentro del modelo y se serializa como número JSON. Se permiten ceros finales: `25.000` equivale a `25` y `25.120` a `25.12`; `25.123` se rechaza. Se utiliza la lectura JSON normal de FastAPI. No se conserva precisión decimal arbitraria antes de validar: los casos de alta precisión reportados pueden redondearse al leerlos como float; la corrección de ese comportamiento se retiró del alcance por decisión de Aris.

Nombre y descripción se recortan antes de validar su longitud. Se rechazan campos extra, incluido `id` en la entrada del cliente.

`imagen_url` debe ser texto no vacío y terminar literalmente en `.jpg`, `.jpeg`, `.png` o `.webp`. El último segmento de la ruta debe tener un nombre no vacío (tras quitar espacios) antes de la extensión: `.jpg`, `/img/.png` y ` .jpeg` se rechazan. Se rechazan saltos de línea CR y LF en cualquier posición. Se mantiene el comportamiento original para mayúsculas y parámetros: `foto.JPG` y `foto.jpg?v=1` se rechazan porque no terminan en uno de los sufijos literales admitidos. Esta comprobación mínima no descarga la imagen ni verifica su existencia, contenido o la validez completa de una URL.

## Prueba del profesor y configuración individual

`probar_api.py` se conserva sin modificar y se ejecutará directamente con `prueba.json`. La configuración actual ya usa `/productos`, los seis campos y un PUT completo. La matrícula local de Aris es `20204413`; conservar ese cambio personal al revisar Git.

Con la API ejecutándose en una terminal, abre otra, activa el entorno y ejecuta desde la raíz para una ejecución normal:

```bash
source .venv/bin/activate
python probar_api.py
```

Cada integrante debe poner su matrícula en `prueba.json` para su ejecución. Para compartirlo, se propone versionar una configuración común con matrícula ilustrativa y no incluir en commits los cambios personales de matrícula. Antes de preparar un commit, revisar `git diff -- prueba.json` y después `git diff --cached -- prueba.json`; añadir archivos por nombre o seleccionar cambios con `git add -p`. Esta revisión reduce errores, pero no bloquea automáticamente una matrícula personal. No se han instalado controles automáticos.

Aris ya había ejecutado personalmente el script con resultado **11 de 11**. En la revisión anterior, antes de reducir el alcance, el asistente realizó una ejecución nueva e independiente: **11 de 11**, matrícula `20204413`, contra una instancia aislada en `127.0.0.1:37383`. Se usó una copia temporal de la configuración con solo el puerto cambiado; no se alteraron `prueba.json`, el script ni el reporte anterior. El reporte nuevo quedó en `/tmp/katea-revision-nonbaek8/reporte_U3S2_20204413.txt`; `/tmp` es temporal y debe respaldarse si se usará como evidencia. Estas dos ejecuciones son distintas. El script del profesor no se volvió a ejecutar después de reducir el alcance; la verificación actual corresponde a las 90 pruebas propias.

### Evidencias personales

El script escribe `reporte_U3S2_<matrícula>.txt` en el directorio desde el que se ejecuta: con estas instrucciones, en la raíz del proyecto. Git ignora esos reportes y la carpeta `evidencias/`. `prueba.json` no está ignorado porque se compartirá con el equipo. Ignorar archivos no los elimina ni respalda.

Después de cada ejecución real, copia el reporte y sus capturas a `evidencias/<matrícula>/<fecha-hora>/` para evitar que otra ejecución sobrescriba la evidencia anterior. Guarda además una copia fuera del repositorio para la entrega. Usa únicamente reportes y capturas de tu propia ejecución y conserva el texto completo del reporte; la ejecución aislada descrita arriba generó un reporte nuevo fuera del repositorio.

## Continuidad del proyecto

Consulta [el contexto del proyecto](docs/CONTEXTO_PROYECTO.md) para conocer las reglas acordadas, verificaciones realizadas y pendientes. El README contiene las instrucciones de instalación y uso; el documento de contexto permite retomar el trabajo con el equipo y asistentes de IA.
