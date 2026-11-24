"""Reglas de negocio de pedidos: pieza 7 (regla de negocio fuera de HTTP) del mapa.

Un pedido solo lleva productos existentes y disponibles (si no, 409), cada uno una vez;
congela el precio de compra y suma el total con Decimal sin pasar MAX_IMPORTE.
Admin ve y borra cualquier pedido; un cliente, solo los suyos. No conoce HTTP ni SQL.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Solo para anotaciones: evita importar modelos y repositorio en ejecución.
    from app.modelos.pedidos import Pedido, PedidoEntrada
    from app.repositorios.pedidos import RepositorioPedidos


MAX_IMPORTE = Decimal("9" * 63 + ".99")  # Lo máximo que cabe en DECIMAL(65, 2).


class ProductoPedidoInexistente(Exception):
    """El producto pedido no existe en el catálogo."""


class ProductoNoDisponible(Exception):
    """El producto existe pero no está disponible para nuevas compras."""


class ImporteFueraDeRango(Exception):
    """El total del pedido supera MAX_IMPORTE."""


class ProductoRepetido(ValueError):
    """Un mismo producto aparece dos veces en el pedido.

    Hereda de ValueError para que el validador de Pydantic la convierta en 422.
    """


def verificar_productos_unicos(ids: list[int]) -> None:
    if len(ids) != len(set(ids)):
        raise ProductoRepetido("Cada producto debe aparecer una sola vez; usa cantidad")


def precio_de_compra(producto: dict | None) -> Decimal:
    """Recibe la fila leída del catálogo y devuelve el precio que se congela en el pedido."""
    if producto is None:
        raise ProductoPedidoInexistente
    if not producto["disponible"]:
        raise ProductoNoDisponible
    return Decimal(str(producto["precio"]))


def sumar_al_total(total: Decimal, precio: Decimal, cantidad: int) -> Decimal:
    """Suma cantidad × precio al total sin redondeos binarios y sin pasar el tope."""
    with localcontext() as contexto:
        contexto.prec = 90  # DECIMAL(65,2) no cabe en la precisión Decimal por defecto.
        nuevo_total = total + precio * cantidad
    if nuevo_total > MAX_IMPORTE:
        raise ImporteFueraDeRango
    return nuevo_total


class PedidoNoEncontrado(Exception):
    """El pedido no existe o pertenece a otro cliente: ambos casos se ven igual."""


def ve_todos(rol: str) -> bool:
    """Solo admin tiene acceso global; cualquier otro rol queda limitado a lo propio."""
    return rol == "admin"


def crear_pedido(repositorio: RepositorioPedidos, entrada: PedidoEntrada, usuario_id: int) -> Pedido:
    """El dueño siempre es quien hizo la petición (viene del token, no del cuerpo)."""
    return repositorio.crear(entrada, usuario_id)


def listar_pedidos(repositorio: RepositorioPedidos, usuario_id: int, rol: str) -> list[Pedido]:
    return repositorio.listar_todos() if ve_todos(rol) else repositorio.listar_propios(usuario_id)


def consultar_pedido(repositorio: RepositorioPedidos, id: int, usuario_id: int, rol: str) -> Pedido:
    pedido = repositorio.obtener_cualquiera(id) if ve_todos(rol) else repositorio.obtener_propio(id, usuario_id)
    if pedido is None:
        raise PedidoNoEncontrado
    return pedido


def eliminar_pedido(repositorio: RepositorioPedidos, id: int, usuario_id: int, rol: str) -> None:
    eliminado = repositorio.eliminar_cualquiera(id) if ve_todos(rol) else repositorio.eliminar_propio(id, usuario_id)
    if not eliminado:
        raise PedidoNoEncontrado
