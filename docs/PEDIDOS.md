# Pedidos persistentes — U3S4, etapa 3

## Contrato

Todas las rutas exigen Bearer JWT válido mediante `usuario_actual`.

| Método | Ruta | Cliente | Admin | Éxito |
| --- | --- | --- | --- | --- |
| GET | `/pedidos` | Solo propios | Todos | 200, lista |
| GET | `/pedidos/{id}` | Solo propio | Cualquiera | 200 |
| POST | `/pedidos` | Crea a su nombre | Crea a su nombre | 201, pedido con ID |
| POST | `/pedidos/comentario` | Comenta como sí mismo | Comenta como sí mismo | 200, sentimiento y respuesta |
| DELETE | `/pedidos/{id}` | Solo propio | Cualquiera | 204 sin cuerpo |

Crear recibe este cuerpo (los IDs son ilustrativos, no semillas):

```json
{
  "productos": [
    {"producto_id": 1, "cantidad": 2},
    {"producto_id": 3, "cantidad": 1}
  ]
}
```

No admite campos extra, ni en el pedido ni en cada línea: se rechazan dueño,
usuario_id, estado, precio, precio_unitario o total enviados por el cliente.
La lista es obligatoria y no vacía. IDs y cantidades son enteros estrictos
positivos hasta 4294967295, según INT UNSIGNED de MySQL; no se aceptan booleanos,
textos ni fracciones. Un producto repetido da 422: debe aparecer una sola línea
con su cantidad. La respuesta ordena los detalles por producto_id.

El pedido responde con `id`, `usuario_id`, `estado: pendiente`, `total` y
`productos` (producto_id, cantidad, precio_unitario). Los importes de pedidos
se serializan como textos decimales con dos posiciones, por ejemplo `"20.80"`,
para conservar precisión. El contrato anterior de precio numérico en productos
no cambia. No se implementa actualización de pedidos o transición de estados.

## Errores

Se conserva `{"error": "...", "detalles": [...]}`.

| Caso | Código |
| --- | --- |
| Falta token o token inválido/vencido | 401, WWW-Authenticate: Bearer |
| JSON mal formado | 400 |
| Lista vacía, cantidad/ID inválido, línea duplicada o campo extra | 422 |
| Producto inexistente al crear | 422, Producto no encontrado |
| Producto no disponible al crear | 409, Producto no disponible |
| Total fuera de DECIMAL(65,2) | 422 |
| Pedido inexistente o ajeno | 404, Pedido no encontrado |
| Fallo inesperado de almacenamiento | 500 genérico y rollback |

La guía U3S4 exige obtener al dueño del token y usarlo en WHERE, con 404 para
objetos ajenos; conserva los códigos de validación/conflicto de la API. El 409
para indisponibilidad expresa un conflicto con el estado actual del catálogo.
El cliente recibe exactamente el mismo error para un pedido ajeno e inexistente.
Un cliente autenticado sí puede operar pedidos: no se le aplica exigir_admin.

## Comentarios con IA

`POST /pedidos/comentario` exige un JWT válido. El cuerpo solo admite
`comentario`, texto estricto de 2 a 300 caracteres tras recortar extremos; se
rechazan campos extra. La ruta usa la identidad del token (`id` y `rol`) y
consulta el nombre de usuario en `usuarios` para construir el contexto que se
envía a Gemini. El comentario del cliente se agrega al final de la instrucción.

La respuesta esperada de la IA es un objeto con `sentimiento` limitado a
positivo/neutral/negativo y `respuesta` no vacía. La API valida ese contenido,
recorta la respuesta a 200 caracteres y responde solo esos dos campos. Una
respuesta con otra forma produce 502; `GEMINI_API_KEY` ausente, 503; un timeout
de 5 segundos, 504. La llamada externa se reintenta una vez ante 5xx/429, pero no
ante 400, respuestas inválidas ni timeouts. La clave y el modelo se configuran en
el entorno y no se versionan.

## Relaciones e integridad

`usuarios` 1 → N `pedidos` 1 → N `pedido_detalles` N → 1 `productos`.

- pedidos: ID autoincremental, usuario_id con FK RESTRICT, estado y total.
- pedido_detalles: clave primaria (pedido_id, producto_id), cantidad y precio
  unitario histórico. FK a pedidos con CASCADE y a productos con RESTRICT.
- El CASCADE solo borra detalles al eliminar expresamente el pedido autorizado.
  Borrar un producto nunca elimina pedidos ni detalles.

`rutas_pedidos.py` toma el usuario_id de la identidad verificada. Para clientes
llama listar_propios/obtener_propio/eliminar_propio. Los filtros se aplican en
SQL con parámetros `%s`, incluso en la consulta de detalles mediante JOIN.
El admin usa explícitamente listar_todos/obtener_cualquiera/eliminar_cualquiera;
no puede seleccionar otro dueño en el cuerpo de creación.

