# Katea — API de productos y pedidos

Proyecto académico con FastAPI, Pydantic, MySQL 8 y PyMySQL. Incluye login JSON,
roles y pedidos con control de dueño. QR, pagos y caja quedan para otra etapa.

## Preparación

La guía reproducible para el equipo está en [docs/U3S4.md](docs/U3S4.md): instala
dependencias, configura un MySQL de desarrollo, crea cuentas y ejecuta dos
corridas con la matrícula de cada integrante.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

Configurar DB_HOST, DB_PORT, DB_USER, DB_PASSWORD y DB_NAME en el entorno o en
`.env` local, tomando `.env.example` como plantilla. JWT_SECRETO debe ser aleatorio,
de al menos 32 bytes, y conservarse entre reinicios; no hay secreto predeterminado.
No versionar `.env` ni credenciales. La guía incluye generación sin imprimirlo.

`compose.yaml` ofrece MySQL 8, puerto local 13306, proyecto Docker katea y volumen
katea_mysql_data. Completar también MYSQL_ROOT_PASSWORD antes de iniciarlo:

```bash
docker compose up -d --wait mysql
python scripts/crear_usuarios_desarrollo.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

El comando de cuentas requiere KATEA_ENTORNO=desarrollo y pide claves sin eco
para dev_admin, dev_cliente1 y dev_cliente2. Las inserta juntas con hashes bcrypt;
si alguna existe, revierte sin reemplazar datos. No hay cuentas automáticas.

MySQL crea la base/usuario de Compose solo al inicializar un volumen nuevo;
cambiar `.env` después no modifica claves existentes. No eliminar volúmenes
para cambiar una contraseña. Al arrancar, la API crea tablas ausentes, no la base.
Las conexiones usan commit/rollback/cierre y SQL con `%s` y valores separados.

## Rutas y permisos

| Operación | Acceso | Éxito |
| --- | --- | --- |
| POST `/login` | Público, credenciales JSON | 200, access_token y token_type |
| GET `/productos` | Público, incluye no disponibles | 200 |
| GET `/productos/{id}` | Público | 200 |
| POST `/productos` | Admin | 201 |
| PUT `/productos/{id}` | Admin, reemplazo completo | 200 |
| DELETE `/productos/{id}` | Admin | 204 sin cuerpo |
| GET `/pedidos` | Cliente: propios; admin: todos | 200 |
| GET `/pedidos/{id}` | Cliente: propio; admin: cualquiera | 200 |
| POST `/pedidos` | Autenticado; dueño desde token | 201 |
| DELETE `/pedidos/{id}` | Cliente: propio; admin: cualquiera | 204 sin cuerpo |

JWT HS256 con identidad, rol y vencimiento de 30 minutos; contraseñas con bcrypt,
sal aleatoria y costo 12. Token ausente/inválido/vencido: 401 con
WWW-Authenticate Bearer. Cliente que escribe productos: 403. Pedido ajeno o
inexistente: el mismo 404. El token no contiene contraseñas ni hashes.

## Reglas de datos

Productos exige seis campos y rechaza extras, incluido id. Nombre: 2–80 y
descripción: 5–200 caracteres tras recortar extremos. Precio: número positivo,
sin textos/booleanos y máximo dos decimales. Se convierte a Decimal después de
la lectura JSON normal, sin preservar precisión arbitraria previa a validar.
Imagen: sufijo literal .jpg/.jpeg/.png/.webp, nombre no vacío y sin CR/LF; no se
descarga. Disponible: booleano estricto. Preparación: frio/caliente/no_aplica.
Duplicados: nombre normalizado con strip/casefold y preparación; conflicto 409.
PUT excluye al propio producto y puede repetirse sin cambiar el resultado.

Pedidos recibe productos no vacíos con producto_id y cantidad entera positiva;
rechaza dueño, precios, total, estado y otros campos extra. Lee precios y
disponibilidad desde MySQL; guarda precio unitario histórico y total en una
transacción. Un fallo revierte cabecera y detalles. Los importes de pedidos se
devuelven como textos con dos decimales; productos conserva precio numérico.
Lista vacía, cantidad inválida o producto inexistente en el cuerpo: 422.
Producto no disponible: 409. Borrar un producto referenciado por pedidos: 409;
puede desactivarse para nuevas compras. Borrar expresamente un pedido autorizado
elimina sus detalles. Ver [docs/PEDIDOS.md](docs/PEDIDOS.md).

Errores uniformes: `{"error": "...", "detalles": [...]}`. JSON mal formado: 400;
datos inválidos: 422; fallo interno: 500 genérico.

## Contrato y pruebas

Swagger: `/docs`, ReDoc: `/redoc`, esquema: `/openapi.json`. Authorize permite
usar Bearer en las rutas protegidas. Contrato exportado: `docs/openapi.json`.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
python scripts/generar_contrato.py
```

La suite propia usa repositorios aislados y un adaptador SQL en memoria, sin
conectar a MySQL real. Resultado previo registrado: 202 aprobadas.
La integración previa con MySQL 8.0.46 aislado comprobó hashes/login, permisos,
propiedad, DECIMAL histórico, FK RESTRICT/CASCADE y rollback ante fallo de detalle.
U3S4 obtuvo 19/20 con persistencia pendiente y 20/20 tras reiniciar solo la API.
No son resultados de una nueva ejecución personal de cada integrante.
Faltan pruebas de concurrencia y carga.

`probar_api_U3S4.py` es la copia auténtica de las 20 pruebas, sin cambios y sin
sobrescribir probar_api.py/probar_api_U3S3.py anteriores. Usar una copia personal
ignorada de `prueba_U3S4.example.json`; instrucciones completas de cuentas,
producto soporte, matrícula, reinicio y respaldo por ronda en
[docs/U3S4.md](docs/U3S4.md). Los scripts U3S3 no hacen login y sus resultados
anteriores son históricos; no validan las escrituras protegidas actuales.

Configuración personal, reportes, capturas, evidencias y estado temporal quedan
fuera de Git. Conservar los cambios personales de prueba.json sin incluirlos en
commits. El contexto del equipo está en [docs/CONTEXTO_PROYECTO.md](docs/CONTEXTO_PROYECTO.md).
