"""Doble de prueba en memoria para validar la API sin depender de MySQL."""

from threading import Lock

import pytest

from modelos import Producto, ProductoEntrada
from repositorio import ProductoDuplicado, nombre_normalizado


class RepositorioFalso:
    """Misma interfaz que RepositorioProductos, sin base de datos."""

    def __init__(self) -> None:
        self._productos: dict[int, Producto] = {}
        self._siguiente_id = 1
        self._candado = Lock()

    def inicializar(self) -> None:
        pass

    def listar(self) -> list[Producto]:
        with self._candado:
            return [self._productos[id] for id in sorted(self._productos)]

    def obtener(self, id: int) -> Producto | None:
        with self._candado:
            return self._productos.get(id)

    def existe_duplicado(self, entrada: ProductoEntrada, excluir_id: int | None = None) -> bool:
        nombre = nombre_normalizado(entrada.nombre)
        with self._candado:
            return any(
                producto.id != excluir_id
                and nombre_normalizado(producto.nombre) == nombre
                and producto.preparacion == entrada.preparacion
                for producto in self._productos.values()
            )

    def crear(self, entrada: ProductoEntrada) -> Producto:
        if self.existe_duplicado(entrada):
            raise ProductoDuplicado
        with self._candado:
            producto = Producto.model_construct(id=self._siguiente_id, **entrada.model_dump())
            self._productos[producto.id] = producto
            self._siguiente_id += 1
            return producto

    def reemplazar(self, id: int, entrada: ProductoEntrada) -> Producto | None:
        if self.existe_duplicado(entrada, excluir_id=id):
            raise ProductoDuplicado
        with self._candado:
            if id not in self._productos:
                return None
            producto = Producto.model_construct(id=id, **entrada.model_dump())
            self._productos[id] = producto
            return producto

    def eliminar(self, id: int) -> bool:
        with self._candado:
            return self._productos.pop(id, None) is not None

    def vaciar(self) -> None:
        with self._candado:
            self._productos.clear()
            self._siguiente_id = 1


@pytest.fixture
def repositorio_falso() -> RepositorioFalso:
    return RepositorioFalso()
