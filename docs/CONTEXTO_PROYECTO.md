# Contexto de Katea — actualizado 2026-11-11

## Proyecto y trabajo en equipo

Katea es un menú digital y sistema de pedidos académico. Equipo: Arisbeth
Cervantes, Diego Verduzco y Lorenzo Chávez. Repositorio:
https://github.com/ariscervantes/katea-coffee-system.

Trabajar por etapas y revisar Git antes de cambiar archivos. No mostrar .env,
claves, hashes privados ni tokens. Mantener la matrícula/configuración personal
y evidencias fuera de los commits. Usar la identidad Git existente, sin agregar
autores ni coautores. Commit y push de login-y-roles están autorizados para esta
revisión; no abrir, aprobar ni fusionar el PR todavía.

## Base y alcance

Rama login-y-roles basada en main 0b09d9a. El PR #2 de persistencia y contrato
está integrado. Antes de publicar se consultaron las referencias de origin:
main seguía en esa base y no existía login-y-roles remoto. Comprobar el estado
actual de Git: este registro no sustituye una consulta nueva.

FastAPI/Pydantic, MySQL 8, PyMySQL; SQL parametrizado con %s. CRUD de productos,
usuarios con bcrypt y roles admin/cliente, login JSON, JWT HS256 con expiración
de 30 minutos y pedidos persistentes con control de dueño. No hay QR, pagos,
caja, registro público ni edición de usuarios.

## Implementación y decisiones

- main.py crea la app con repositorios inyectables; al iniciar crea tablas
  ausentes en orden: productos, usuarios, pedidos y detalles. No crea cuentas.
- basedatos.py obtiene configuración de entorno/.env y administra conexión,
  commit, rollback y cierre. La base MySQL debe existir antes de arrancar.
- autenticacion.py exige sub, rol, iat y exp, firma válida y algoritmo HS256.
  JWT_SECRETO debe ser aleatorio y tener al menos 32 bytes, sin valor por defecto.
  Login JSON con usuario/clave devuelve access_token/token_type; credenciales
  incorrectas producen el mismo 401 sin exponer clave ni hash.
- Usuarios: ID autoincremental, nombre único sensible a mayúsculas, hash bcrypt
  y rol. bcrypt 5.0.0 directo, costo 12 y sal aleatoria; claves nuevas de 8–72
  bytes UTF-8 sin truncar. PyJWT 2.15.0; comprobado en Python 3.14.4.
- GET de productos públicos; POST/PUT/DELETE requieren exigir_admin, que depende
  de usuario_actual. 401 para token ausente/inválido/vencido; 403 para cliente.
- Pedidos exige sesión. Dueño desde identidad; se rechaza si viene en el cuerpo.
  Cliente lista/consulta/elimina solo propios mediante WHERE usuario_id = %s;
  admin usa métodos globales explícitos. Ajeno e inexistente dan el mismo 404.
- Entrada: productos no vacíos con producto_id y cantidad enteros estrictos
  positivos hasta 4294967295; sin repetidos, precios, total, estado ni extras.
  Lista/cantidad inválidas y producto inexistente en cuerpo dan 422; producto
  no disponible da 409.
- Crear pedido bloquea productos con FOR UPDATE en orden de ID, toma sus precios,
  calcula con Decimal precisión 90 y comprueba DECIMAL(65,2). Guarda cabecera y
  detalles en una transacción con estado pendiente y precios históricos.
  Importes JSON de pedidos son textos con dos decimales; productos sigue numérico.
- FK usuario→pedido RESTRICT, producto→detalle RESTRICT y pedido→detalle CASCADE.
  DELETE de producto referenciado da 409 (MySQL 1451); no borra pedidos.
- Productos conserva validaciones y normalización previas de README. No se
  amplió la precisión arbitraria de lectura JSON ni cambió la validación de imagen.
- OpenAPI documenta Bearer/Authorize, éxitos y errores uniformes RespuestaError.
  Exportar con scripts/generar_contrato.py; no necesita iniciar servicios.

## Preparación para cada integrante

Seguir docs/U3S4.md: entorno virtual y .env privado, MySQL propio, semilla manual
scripts/crear_usuarios_desarrollo.py con KATEA_ENTORNO=desarrollo, API en terminal,
producto soporte disponible y copia privada prueba_U3S4.local.json con matrícula
propia y las tres cuentas. No sobrescribir prueba.json personal.

probar_api_U3S4.py es copia byte por byte del script versión 3 del profesor:
SHA-256 929ce89653d01c8cb18b506e6f5241a76b91344be83e987e1a51ac190eb738c5.
Se comprobó contra el original de Downloads y clase-s4.zip. Acepta la ruta de
configuración en sys.argv[1]. Los scripts anteriores se conservan sin cambios.

La prueba 20 necesita producto disponible previo, distinto de los registros CRUD
del script. Conservar su ID, base, configuración, cwd y estado entre corridas;
respaldar salida y reporte antes de repetir, reiniciando solo la API. El script
no demuestra por sí mismo que se haya reiniciado el proceso.

.env, prueba_U3S4.local.json, entorno virtual, evidencias/reportes y estado de
persistencia U3S3/U3S4 están ignorados. No versionar contraseñas ni resultados
personales. La plantilla compartida tiene únicamente marcadores de configuración.

## Resultados previos registrados

- Suite propia: 202 aprobadas en la integración previa. Las pruebas aíslan HTTP
  y SQL en memoria; no conectan a MySQL real ni prueban su bloqueo concurrente.
- Integración previa MySQL 8.0.46 en contenedor/base/volumen nuevos y exclusivos,
  sin modificar la base habitual. Cuatro tablas InnoDB y tres FK comprobadas.
- Login y hashes, permisos de productos, propiedad y admin en pedidos, DECIMAL
  exacto/histórico, 422 para referencia inexistente en cuerpo y 409 de conflicto.
  RESTRICT de producto/usuario y CASCADE de detalles verificados.
- Un trigger temporal falló en el segundo detalle: 500 genérico y rollback real
  sin cabecera ni detalles incompletos. El trigger se retiró después.
- U3S4: 19/20 primero con persistencia pendiente; 20/20 tras reiniciar solo API.
  Se comprobaron PIDs distintos y registro de control en SQL, conservando MySQL,
  producto soporte y hashes de configuración/estado. Evidencias personales ignoradas.

Estos resultados son históricos; no atribuirlos a una nueva ejecución de otro
integrante. Consultar la salida realmente obtenida en cada revisión. La API y
contenedores de pruebas pueden haber cambiado de estado: no asumir que estén
activos ni compartir sus credenciales.

## Pendientes

Revisión por otro integrante y capturas personales, luego PR cuando se autorice.
No se han hecho pruebas de carreras concurrentes/carga. No hay revocación
anticipada de JWT: cambios de rol se reflejan al emitir un token nuevo y los ya
emitidos conservan su vigencia. QR, pagos y caja quedan para otra actividad.

## Revisión para publicación

Se ejecutó nuevamente la suite propia: 202 aprobadas en 13.62 s; pip check
correcto y git diff --check sin errores. Se comprobó el contrato exportado en la
suite. No se repitieron las corridas U3S4 ni la integración MySQL en esta revisión;
se conservan como resultados previos registrados. Script U3S4 contrastado contra
original y ZIP; versiones anteriores y configuración personal intactas.
