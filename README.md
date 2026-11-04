# katea-coffee-system
Katea es un proyecto académico de cafetería cuyo objetivo es ofrecer menú digital, pedidos y consulta mediante QR para pago en caja. Estas funcionalidades todavía no están implementadas.

## Estado actual

La API de productos tiene cinco rutas CRUD, modelo validado, errores uniformes, almacenamiento en memoria y generación de identificadores. POST y PUT comprueban duplicados por nombre y preparación. Las pruebas propias del proyecto corresponden a Aris con el asistente; el compañero se encarga únicamente de preparar y ejecutar las pruebas del profesor. La cobertura funcional completa de endpoints sigue pendiente.

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

Última ejecución de pruebas propias: **71 aprobadas en 0.46 s**. La prueba de ausencia de rutas se reemplazó por una comprobación de los cinco pares método/ruta esperados. La suite cubre validaciones, IDs, errores y registro de rutas; todavía no verifica el funcionamiento completo del CRUD, los conflictos 409 ni el PUT repetido.

El precio acepta números JSON positivos con hasta dos decimales y rechaza textos y booleanos. Se conserva como `Decimal` internamente y se serializa como número JSON. Los ceros decimales finales no cambian el valor. Nombre y descripción se recortan antes de validar su longitud. La extensión de imagen se comprueba literalmente en minúsculas, sin verificar el archivo. Se rechazan campos extra, incluido `id` en la entrada del cliente.

## Prueba del profesor y configuración individual

`probar_api.py` se conserva sin modificar y se ejecutará directamente con `prueba.json`. Este JSON aún conserva el ejemplo de equipos y matrícula 20201234: el compañero encargado de las pruebas del profesor lo adaptará a `/productos`, con los seis campos y un cambio PUT completo. No se utilizan configuraciones alternativas.

Con la API ejecutándose en una terminal, abre otra, activa el entorno y ejecuta desde la raíz cuando la configuración esté preparada:

```bash
source .venv/bin/activate
python probar_api.py
```

Cada integrante debe poner su matrícula en `prueba.json` para su ejecución. Para compartirlo, se propone versionar una configuración común con matrícula ilustrativa y no incluir en commits los cambios personales de matrícula. Antes de preparar un commit, revisar `git diff -- prueba.json` y después `git diff --cached -- prueba.json`; añadir archivos por nombre o seleccionar cambios con `git add -p`. Esta revisión reduce errores, pero no bloquea automáticamente una matrícula personal. No se han instalado controles automáticos.

El compañero preparará `prueba.json` y ejecutará el script del profesor; ambas tareas siguen pendientes. Aris y el asistente mantienen las pruebas propias, incluida la comprobación actualizada del registro de rutas. Queda pendiente ampliar sus pruebas funcionales del CRUD.

### Evidencias personales

El script escribe `reporte_U3S2_<matrícula>.txt` en el directorio desde el que se ejecuta: con estas instrucciones, en la raíz del proyecto. Git ignora esos reportes y la carpeta `evidencias/`. `prueba.json` no está ignorado porque se compartirá con el equipo. Ignorar archivos no los elimina ni respalda.

Después de cada ejecución real, copia el reporte y sus capturas a `evidencias/<matrícula>/<fecha-hora>/` para evitar que otra ejecución sobrescriba la evidencia anterior. Guarda además una copia fuera del repositorio para la entrega. Usa únicamente reportes y capturas de tu propia ejecución y conserva el texto completo del reporte; no se ha generado ninguno en esta preparación.

## Continuidad del proyecto

Consulta [el contexto del proyecto](docs/CONTEXTO_PROYECTO.md) para conocer las reglas acordadas, verificaciones realizadas y pendientes. El README contiene las instrucciones de instalación y uso; el documento de contexto permite retomar el trabajo con el equipo y asistentes de IA.
