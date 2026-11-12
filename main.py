"""Punto de entrada: uvicorn main:app --reload."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response, status

from autenticacion import Autenticacion, Credenciales, Sesion, exigir_admin
from usuarios import RepositorioUsuarios
from errores import registrar_manejadores
from modelos import Producto, ProductoEntrada, RespuestaError
from repositorio import ProductoDuplicado, ProductoEnPedido, RepositorioProductos
from repositorio_pedidos import RepositorioPedidos
from rutas_pedidos import rutas_pedidos


MENSAJE_NO_ENCONTRADO = "Producto no encontrado"
MENSAJE_DUPLICADO = "Ya existe un producto con ese nombre y preparación"

RESPUESTA_400 = {"model": RespuestaError, "description": "JSON mal formado"}
RESPUESTA_401 = {"model": RespuestaError, "description": "Falta un token válido o ha vencido"}
RESPUESTA_403 = {"model": RespuestaError, "description": "Se requiere rol admin"}
RESPUESTA_404 = {"model": RespuestaError, "description": "Producto no encontrado"}
RESPUESTA_409 = {"model": RespuestaError, "description": "Nombre y preparación duplicados"}
RESPUESTA_422 = {"model": RespuestaError, "description": "Datos o parámetros inválidos"}
RESPUESTA_500 = {"model": RespuestaError, "description": "Error interno del servidor"}


def crear_app(
    repositorio: RepositorioProductos | None = None,
    usuarios: RepositorioUsuarios | None = None,
    autenticacion: Autenticacion | None = None,
    pedidos: RepositorioPedidos | None = None,
) -> FastAPI:
    almacen = repositorio or RepositorioProductos()

    cuentas = usuarios if usuarios is not None else RepositorioUsuarios()
    seguridad = autenticacion if autenticacion is not None else Autenticacion(cuentas)
    ordenes = pedidos if pedidos is not None else RepositorioPedidos()

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI):
        almacen.inicializar()
        cuentas.inicializar()
        ordenes.inicializar()
        yield

    app = FastAPI(title="Katea — API de productos", version="1.0.0", lifespan=ciclo_vida)
    registrar_manejadores(app)
    app.state.autenticacion = seguridad
    app.include_router(rutas_pedidos(ordenes))

    @app.post(
        "/login", response_model=Sesion, tags=["Autenticación"],
        responses={400: RESPUESTA_400, 401: {"model": RespuestaError, "description": "Usuario o clave incorrectos"},
                   422: RESPUESTA_422, 500: RESPUESTA_500},
        description="Recibe credenciales JSON y devuelve un JWT válido durante 30 minutos.",
    )
    def login(credenciales: Credenciales) -> Sesion:
        return seguridad.iniciar_sesion(credenciales)


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
        dependencies=[Depends(exigir_admin)],
        responses={400: RESPUESTA_400, 401: RESPUESTA_401, 403: RESPUESTA_403,
                   409: RESPUESTA_409, 422: RESPUESTA_422, 500: RESPUESTA_500},
    )
    def crear_producto(entrada: ProductoEntrada) -> Producto:
        comprobar_duplicado(entrada)
        try:
            return almacen.crear(entrada)
        except ProductoDuplicado:
            raise HTTPException(status_code=409, detail=MENSAJE_DUPLICADO) from None

    @app.put(
        "/productos/{id}",
        dependencies=[Depends(exigir_admin)],
        response_model=Producto,
        responses={
            400: RESPUESTA_400,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
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
        dependencies=[Depends(exigir_admin)],
        responses={401: RESPUESTA_401, 403: RESPUESTA_403, 404: RESPUESTA_404,
                   409: {"model": RespuestaError, "description": "Producto asociado a un pedido"},
                   422: RESPUESTA_422, 500: RESPUESTA_500},
    )
    def eliminar_producto(id: int) -> Response:
        try:
            eliminado = almacen.eliminar(id)
        except ProductoEnPedido:
            raise HTTPException(409, "El producto está asociado a un pedido") from None
        if not eliminado:
            raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = crear_app()
