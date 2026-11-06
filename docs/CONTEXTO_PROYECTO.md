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
4. Implementar cinco endpoints: GET /productos, GET /productos/{id}, POST /productos, PUT /productos/{id} y DELETE /productos/{id}. Almacenar los datos en MySQL.
5. Usar errores con formato {"error": "...", "detalles": [...]}; seguir la guía de clase sobre 400, 404, 409 y 422.
6. Adaptar `prueba.json`, configurar la matrícula individual y ejecutar `python probar_api.py` con la API en marcha; objetivo: 11 de 11, ya obtenido por Aris y nuevamente en la verificación aislada del asistente. Revisar también las reglas de validación y 409, que no están todas cubiertas por ese script.
7. Trabajar en una rama y abrir un pull request que describa qué cambia y cómo se probó, incluyendo la línea RESULTADO. Otro integrante debe revisarlo según la lista de la diapositiva 18.
8. Completar las evidencias y reflexión de la actividad. Cada integrante entrega su propio PDF, con reporte y captura reales.

## Reglas de productos acordadas para la práctica

La API genera el id. El cliente no lo proporciona al crear.

- **nombre:** texto obligatorio de 2 a 80 caracteres tras quitar espacios al inicio y al final.
- **descripcion:** texto obligatorio de 5 a 200 caracteres tras quitar espacios al inicio y al final.
- **precio:** número obligatorio mayor que cero, con máximo dos decimales, sin aceptar textos ni booleanos. Se conserva la validación original int/float a Decimal y se permiten ceros finales: 25.000 equivale a 25 y 25.120 a 25.12. No se preserva precisión decimal desde la lectura JSON; los casos de alta precisión reportados pueden redondearse antes de validar. Esa corrección quedó fuera del alcance por decisión de Aris.
- **imagen_url:** texto obligatorio no vacío que termina literalmente en .jpg, .jpeg, .png o .webp. Debe tener nombre no vacío antes de la extensión en el último segmento de la ruta y no contener saltos de línea CR/LF. Se conserva el rechazo original de extensiones mayúsculas y parámetros después de la extensión. No se descarga ni comprueba existencia, contenido o validez completa de la URL.
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

## Estado de la corrección local (2026-11-04)

- Al comenzar, el único cambio local era la matrícula de `prueba.json`: de `20205116` a `20204413`. Se conserva intacto. No se consultó el remoto ni se creó commit, push, aprobación o merge.
- CRUD con almacenamiento en MySQL. La tabla se crea al iniciar si no existe y los datos e IDs se conservan al reiniciar. No hay login, pedidos, pagos, QR ni interfaz visual.
- Se retiraron `rutas.py`, su registro en `main.py`, la aceptación de Decimal como entrada y las pruebas exclusivas de precisión. `main.py` vuelve a coincidir con la versión previa a la revisión. El Decimal interno y el serializador originales se conservan.
- La corrección de imagen se limita a extensión literal, nombre de archivo no vacío y rechazo de CR/LF. Se retiraron urlsplit, decodificación porcentual, restricciones de esquema/host y aceptación de mayúsculas o parámetros.
- Continúan los campos obligatorios y el rechazo de campos extra, incluido id. Nombre y descripción se recortan. Disponible usa StrictBool; preparación tiene tres valores. Los duplicados comparan nombre con strip/casefold y preparación; PUT excluye el propio ID.

### Migración a MySQL (2026-11-06)

- Se eliminó `memoria.py`. La tabla `productos` vive en MySQL y se crea al iniciar si no existe; el ID es `AUTO_INCREMENT`.
- `basedatos.py` carga `.env` con `python-dotenv`, valida `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`, y abre una conexión por operación con transacción.
- `repositorio.py` contiene todas las consultas. Usa marcadores `%s` de MySQL y parámetros separados; no concatena datos del cliente al texto del SQL.
- La pareja nombre/preparación tiene una restricción única en MySQL. La comparación normaliza nombre con `strip().casefold()` y se guarda en una columna con colación binaria. Si dos peticiones compiten, la base devuelve el conflicto y la API responde 409.
- `.env.example` contiene solo datos de ejemplo. `sql/esquema.sql` permite crear la tabla manualmente.
- Las respuestas de las cinco rutas declaran sus códigos con `responses`. El contrato exportado se genera con `python scripts/generar_contrato.py` en `docs/openapi.json`; el resumen está en `docs/CONTRATO_API.md`. Swagger UI sigue disponible en `/docs`.

