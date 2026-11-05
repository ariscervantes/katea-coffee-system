"""Estado temporal de un proceso; se pierde al reiniciar el servidor."""

from itertools import count

from modelos import Producto


productos: dict[int, Producto] = {}
_secuencia_ids = count(1)


def generar_id() -> int:
    """Genera identificadores crecientes; no reutiliza los eliminados."""
    return next(_secuencia_ids)
