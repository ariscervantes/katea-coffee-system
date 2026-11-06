# Contexto de Katea — actualizado 2026-11-06

## Proyecto y equipo

Katea es un proyecto académico de cafetería, Programación Distribuida, Universidad de Colima. Equipo: Arisbeth Cervantes (20204413), Diego Verduzco (20205116) y Lorenzo Chávez (20209634). Repositorio: https://github.com/ariscervantes/katea-coffee-system.

Trabajo por etapas, con explicaciones claras. No hacer commit ni push hasta indicación expresa. No mostrar contraseñas ni contenido de .env. Conservar la matrícula local de Aris y revisar su diff antes de cualquier commit.

## Estado real de integración

- Rama local `persistencia-y-contrato`, siguiendo `origin/persistencia-y-contrato`, base e2a79f7 de Diego. El CRUD anterior está integrado en origin/main mediante PR #1, commit 946ac53. No se creó actividad/persistencia-katea.
- Se aprovecharon basedatos.py, repositorio.py y sql/esquema.sql de Diego sin modificarlos. Se integraron main.py, modelos.py y errores.py exclusivamente desde Aris.zip. No se usó Lorenzo.zip.
- Se mantienen MySQL, PyMySQL y consultas con %s y valores separados; no se usa mysql-connector-python ni marcadores ?. La API inicializa la tabla al arrancar, abre una conexión por operación y hace commit/rollback y cierre.
- Modelo de error documentado y precio de entrada anunciado como número en OpenAPI. Se mantienen las reglas del CRUD, incluido strip/casefold para duplicados. El precio conserva la lectura JSON normal previa a Decimal; no se corrigió precisión arbitraria fuera del alcance.
- Se conserva probar_api.py (11 verificaciones, SHA256 b257b622dbe127c35db8f419fdce3e1b1cd0755e0912d09a0d6cfcfafe80b5dd). Se agregó probar_api_U3S3.py (15), idéntico al ZIP de Aris. prueba.json añade openapi en la configuración compartida; la matrícula 20204413 se conserva como cambio local fuera del commit.
- Las pruebas propias usan un repositorio aislado e inyectado; no importan memoria.py. Se retiró la prueba del generador en memoria y se añadió contrato y ciclo de vida. Último resultado: 90 aprobadas en 1.04 s, sin advertencias; pip check correcto.

## MySQL dedicado autorizado por Aris

- compose.yaml crea el proyecto katea, contenedor katea-mysql-1, imagen mysql:8.0 (servidor comprobado 8.0.46), volumen katea_mysql_data y puerto 127.0.0.1:13306.
- Base katea y usuario propio katea_app. Credenciales aleatorias guardadas en .env con permisos 600 e ignoradas por Git; .env.example solo contiene plantilla. No se modificaron los contenedores preexistentes.
- MySQL permanece activo. La API temporal de verificación en 127.0.0.1:18000 fue detenida.

## Resultados comprobados

Ejecución del asistente el 2026-11-06 con matrícula 20204413, sin atribuirla a Aris:

- Primera ronda U3S3: 14/15, persistencia pendiente.
- Se detuvo el proceso de API PID 50176 y se inició otro PID 50204. MySQL permaneció activo. Se comprobó directamente en SQL la existencia del registro de control tras el reinicio.
- Segunda ronda: 15/15. Línea real: U3S3;20204413;http://127.0.0.1:18000/productos;111111111111111;E3B12A3F.
- Se comprobaron además datos con comillas y SQL aparente guardados literalmente, recuperación de DECIMAL y booleanos, restricción única, reemplazo repetido, conflicto al reemplazar y rollback. Los registros adicionales fueron eliminados.
- Evidencias separadas: evidencias/20204413/20261106-151600-persistencia-mysql/. Incluyen ambos reportes, configuración temporal, registros de API, constancia del reinicio y comprobación SQL. No se generaron capturas. No se sobrescribió evidencia de U3S2.

## Pendientes

Aris autorizó revisar, preparar, hacer commit y push en esta rama compartida, conservando su matrícula fuera del commit. No abrir ni aprobar el PR hasta indicación expresa. Las evidencias están ignoradas: respaldarlas fuera del repositorio si se necesitan para entrega. Aris confirmó su segunda corrida personal tras reiniciar la API: 15/15. Se revisó el reporte local evidencias/20204413/reporte-ronda-2.txt, con base en el puerto 8000; no se versiona ese archivo.

README describe la instalación, operaciones y ejecución. No hay contratos exportados ni scripts de exportación adicionales. Pedidos, pagos, QR, login y frontend siguen fuera del alcance. Las pruebas cubren los casos ejecutados; no garantizan cualquier entrada posible. El esquema DECIMAL tiene un límite finito y el precio del modelo no declara un máximo; no se amplió esta actividad para cambiar esa regla.