### Verificación real de esta corrección

- `.venv/bin/python -m pytest -q -p no:cacheprovider`, con bytecode desactivado, tras reducir el alcance: **90 passed**. Se conservan las pruebas originales, se añaden casos de imagen en modelo y POST/PUT, se conserva la regresión general de errores, duplicados, CRUD y PUT repetido, y se añade una comprobación de los códigos documentados en el contrato. Los errores comprobados usan 400/404/409/422 y formato uniforme; no se observaron respuestas 500. Las pruebas HTTP usan un repositorio falso inyectado; la aplicación real usa MySQL.
- Aris había ejecutado personalmente `probar_api.py` con matrícula `20204413`: **11 de 11**. Ese resultado es previo y pertenece a su ejecución.
- En la revisión anterior, antes de reducir el alcance, el asistente ejecutó el script original contra Uvicorn aislado en `http://127.0.0.1:37383`: **RESULTADO: 11 de 11**, salida 0. Se utilizó una copia temporal de `prueba.json` con solo la base cambiada al puerto temporal. Esa instancia se detuvo al terminar y no se sobrescribió la evidencia anterior.
- En la verificación de la migración a MySQL, el asistente levantó MySQL 8.4 y Uvicorn en `127.0.0.1:18000` con una base temporal. `probar_api.py` obtuvo **11 de 11** y se detuvieron ambos servicios después. Se usó una copia temporal de la configuración; no se modificaron `prueba.json`, `probar_api.py` ni sus reportes. Es una ejecución del asistente, no una evidencia personal.
- SHA-256 de `probar_api.py`, sin cambios: `b257b622dbe127c35db8f419fdce3e1b1cd0755e0912d09a0d6cfcfafe80b5dd`.
- `prueba.json` tiene cambios locales previos de matrícula y una clave `openapi`; revisar `git diff -- prueba.json` antes de cualquier commit.

## Pendientes y límites

- Revisar el diff antes de autorizar cualquier commit, push, aprobación o merge. No se ha verificado el estado remoto del PR.
- Conservar evidencias personales reales y respaldarlas; no atribuir la ejecución del asistente a Aris. Git ignora reportes y `evidencias/`, pero no la matrícula local en `prueba.json`.
- El documento original menciona `Ficha_original_Katea.md`, que no se localizó en el repositorio. Las reglas usadas aquí son las indicadas y aclaradas por Aris en la conversación.
- El almacenamiento usa MySQL y persiste entre reinicios. Las pruebas cubren los casos descritos, sin afirmar ausencia de fallos para cualquier entrada posible.
- Falta completar la revisión humana y las evidencias/reflexión de la actividad. No inventar resultados ni capturas.

## Mantenimiento de la documentación

- Al terminar cada incremento, revisar primero código y Git. Actualizar este documento con lo implementado, decisiones relevantes, pruebas realmente ejecutadas y resultados, y pendientes.
- Corregir información desactualizada; no acumular transcripciones de conversaciones.
- README.md es la guía de presentación, instalación y uso. Revisarlo cuando cambien instalación, ejecución o pruebas. Este documento sirve para continuidad con el equipo y asistentes de IA.
- No hacer commit, push ni abrir pull request sin indicación expresa de Aris; las tareas de entrega descritas arriba son pendientes, no autorizaciones.

## Prompt para retomar

«Lee este archivo como contexto de Katea y revisa el estado actual de los archivos y Git antes de proponer cambios. Dime qué está hecho y qué falta respecto de la actividad vigente. Guíame por etapas y explícame lo que hagamos para que pueda aprender y presentar mi trabajo. No hagas commit, push ni abras un pull request sin que te lo indique.»