`RepositorioPedidos.crear` abre una sola conexión/transacción. Lee y bloquea
cada producto con FOR UPDATE, en orden de ID, comprueba existencia y disponibilidad,
y toma el precio desde MySQL. Calcula cantidad por precio y el total usando
Decimal con precisión 90; comprueba el límite DECIMAL(65,2). Inserta cabecera y
detalles y solo entonces confirma. Cualquier excepción revierte la transacción.
No consulta precios a través de operaciones separadas del repositorio de productos.

Cada detalle conserva el precio de compra. Cambiar después precio, nombre o
disponibilidad del catálogo no recalcula el pedido. Conservar producto_id permite
seguir relacionándolo; no se guarda una copia histórica del nombre.

DELETE /productos/{id} ahora devuelve 409 si un detalle lo referencia, respaldado
por FK RESTRICT (MySQL 1451). Puede desactivarse mediante PUT para impedir nuevas
compras. Si se eliminan explícitamente todos los pedidos que lo referencian,
la restricción deja de impedir el borrado. No hay borrado lógico ni archivo de
pedidos: el DELETE de pedidos pedido en esta actividad es físico.

## Preparación del script de 20 pruebas

El script auténtico está compartido como `probar_api_U3S4.py`. Para preparar
cuentas, producto soporte y configuración personal, seguir [U3S4.md](U3S4.md).
Fue ejecutado sin cambios en la integración previa descrita al final. La prueba 20 envía
`propio.valido` tal como está, espera 201 y un ID, consulta con dos usuarios y
finalmente intenta borrar como dueño. No crea el producto requerido para ese pedido.

Para preparar las dos corridas de forma repetible, en una etapa autorizada:

1. Crear con admin un producto exclusivo, por ejemplo `U3S4 soporte pedidos`, con
   descripción válida, precio positivo, imagen `.png`, disponible=true y
   preparacion=no_aplica. Debe tener nombre distinto de los cuerpos valido/cambio
   del CRUD del profesor. Si ya existe, consultarlo y reutilizar su ID real tras
   comprobar su disponibilidad; no asumir que su ID es 1 o 2.
2. Mantener ese producto entre corridas, sin cambiar ID ni disponibilidad. No usar
   los productos que el propio script crea/reemplaza/borra en las pruebas 1–19.
3. En la configuración local futura, usar `propio.coleccion: /pedidos` y:
   `propio.valido: {"productos": [{"producto_id": ID_REAL, "cantidad": 1}]}`.
   Ese ID debe ser un número JSON. Configurar también auth con admin y dos clientes.
4. Conservar MySQL, configuración y archivo de estado U3S4 al reiniciar solo la API.
   El producto soporte sigue disponible para la prueba 20 de la segunda corrida.
   Al terminar, comprobar que el script eliminó sus pedidos antes de retirar el
   producto soporte. No borrar productos/datos ajenos al conjunto de pruebas.

Esta preparación ya se realizó en la base aislada de integración, con ID soporte 1
y una configuración privada ignorada; prueba.json quedó intacto. El estado U3S4
ya está ignorado. Las 20 pruebas no cubren todo el contrato de pedidos.

## Verificación y límite actual

Las pruebas propias ejecutan los repositorios reales contra un adaptador SQL en
memoria con transacciones y claves foráneas SQLite. Traducen `%s` a `?` y omiten
FOR UPDATE solo dentro del adaptador de pruebas; el código de producción sigue
usando PyMySQL. Comprueban filtros SQL, precios históricos, dos clientes/admin,
validación, 401, rollback con un fallo en el segundo detalle, límites monetarios,
FK de productos y el contrato exportado. El esquema MySQL se comprueba por separado.

El adaptador por sí solo no valida DDL MySQL ni bloqueos InnoDB. En la integración
posterior se comprobaron DDL, transacciones, restricciones y precios DECIMAL en
MySQL 8.0.46 aislado. Siguen pendientes pruebas de carreras concurrentes y carga.

La integración posterior inició la API solo contra una base nueva de pruebas.
El lifespan creó productos, usuarios, pedidos y detalles. No se aplicaron tablas
a la base habitual de Katea.

## Resultado de integración real

Suite propia: 202 aprobadas. U3S4: 19/20 con persistencia pendiente en primera
corrida, 20/20 tras reiniciar solo la API. MySQL, producto soporte, configuración
y estado permanecieron iguales; el registro de control se comprobó por SQL.
Se verificaron FK RESTRICT/CASCADE y rollback real mediante fallo controlado del
segundo detalle. Los reportes completos están separados por corrida en las evidencias locales
ignoradas de esa integración. No se generaron capturas personales.

La referencia inexistente dentro de PedidoEntrada da 422 por indicación del
profesor; el 404 se reserva para la consulta/borrado de pedidos ajenos o inexistentes.
