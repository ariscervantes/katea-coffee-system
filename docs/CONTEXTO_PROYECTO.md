# Contexto del proyecto Katea

Documento de continuidad para conversaciones nuevas y para el equipo. Última revisión local: 2026-11-04. No sustituye la revisión del código, Git y las instrucciones vigentes de la clase. Los datos del equipo y de la actividad provienen del documento aportado; no se han cotejado con Classroom.

## Proyecto y equipo

- **Nombre:** Katea — menú digital y pedidos para cafetería.
- **Asignatura:** Programación Distribuida, Universidad de Colima.
- **Repositorio:** https://github.com/ariscervantes/katea-coffee-system
- **Integrantes:** Arisbeth Cervantes (20204413), Diego Verduzco (20205116) y Lorenzo Chávez (20209634).
- **Modo de trabajo preferido:** explicaciones claras, acompañamiento por etapas y aprendizaje activo. Usar Codex dentro del proyecto local. No hacer commit, push ni abrir pull requests hasta que Aris lo indique.

## Objetivo y alcance futuro

El cliente consulta un menú digital, selecciona productos y confirma una orden. Recibe un QR asociado a su pedido; en caja, el personal lo escanea para recuperar los productos y el total, y registrar el pago. A futuro habrá administración del menú y login para el personal. No se ha implementado ni validado aquí la solución completa.

## Actividad actual: Unidad III, sesión 2

1. Revisar la ficha original y los códigos de respuesta.
2. Resolver individualmente los ejercicios de filtros y detección de bugs.
3. Acordar antes de programar las reglas de un recurso: productos.
4. Implementar cinco endpoints: GET /productos, GET /productos/{id}, POST /productos, PUT /productos/{id} y DELETE /productos/{id}. Almacenar datos en memoria; la base de datos se abordará después.
5. Usar errores con formato {"error": "...", "detalles": [...]}; seguir la guía de clase sobre 400, 404, 409 y 422.
6. Adaptar `prueba.json`, configurar la matrícula individual y ejecutar `python probar_api.py` con la API en marcha; objetivo: 11 de 11, todavía pendiente de ejecución. Revisar también las reglas de validación y 409, que no están todas cubiertas por ese script.
7. Trabajar en una rama y abrir un pull request que describa qué cambia y cómo se probó, incluyendo la línea RESULTADO. Otro integrante debe revisarlo según la lista de la diapositiva 18.
8. Completar las evidencias y reflexión de la actividad. Cada integrante entrega su propio PDF, con reporte y captura reales.

## Reglas de productos acordadas para la práctica

La API genera el id. El cliente no lo proporciona al crear.

- **nombre:** texto obligatorio de 2 a 80 caracteres tras quitar espacios al inicio y al final.
- **descripcion:** texto obligatorio de 5 a 200 caracteres tras quitar espacios al inicio y al final.
- **precio:** número obligatorio mayor que cero, con máximo dos decimales. No aceptar números como texto, por ejemplo "25".
- **imagen_url:** texto obligatorio no vacío que termina en .jpg, .jpeg, .png o .webp. Se valida la dirección, no la existencia ni el contenido del archivo.
- **disponible:** booleano obligatorio; aceptar true o false y rechazar cadenas y números.
- **preparacion:** texto obligatorio: frio, caliente o no_aplica.

**Conflicto 409:** no permitir dos registros con la misma combinación de nombre y preparación. Comparar nombres sin distinguir mayúsculas/minúsculas y quitando espacios al inicio y final. En PUT, excluir el mismo producto al comprobar el conflicto: puede conservar su combinación, pero no adoptar la de otro producto. Repetir el mismo PUT debe mantener los datos.

Ejemplo válido:

```json
{
  "nombre": "Matcha latte",
  "descripcion": "Bebida de té matcha con leche.",
  "precio": 65.00,
  "imagen_url": "/imagenes/matcha-latte.jpg",
  "disponible": true,
  "preparacion": "frio"
}
```

Implementado para esta práctica: GET /productos incluye disponibles y no disponibles. El filtro del menú público se definirá después. El login y los permisos 401/403 son futuros; no están implementados.

Códigos requeridos: 400 para JSON mal formado, 422 para datos inválidos, 404 para producto solicitado no encontrado, 409 para conflicto nombre/preparación, 201 al crear, 200 al consultar o reemplazar y 204 al eliminar, sin cuerpo. PUT reemplaza todos los campos obligatorios.

## Estado conocido al último diagnóstico de Codex local

