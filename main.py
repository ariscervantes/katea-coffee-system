"""Punto de entrada: uvicorn main:app --reload."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status

from errores import registrar_manejadores
from modelos import Producto, ProductoEntrada, RespuestaError
from repositorio import ProductoDuplicado, RepositorioProductos


MENSAJE_NO_ENCONTRADO = "Producto no encontrado"
MENSAJE_DUPLICADO = "Ya existe un producto con ese nombre y preparación"

RESPUESTA_400 = {"model": RespuestaError, "description": "JSON mal formado"}
RESPUESTA_404 = {"model": RespuestaError, "description": "Producto no encontrado"}
RESPUESTA_409 = {"model": RespuestaError, "description": "Nombre y preparación duplicados"}
RESPUESTA_422 = {"model": RespuestaError, "description": "Datos o parámetros inválidos"}
RESPUESTA_500 = {"model": RespuestaError, "description": "Error interno del servidor"}


def crear_app(repositorio: RepositorioProductos | None = None) -> FastAPI:
    almacen = repositorio or RepositorioProductos()

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI):
        almacen.inicializar()
        yield

    app = FastAPI(title="Katea — API de productos", version="1.0.0", lifespan=ciclo_vida)
    registrar_manejadores(app)

    def buscar_producto(id: int) -> Producto:
        producto = almacen.obtener(id)
        if producto is None:
            raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
        return producto

    def comprobar_duplicado(entrada: ProductoEntrada, excluir_id: int | None = None) -> None:
        if almacen.existe_duplicado(entrada, excluir_id=excluir_id):
            raise HTTPException(status_code=409, detail=MENSAJE_DUPLICADO)

    @app.get(
        "/productos",
        response_model=list[Producto],
        responses={500: RESPUESTA_500},
    )
    def listar_productos() -> list[Producto]:
        # Esta práctica incluye también los no disponibles.
        return almacen.listar()

    @app.get(
        "/productos/{id}",
        response_model=Producto,
        responses={404: RESPUESTA_404, 422: RESPUESTA_422, 500: RESPUESTA_500},
    )
    def consultar_producto(id: int) -> Producto:
        return buscar_producto(id)

    @app.post(
        "/productos",
        response_model=Producto,
        status_code=status.HTTP_201_CREATED,
        responses={400: RESPUESTA_400, 409: RESPUESTA_409, 422: RESPUESTA_422, 500: RESPUESTA_500},
    )
    def crear_producto(entrada: ProductoEntrada) -> Producto:
        comprobar_duplicado(entrada)
        try:
            return almacen.crear(entrada)
        except ProductoDuplicado:
            raise HTTPException(status_code=409, detail=MENSAJE_DUPLICADO) from None

    @app.put(
        "/productos/{id}",
        response_model=Producto,
        responses={
            400: RESPUESTA_400,
            404: RESPUESTA_404,
            409: RESPUESTA_409,
            422: RESPUESTA_422,
            500: RESPUESTA_500,
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

    @app.delete(
        "/productos/{id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={404: RESPUESTA_404, 422: RESPUESTA_422, 500: RESPUESTA_500},
    )
    def eliminar_producto(id: int) -> Response:
        if not almacen.eliminar(id):
            raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = crear_app()
