"""Pedidos MySQL: transacción única y filtros de dueño ejecutados en SQL."""

from decimal import Decimal, localcontext

from basedatos import BaseDatos
from modelos_pedidos import DetallePedido, Pedido, PedidoEntrada

ESQUEMA_PEDIDOS = """
CREATE TABLE IF NOT EXISTS pedidos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT UNSIGNED NOT NULL,
    estado ENUM('pendiente') NOT NULL DEFAULT 'pendiente',
    total DECIMAL(65, 2) NOT NULL,
    KEY ix_pedidos_usuario (usuario_id),
    CONSTRAINT fk_pedidos_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""
ESQUEMA_DETALLES = """
CREATE TABLE IF NOT EXISTS pedido_detalles (
    pedido_id INT UNSIGNED NOT NULL,
    producto_id INT UNSIGNED NOT NULL,
    cantidad INT UNSIGNED NOT NULL,
    precio_unitario DECIMAL(65, 2) NOT NULL,
    PRIMARY KEY (pedido_id, producto_id),
    CONSTRAINT fk_detalles_pedido FOREIGN KEY (pedido_id)
        REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalles_producto FOREIGN KEY (producto_id)
        REFERENCES productos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""
MAX_IMPORTE = Decimal("9" * 63 + ".99")


class ProductoPedidoInexistente(Exception):
    pass


class ProductoNoDisponible(Exception):
    pass


class ImporteFueraDeRango(Exception):
    pass


class RepositorioPedidos:
    def __init__(self, base_datos: BaseDatos | None = None):
        self._base_datos = base_datos or BaseDatos()

    def inicializar(self) -> None:
        # Productos y usuarios deben inicializarse primero. DDL no implica semillas.
        with self._base_datos.conexion() as cursor:
            cursor.execute(ESQUEMA_PEDIDOS)
            cursor.execute(ESQUEMA_DETALLES)

    def crear(self, entrada: PedidoEntrada, usuario_id: int) -> Pedido:
        with self._base_datos.conexion() as cursor, localcontext() as contexto:
            contexto.prec = 90  # DECIMAL(65,2) no cabe en la precisión Decimal por defecto.
            detalles = []
            total = Decimal("0.00")
            # Mismo orden de bloqueo entre peticiones; bloquea también cambios/borrado del menú.
            for item in sorted(entrada.productos, key=lambda p: p.producto_id):
                cursor.execute(
                    "SELECT id, precio, disponible FROM productos WHERE id = %s FOR UPDATE",
                    (item.producto_id,),
                )
                producto = cursor.fetchone()
                if producto is None:
                    raise ProductoPedidoInexistente
                if not producto["disponible"]:
                    raise ProductoNoDisponible
                precio = Decimal(str(producto["precio"]))
                total += precio * item.cantidad
                if total > MAX_IMPORTE:
                    raise ImporteFueraDeRango
                detalles.append(DetallePedido(producto_id=item.producto_id, cantidad=item.cantidad, precio_unitario=precio))
            cursor.execute(
                "INSERT INTO pedidos (usuario_id, estado, total) VALUES (%s, %s, %s)",
                (usuario_id, "pendiente", total),
            )
            id = int(cursor.lastrowid)
            for detalle in detalles:
                cursor.execute(
                    "INSERT INTO pedido_detalles (pedido_id, producto_id, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)",
                    (id, detalle.producto_id, detalle.cantidad, detalle.precio_unitario),
                )
            pedido = Pedido(id=id, usuario_id=usuario_id, estado="pendiente", total=total, productos=detalles)
        # La conexión hace commit aquí; cualquier fallo anterior provoca rollback.
        return pedido

    def listar_propios(self, usuario_id: int) -> list[Pedido]:
        return self._listar(usuario_id)

    def listar_todos(self) -> list[Pedido]:
        """Acceso global: solo invocado por la ruta tras comprobar admin."""
        return self._listar(None)

    def _listar(self, usuario_id: int | None) -> list[Pedido]:
        consulta = "SELECT id, usuario_id, estado, total FROM pedidos"
        parametros = ()
        if usuario_id is not None:
            consulta += " WHERE usuario_id = %s"
            parametros = (usuario_id,)
        consulta += " ORDER BY id"
        with self._base_datos.conexion() as cursor:
            cursor.execute(consulta, parametros)
            filas = cursor.fetchall()
            return [self._desde_fila(cursor, fila, usuario_id) for fila in filas]

    def obtener_propio(self, id: int, usuario_id: int) -> Pedido | None:
        return self._obtener(id, usuario_id)

    def obtener_cualquiera(self, id: int) -> Pedido | None:
        return self._obtener(id, None)

    def _obtener(self, id: int, usuario_id: int | None) -> Pedido | None:
        consulta = "SELECT id, usuario_id, estado, total FROM pedidos WHERE id = %s"
        parametros = (id,)
        if usuario_id is not None:
            consulta += " AND usuario_id = %s"
            parametros += (usuario_id,)
        with self._base_datos.conexion() as cursor:
            cursor.execute(consulta, parametros)
            fila = cursor.fetchone()
            return self._desde_fila(cursor, fila, usuario_id) if fila else None

    @staticmethod
    def _desde_fila(cursor, fila: dict, usuario_id: int | None) -> Pedido:
        consulta = (
            "SELECT d.producto_id, d.cantidad, d.precio_unitario FROM pedido_detalles d "
            "JOIN pedidos p ON p.id = d.pedido_id WHERE d.pedido_id = %s"
        )
        parametros = (fila["id"],)
        if usuario_id is not None:
            consulta += " AND p.usuario_id = %s"
            parametros += (usuario_id,)
        consulta += " ORDER BY d.producto_id"
        cursor.execute(consulta, parametros)
        return Pedido(**fila, productos=[DetallePedido(**d) for d in cursor.fetchall()])

    def eliminar_propio(self, id: int, usuario_id: int) -> bool:
        return self._eliminar(id, usuario_id)

    def eliminar_cualquiera(self, id: int) -> bool:
        return self._eliminar(id, None)

    def _eliminar(self, id: int, usuario_id: int | None) -> bool:
        consulta = "DELETE FROM pedidos WHERE id = %s"
        parametros = (id,)
        if usuario_id is not None:
            consulta += " AND usuario_id = %s"
            parametros += (usuario_id,)
        with self._base_datos.conexion() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.rowcount > 0
