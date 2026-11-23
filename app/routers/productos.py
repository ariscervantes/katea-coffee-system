"""Rutas de productos: lectura pública; crear, reemplazar y eliminar exigen rol admin."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.errores import (
    RESPUESTA_400, RESPUESTA_401, RESPUESTA_403, RESPUESTA_404, RESPUESTA_409, RESPUESTA_422, RESPUESTA_500,
)
from app.modelos.productos import Producto, ProductoEntrada, RespuestaError
from app.repositorios.productos import ProductoDuplicado, ProductoEnPedido, RepositorioProductos
from app.seguridad import exigir_admin


MENSAJE_NO_ENCONTRADO = "Producto no encontrado"
MENSAJE_DUPLICADO = "Ya existe un producto con ese nombre y preparación"


def rutas_productos(almacen: RepositorioProductos) -> APIRouter:
    router = APIRouter(prefix="/productos", responses={500: RESPUESTA_500})

    def buscar_producto(id: int) -> Producto:
        producto = almacen.obtener(id)
        if producto is None:
            raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
        return producto

    def comprobar_duplicado(entrada: ProductoEntrada, excluir_id: int | None = None) -> None:
        if almacen.existe_duplicado(entrada, excluir_id=excluir_id):
            raise HTTPException(status_code=409, detail=MENSAJE_DUPLICADO)

    @router.get(
        "",
        response_model=list[Producto],
    )
    def listar_productos() -> list[Producto]:
        # Esta práctica incluye también los no disponibles.
        return almacen.listar()

    @router.get(
        "/{id}",
        response_model=Producto,
        responses={404: RESPUESTA_404, 422: RESPUESTA_422},
    )
    def consultar_producto(id: int) -> Producto:
        return buscar_producto(id)

    @router.post(
        "",
        response_model=Producto,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(exigir_admin)],
        responses={400: RESPUESTA_400, 401: RESPUESTA_401, 403: RESPUESTA_403,
                   409: RESPUESTA_409, 422: RESPUESTA_422},
    )
    def crear_producto(entrada: ProductoEntrada) -> Producto:
        comprobar_duplicado(entrada)
        try:
            return almacen.crear(entrada)
        except ProductoDuplicado:
            raise HTTPException(status_code=409, detail=MENSAJE_DUPLICADO) from None

    @router.put(
        "/{id}",
        dependencies=[Depends(exigir_admin)],
        response_model=Producto,
        responses={
            400: RESPUESTA_400,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
            404: RESPUESTA_404,
            409: RESPUESTA_409,
            422: RESPUESTA_422,
        },
    )
    def reemplazar_producto(id: int, entrada: ProductoEntrada) -> Producto:
        buscar_producto(id)
        comprobar_duplicado(entrada, excluir_id=id)
        try:
            producto = almacen.reemplazar(id, entrada)
        except ProductoDuplicado:
            raise HTTPException(status_code=409, detail=MENSAJE_DUPLICADO) from None
        if producto is None:
            raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
        return producto

    @router.delete(
        "/{id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(exigir_admin)],
        responses={401: RESPUESTA_401, 403: RESPUESTA_403, 404: RESPUESTA_404,
                   409: {"model": RespuestaError, "description": "Producto asociado a un pedido"},
                   422: RESPUESTA_422},
    )
    def eliminar_producto(id: int) -> Response:
        try:
            eliminado = almacen.eliminar(id)
        except ProductoEnPedido:
            raise HTTPException(409, "El producto está asociado a un pedido") from None
        if not eliminado:
            raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
