"""Repositorio aislado para probar HTTP sin conectar a MySQL."""

import pytest

import main
from modelos import Producto
from repositorio import ProductoDuplicado, nombre_normalizado


class RepositorioPrueba:
    def __init__(self):
        self.productos = {}
        self.siguiente = 1

    def inicializar(self):
        pass

    def listar(self):
        return list(self.productos.values())

    def obtener(self, id):
        return self.productos.get(id)

    def existe_duplicado(self, entrada, excluir_id=None):
        return any(
            p.id != excluir_id
            and nombre_normalizado(p.nombre) == nombre_normalizado(entrada.nombre)
            and p.preparacion == entrada.preparacion
            for p in self.productos.values()
        )

    def crear(self, entrada):
        if self.existe_duplicado(entrada):
            raise ProductoDuplicado
        producto = Producto.model_construct(id=self.siguiente, **entrada.model_dump())
        self.productos[producto.id] = producto
        self.siguiente += 1
        return producto

    def reemplazar(self, id, entrada):
        if id not in self.productos:
            return None
        if self.existe_duplicado(entrada, excluir_id=id):
            raise ProductoDuplicado
        producto = Producto.model_construct(id=id, **entrada.model_dump())
        self.productos[id] = producto
        return producto

    def eliminar(self, id):
        return self.productos.pop(id, None) is not None


@pytest.fixture(autouse=True)
def repositorio_prueba(monkeypatch):
    repositorio = RepositorioPrueba()
    monkeypatch.setattr(main, "RepositorioProductos", lambda: repositorio)
    return repositorio