Ruta local: `~/Documents/katea/katea-coffee-system`. Estado comprobado el 2026-11-04:

- La rama actual es `actividad/productos-api`; HEAD continúa en `f02c243` (Initial commit). `origin` apunta al repositorio indicado. No se consultó el servidor remoto para comprobar cambios recientes. No se han realizado commits nuevos, push ni PR en estas sesiones.
- README.md es el único archivo versionado al revisar Git. Incluye instalación, arranque de la aplicación base y ejecución de las pruebas; tiene modificaciones sin commit.
- probar_api.py y prueba.json estaban presentes pero sin seguimiento. Habían sido copiados desde la carpeta superior; la igualdad con esas copias no certifica su procedencia.
- `prueba.json` conserva intacto el ejemplo de equipos y matrícula 20201234. El compañero encargado de las pruebas del profesor se encargará de adaptarlo a productos; no modificarlo por ahora. Decisión vigente: usar directamente ese archivo con `python probar_api.py`, sin configuraciones alternativas. Se retiró la plantilla creada en el paso anterior; no existe configuración local alternativa. Cada integrante ejecutará con su matrícula (Aris: 20204413).
- Entorno `.venv` creado con Python 3.14.4. `.gitignore` excluye el entorno, bytecode y caché de pytest. `requirements.txt` registra las versiones instaladas, incluidas dependencias indirectas: FastAPI 0.162.0, Uvicorn 0.54.0, Pydantic 2.14.2, pytest 9.2.0 y HTTPX 0.28.1 entre ellas.
- `.gitignore` y `requirements.txt` estaban sin seguimiento; `docs/CONTEXTO_PROYECTO.md` se incorpora en esta actualización desde `Downloads/Contexto_proyecto_Katea.md`, conservando el original.
- Implementado: `main.py` crea FastAPI; `modelos.py` define los seis campos obligatorios, validaciones y representación con id; `memoria.py` prepara un diccionario vacío y secuencia creciente de IDs; `errores.py` registra respuestas uniformes para errores de validación y HTTP. `tests/test_base_api.py` comprueba esta base. Los archivos nuevos siguen sin seguimiento.
- `main.py` implementa GET colección y detalle (200), POST (201 con id generado), PUT completo (200 conservando id) y DELETE (204 sin cuerpo). Consulta, reemplazo y eliminación de un producto inexistente responden 404. POST y PUT comprueban 409 por nombre normalizado con strip/casefold y preparación, excluyendo en PUT el id actual. Las operaciones modifican el diccionario de memoria después de validar. No hay base de datos, login, pedidos, pagos, QR ni interfaz visual.
- `producto_con_id` utiliza `Producto.model_construct` exclusivamente con una entrada ya validada y un id controlado por la API; conserva el Decimal interno sin pasar de nuevo por el validador de números de entrada. Las rutas son asíncronas y no tienen esperas entre comprobar y modificar la memoria; el alcance sigue siendo un solo proceso.
- Decisiones: rechazar campos extra (incluido id en entrada); precio acepta únicamente int/float antes de convertir a Decimal, excluyendo bool y texto. Se comprueban decimales sin redondear ni contar ceros finales y se serializa como número JSON. Disponible usa StrictBool. Nombre y descripción se recortan; extensión de imagen literal en minúsculas. La memoria y el contador son de un único proceso y se pierden al reiniciar.

### Verificaciones ejecutadas y límites

- Se comprobaron las importaciones de FastAPI, Uvicorn, Pydantic, pytest y HTTPX dentro de `.venv`, con Python 3.14.4. Se repitió la comprobación al actualizar este documento: correcta.
- `.venv/bin/python -m pip --no-cache-dir check`: `No broken requirements found.` en esta revisión.
- En la preparación del entorno se verificó que Git ignora `.venv` y que el intérprete pertenece a ese entorno.
- La importación previa de `fastapi.testclient.TestClient` funcionó con un aviso de Starlette: su integración con HTTPX está obsoleta y recomienda `httpx2`. Revisar al preparar las pruebas.
- `probar_api.py` conserva SHA-256 `b257b622dbe127c35db8f419fdce3e1b1cd0755e0912d09a0d6cfcfafe80b5dd`; no se ha modificado para forzar resultados.
- Última ejecución de pruebas propias: `.venv/bin/python -m pytest -q`: **71 passed in 0.46s**. Se sustituyó `test_no_hay_rutas_de_productos`, obsoleta tras implementar el CRUD, por `test_estan_registradas_las_cinco_operaciones_de_productos`: verifica los cinco pares método/ruta esperados. El total sigue en 71 casos porque se reemplazó una prueba por otra. La suite cubre modelo, IDs, errores y registro de rutas, no el funcionamiento completo del CRUD.
- Reparto vigente: Aris y el asistente mantienen y ejecutan las pruebas propias del proyecto. El compañero se encarga únicamente de adaptar `prueba.json` a productos y ejecutar `probar_api.py`. Pendiente para nuestras pruebas propias: verificar CRUD, conflictos POST/PUT, PUT repetido, listado de no disponibles y errores específicos de endpoints.

