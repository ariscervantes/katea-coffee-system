# Autenticación de Katea — U3S4, etapas 1, 2 y 3

## Alcance y recorrido

1. `POST /login` recibe JSON con dos textos: `usuario` y `clave`.
2. `RepositorioUsuarios.buscar` consulta MySQL con `%s` y valores separados.
3. bcrypt compara la clave recibida con el hash guardado. No se descifra el hash.
   Para un usuario inexistente también se hace una comparación bcrypt ficticia.
4. Una clave incorrecta o un usuario inexistente producen el mismo 401:
   `{"error": "Usuario o clave incorrectos", "detalles": []}`.
5. Si coincide, el login responde 200 con `access_token` y `token_type: bearer`.
   No incluye clave, hash ni el registro completo del usuario.
6. El cliente presenta `Authorization: Bearer <token>` en una ruta protegida.
   `usuario_actual` verifica firma, algoritmo HS256 y vencimiento; exige `sub`,
   `rol`, `iat` y `exp`, y valida la identidad y el rol. Los errores producen 401
   con el formato del proyecto y `WWW-Authenticate: Bearer`.

El JWT contiene `sub` (ID numérico del usuario representado como texto), `rol`
(`admin` o `cliente`), `iat` y `exp` (30 minutos desde la emisión).
Está firmado, no cifrado; no transporta contraseñas. La identidad y el rol se
leen de los datos firmados. No hay revocación anticipada ni consulta del rol en
cada petición: un cambio de rol requiere esperar el vencimiento del token ya
emitido. No se implementó registro público ni edición de usuarios en esta etapa.

## Persistencia y dependencias

`usuarios.py` crea, si falta, una tabla InnoDB con ID autoincremental, usuario
único y sensible a mayúsculas, hash bcrypt y rol ENUM. Los nombres se comparan
literalmente, sin recortar espacios ni cambiar mayúsculas en el login.
No se alteran tablas ni registros existentes. El arranque agrega únicamente la
creación de la tabla ausente; nunca crea cuentas. El esquema manual equivalente
está en `sql/esquema.sql`.

Se usan PyJWT 2.15.0 y bcrypt 5.0.0 directamente, sin Passlib. Se verifican en
Python 3.14 con las versiones FastAPI/Pydantic del proyecto. bcrypt usa sal
aleatoria y costo 12. La creación de claves admite entre 8 y 72 bytes UTF-8;
no se truncan claves. En login una clave que excede 72 bytes no autentica.

Referencias: [PyJWT](https://pyjwt.readthedocs.io/en/stable/usage.html) y
[bcrypt](https://github.com/pyca/bcrypt), además de `guia_u3s4.html` del profesor.

## Configuración sensible

Instalar dependencias con `python -m pip install -r requirements.txt`.
Configurar `JWT_SECRETO` con al menos 32 bytes aleatorios en el entorno o el
`.env` local ignorado. `.env.example` contiene solo un marcador que se rechaza.
No hay secreto predeterminado ni generación automática al arrancar: debe
conservarse el mismo secreto entre reinicios. Para generarlo sin mostrarlo en
terminal ni historial, se puede usar un gestor de secretos o una herramienta
local que lo escriba directamente en la configuración ignorada.

La configuración se exige al emitir o verificar tokens. Exportar OpenAPI y usar
productos no requiere secreto JWT; si falta, el login correcto no puede emitir
un token y devuelve un 500 genérico mediante el manejador del proyecto.

## Cuentas exclusivas de desarrollo

Confirmar que DB_HOST/DB_PORT/DB_NAME apuntan a una base de desarrollo.
Con `KATEA_ENTORNO=desarrollo` configurado explícitamente, ejecutar:

```bash
python scripts/crear_usuarios_desarrollo.py
```

El comando pide y confirma, sin eco, claves exclusivas de pruebas para
`dev_admin` (admin), `dev_cliente1` y `dev_cliente2` (cliente). No usar claves
personales. No pasar claves por argumentos, no guardarlas en archivos compartidos
ni publicar las respuestas del login. El comando guarda solamente hashes.

Las tres inserciones comparten una transacción: si un nombre ya existe, se
revierte el intento completo y no se actualizan ni borran cuentas anteriores.
El comando requiere desarrollo; en producción usar otro valor de KATEA_ENTORNO
u omitirlo. No está conectado al arranque de la API. El control de entorno evita
la ejecución accidental; no sustituye apuntar a la base correcta.

## OpenAPI y pruebas

`/login` documenta cuerpo JSON, respuesta y errores 400/401/422/500.
La dependencia `usuario_actual` utiliza `HTTPBearer` y añade el esquema
`BearerJWT` y el requisito de seguridad cuando se conecta a una ruta mediante
`Depends`. POST, PUT y DELETE de productos usan `exigir_admin`, que depende de
`usuario_actual`. Primero se verifica el JWT (401); después el rol (403 para
cliente); solo admin entra al CRUD. Los rechazos no llaman a las escrituras del
repositorio. Ambos GET de productos siguen públicos. El contrato publica
Authorize y documenta 401/403 con `RespuestaError`, conservando los otros errores.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
python -m pip check
python scripts/generar_contrato.py
```

Las pruebas usan repositorios y conexiones simulados, sin red ni MySQL real;
comprueban ambos roles, errores de login, firma alterada, vencimiento, algoritmo
no permitido, claims ausentes o inválidos, hashes, semilla y transacciones.
El generador solo escribe `docs/openapi.json`; no inicia la API ni crea tablas.
En la integración posterior se crearon cuentas solo en el MySQL exclusivo de
pruebas y se ejecutó U3S4 sin modificarlo: 19/20 y después 20/20. No se usó la
base habitual. Ver el contexto y las evidencias separadas por ronda.

## Pedidos y siguientes pasos

Las cuatro rutas de pedidos usan usuario_actual. El dueño al crear proviene del
ID verificado; el cliente lista, consulta y elimina solo propios, con filtros
SQL. Admin tiene acceso global explícito. Acceder a un pedido ajeno da 404.
Ver [PEDIDOS.md](PEDIDOS.md) para el contrato y las transacciones.

La integración MySQL aislada y las dos rondas U3S4 están comprobadas. Faltan
capturas personales, revisión por otro integrante y pruebas de concurrencia.
QR, pagos y caja quedan fuera de esta actividad.

La guía del equipo con configuración privada y dos corridas está en [U3S4.md](U3S4.md).
