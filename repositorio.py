"""Acceso a productos en MySQL.

Todas las consultas usan marcadores de parámetro de MySQL (``%s``, el
equivalente a ``?`` en otros motores); los datos del cliente nunca se
concatenan al texto del SQL.
"""

import pymysql

from basedatos import BaseDatos
from modelos import Producto, ProductoEntrada


SQL_LISTAR = "SELECT id, nombre, descripcion, precio, imagen_url, disponible, preparacion FROM productos ORDER BY id"
SQL_OBTENER = "SELECT id, nombre, descripcion, precio, imagen_url, disponible, preparacion FROM productos WHERE id = %s"
SQL_OBTENER_BLOQUEO = "SELECT id FROM productos WHERE id = %s FOR UPDATE"
SQL_DUPLICADO = """
    SELECT 1 FROM productos
    WHERE nombre_normalizado = %s AND preparacion = %s
    LIMIT 1
"""
SQL_DUPLICADO_EXCLUYENDO = """
    SELECT 1 FROM productos
    WHERE nombre_normalizado = %s AND preparacion = %s AND id <> %s
    LIMIT 1
"""
SQL_INSERTAR = """
    INSERT INTO productos
        (nombre, nombre_normalizado, descripcion, precio, imagen_url, disponible, preparacion)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
SQL_ACTUALIZAR = """
    UPDATE productos
    SET nombre = %s,
        nombre_normalizado = %s,
        descripcion = %s,
        precio = %s,
        imagen_url = %s,
        disponible = %s,
        preparacion = %s
    WHERE id = %s
"""
SQL_ELIMINAR = "DELETE FROM productos WHERE id = %s"


class ProductoEnPedido(Exception):
    """Un detalle de pedido impide borrar el producto referenciado."""


class ProductoDuplicado(Exception):
    """La combinación nombre/preparación ya existe."""


def nombre_normalizado(nombre: str) -> str:
    return nombre.strip().casefold()


def _producto_desde_fila(fila: dict) -> Producto:
    return Producto.model_construct(
        id=int(fila["id"]),
        nombre=fila["nombre"],
        descripcion=fila["descripcion"],
        precio=fila["precio"],
        imagen_url=fila["imagen_url"],
        disponible=bool(fila["disponible"]),
        preparacion=fila["preparacion"],
    )


class RepositorioProductos:
    def __init__(self, base_datos: BaseDatos | None = None) -> None:
        self._base_datos = base_datos or BaseDatos()

    def inicializar(self) -> None:
        self._base_datos.inicializar()

    def listar(self) -> list[Producto]:
        with self._base_datos.conexion() as cursor:
            cursor.execute(SQL_LISTAR)
            return [_producto_desde_fila(fila) for fila in cursor.fetchall()]

    def obtener(self, id: int) -> Producto | None:
        with self._base_datos.conexion() as cursor:
            cursor.execute(SQL_OBTENER, (id,))
            fila = cursor.fetchone()
        return None if fila is None else _producto_desde_fila(fila)

    def existe_duplicado(self, entrada: ProductoEntrada, excluir_id: int | None = None) -> bool:
        parametros: tuple = (nombre_normalizado(entrada.nombre), entrada.preparacion)
        consulta = SQL_DUPLICADO
        if excluir_id is not None:
            consulta = SQL_DUPLICADO_EXCLUYENDO
            parametros += (excluir_id,)
        with self._base_datos.conexion() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchone() is not None

    def crear(self, entrada: ProductoEntrada) -> Producto:
        parametros = (
            entrada.nombre,
            nombre_normalizado(entrada.nombre),
            entrada.descripcion,
            entrada.precio,
            entrada.imagen_url,
            entrada.disponible,
            entrada.preparacion,
        )
        try:
            with self._base_datos.conexion() as cursor:
                cursor.execute(SQL_INSERTAR, parametros)
                nuevo_id = int(cursor.lastrowid)
        except pymysql.err.IntegrityError as error:
            if error.args and error.args[0] == 1062:
                raise ProductoDuplicado from None
            raise
        return Producto.model_construct(id=nuevo_id, **entrada.model_dump())

    def reemplazar(self, id: int, entrada: ProductoEntrada) -> Producto | None:
        parametros = (
            entrada.nombre,
            nombre_normalizado(entrada.nombre),
            entrada.descripcion,
            entrada.precio,
            entrada.imagen_url,
            entrada.disponible,
            entrada.preparacion,
            id,
        )
        try:
            with self._base_datos.conexion() as cursor:
                cursor.execute(SQL_OBTENER_BLOQUEO, (id,))
                if cursor.fetchone() is None:
                    return None
                cursor.execute(SQL_ACTUALIZAR, parametros)
                cursor.execute(SQL_OBTENER, (id,))
                fila = cursor.fetchone()
        except pymysql.err.IntegrityError as error:
            if error.args and error.args[0] == 1062:
                raise ProductoDuplicado from None
            raise
        return None if fila is None else _producto_desde_fila(fila)

    def eliminar(self, id: int) -> bool:
        try:
            with self._base_datos.conexion() as cursor:
                cursor.execute(SQL_ELIMINAR, (id,))
                return cursor.rowcount > 0
        except pymysql.err.IntegrityError as error:
            if error.args and error.args[0] == 1451:
                raise ProductoEnPedido from None
            raise
