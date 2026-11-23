# ADR-001: Persistencia en MySQL 8 con PyMySQL

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Decisores:** Equipo Katea
- **Ámbito:** Productos, usuarios, pedidos y detalles de pedido

## Contexto

Katea debe conservar productos, usuarios y pedidos entre reinicios de la API. El
proyecto es académico, usa FastAPI con Pydantic y MySQL 8 está disponible tanto
en el entorno del curso como en el `compose.yaml` del repositorio. La base debe
garantizar integridad referencial, transacciones, bloqueos de filas y aritmética
decimal exacta para los importes.

El equipo es pequeño, no había una capa de persistencia previa y se buscaba que
el SQL fuera visible y comprensible para revisar el comportamiento de la base,
sin introducir un ORM ni una herramienta de migraciones en esta etapa.

## Decisión

Usar **MySQL 8** como única base de datos y **PyMySQL** como driver, con SQL
explícito y una capa de repositorios:

- Las consultas usan marcadores `%s` y parámetros separados; nunca se concatena
  información del cliente al texto del SQL.
- `basedatos.py` define `BaseDatos` y `ConfiguracionBD`. Cada operación abre una
  conexión con `autocommit=False`; la conexión hace `commit` al terminar, hace
  `rollback` ante cualquier excepción y siempre se cierra.
- Los repositorios (`RepositorioProductos`, `RepositorioUsuarios` y
  `RepositorioPedidos`) encapsulan el SQL y los modelos de Pydantic quedan en
  `modelos.py` y `modelos_pedidos.py`.
- El esquema se crea con `CREATE TABLE IF NOT EXISTS` al arrancar la API para las
  tablas ausentes. La versión manual equivalente está en `sql/esquema.sql`.
- Los importes usan `DECIMAL(65, 2)`. Los pedidos guardan el precio unitario
  histórico y calculan el total con `Decimal` y precisión local de 90 dígitos.
- La creación de un pedido bloquea los productos con `SELECT ... FOR UPDATE` en
  orden de ID y guarda cabecera y detalles en una sola transacción.
- Las claves foráneas usan `RESTRICT` para usuarios y productos, y `CASCADE` para
  los detalles cuando se elimina un pedido.

No se usa ORM ni un sistema de migraciones en esta versión. La base y el usuario
de MySQL deben existir antes de arrancar; la API solo crea las tablas.

## Alternativas consideradas

### SQLite o una base en memoria

Es más simple para pruebas y no requiere un servidor, pero no reproduce el
comportamiento de MySQL que interesa en la actividad: bloqueos, restricciones de
clave foránea, tipos `DECIMAL`, concurrencia y volumen de Docker. Se conserva
como apoyo en pruebas mediante adaptadores y dobles, no como base de la API.

### SQLAlchemy u otro ORM

Reduciría el SQL manual y facilitaría el cambio de motor, pero añade una capa de
abstracción y dependencias que el equipo no necesitaba para tres entidades. El
objetivo era revisar y explicar consultas, transacciones y bloqueos concretos.

### `mysqlclient` u otro driver

`mysqlclient` requiere compilación y dependencias nativas. PyMySQL es Python
puro, se instala con `requirements.txt` sin pasos adicionales y ofrece cursores
de diccionario suficientes para el proyecto.

## Consecuencias

### Positivas

- Control explícito de transacciones, rollback, bloqueos y claves foráneas.
- SQL legible y verificable en los repositorios y en el esquema manual.
- El precio histórico y el total decimal no dependen de conversiones flotantes.
- El mismo MySQL puede levantarse con Compose para todos los integrantes.

### Negativas y riesgos

- El SQL y el esquema se mantienen a mano; no hay migraciones automáticas.
- El SQL está acoplado a MySQL, en particular `%s`, `FOR UPDATE` y los tipos
  `ENUM`, `DECIMAL` y `INT UNSIGNED`.
- Abrir una conexión por operación es adecuado para la escala académica, pero no
  es un pool de conexiones de producción.
- MySQL debe estar disponible al arrancar. Cambiar una contraseña en `.env` no
  actualiza un volumen de Compose ya inicializado.
- Los errores de infraestructura terminan en un 500 genérico; el detalle queda en
  el log y no se expone al cliente.

## Referencias

- [basedatos.py](../../basedatos.py): configuración, conexión, transacciones y
  creación del esquema.
- [repositorio.py](../../repositorio.py) y
  [repositorio_pedidos.py](../../repositorio_pedidos.py): SQL de productos y
  pedidos.
- [sql/esquema.sql](../../sql/esquema.sql): esquema manual equivalente.
- [PEDIDOS.md](../PEDIDOS.md): reglas de pedidos y transacciones.
- [CONTEXTO_PROYECTO.md](../CONTEXTO_PROYECTO.md): alcance y resultados previos.