- No se ejecutaron pruebas específicas del CRUD, ni el script del profesor, ni Uvicorn; no se generaron reportes ni capturas. `probar_api.py` y `prueba.json` se conservaron intactos. SHA-256 de prueba.json: `3abe5a98ed8f2d960cdcfa7f4bb452a56974c63fab0710e5b49f608ee9bc8500`.

Verificar siempre el estado real antes de actuar: `git status`, rama actual, archivos y configuración. No sobrescribir archivos ni asumir que las pruebas se ejecutaron o que existe un PR.

## Documentación y pendientes

- El documento descargado menciona `Ficha_original_Katea.md`, pero ese archivo no está en el repositorio inspeccionado. Su contenido y ubicación quedan sin verificar. Tampoco se localizó `api_equipos.py` en las carpetas revisadas (proyecto, Documents y Downloads); solicitar el original de Classroom si se necesita, sin renombrar PDFs.
- Revisar con Aris la implementación y ampliar nuestras pruebas propias de endpoints. El compañero se limita a las pruebas del profesor (preparación de prueba.json y ejecución de probar_api.py). Mantener la separación entre funcionalidad implementada y comportamiento verificado.
- Pendiente del compañero: preparar `prueba.json` para `/productos`, ejemplos válidos e inválidos y un reemplazo PUT completo. Conservar `probar_api.py` intacto. Las pruebas de endpoints y la ejecución del script siguen pendientes. Propuesta para compartir: versionar una configuración común con matrícula ilustrativa, revisar el diff de trabajo y staging de `prueba.json` antes de cada commit y excluir los cambios personales de matrícula. No hay un bloqueo automático configurado.
- La API ya existe. Pendiente iniciarla, ejecutar el script del profesor en otra terminal y comprobar además validaciones estrictas, conflictos 409, PUT repetido y listado de no disponibles. Guardar únicamente evidencias de ejecuciones reales.
- Git ignora `reporte_U3S2_*.txt` y `evidencias/`; `prueba.json` no está ignorado. Al ejecutar desde la raíz, el script genera allí `reporte_U3S2_<matrícula>.txt`. Copiar cada reporte real y sus capturas a `evidencias/<matrícula>/<fecha-hora>/`, y respaldarlos fuera del repositorio para la entrega; otra ejecución con la misma matrícula sobrescribe el reporte de la raíz. La configuración `prueba.json` se compartirá; la matrícula usada en cada ejecución y las evidencias corresponden a cada integrante.
- Las reglas, rutas y códigos del resto de recursos son un diseño inicial; verificar el estado real de la ficha corregida antes de darlo por hecho.
- Falta confirmar el avance de los bloques 01 y 02 y completar revisión, pruebas de endpoints y entrega. El PR sigue pendiente de autorización. No inventar resultados, salidas o reflexiones.

## Mantenimiento de la documentación

- Al terminar cada incremento, revisar primero código y Git. Actualizar este documento con lo implementado, decisiones relevantes, pruebas realmente ejecutadas y resultados, y pendientes.
- Corregir información desactualizada; no acumular transcripciones de conversaciones.
- README.md es la guía de presentación, instalación y uso. Revisarlo cuando cambien instalación, ejecución o pruebas. Este documento sirve para continuidad con el equipo y asistentes de IA.
- No hacer commit, push ni abrir pull request sin indicación expresa de Aris; las tareas de entrega descritas arriba son pendientes, no autorizaciones.

## Prompt para retomar

«Lee este archivo como contexto de Katea y revisa el estado actual de los archivos y Git antes de proponer cambios. Dime qué está hecho y qué falta respecto de la actividad vigente. Guíame por etapas y explícame lo que hagamos para que pueda aprender y presentar mi trabajo. No hagas commit, push ni abras un pull request sin que te lo indique.»
