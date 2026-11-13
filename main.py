"""Punto de entrada: uvicorn main:app --reload."""

from contextlib import asynccontextmanager
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Response, status

from autenticacion import Autenticacion, Credenciales, Sesion, exigir_admin
from usuarios import RepositorioUsuarios
from errores import registrar_manejadores
from modelos import Producto, ProductoEntrada, RespuestaError
from repositorio import ProductoDuplicado, ProductoEnPedido, RepositorioProductos
from repositorio_pedidos import RepositorioPedidos
from rutas_pedidos import rutas_pedidos

# ---------- Preguntarle algo a la IA (péguenlo una vez, arriba de sus rutas) ----------
import json, os, urllib.request, urllib.error


IA_URL = os.environ.get("EXTERNO_URL", "https://generativelanguage.googleapis.com")
IA_MODELO = os.environ.get("GEMINI_MODELO", "gemini-flash-lite-latest")
IA_CLAVE = os.environ.get("GEMINI_API_KEY", "")         # IDEA 3: la clave NO va en el código


def _fallo_transitorio(codigo: int) -> bool:
    """Solo se reintentan fallos que podrían resolverse solos; un 400 no se repite."""
    return codigo == 429 or 500 <= codigo < 600


def preguntar_a_la_ia(instruccion: str) -> dict:
    """Le pregunta algo a Gemini y regresa el JSON que contestó. Si algo sale mal, responde 502/503/504."""
    if not IA_CLAVE and "googleapis.com" in IA_URL:
        raise HTTPException(503, "Falta configurar la variable de entorno GEMINI_API_KEY")
    cuerpo = {"contents": [{"parts": [{"text": instruccion}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    datos = json.dumps(cuerpo).encode()
    for intento in range(2):                                     # Un reintento ante fallos transitorios.
        req = urllib.request.Request(f"{IA_URL}/v1beta/models/{IA_MODELO}:generateContent",
                                     data=datos, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": IA_CLAVE})
        try:                                                     # IDEA 1: su API llama a otra API
            with urllib.request.urlopen(req, timeout=5) as r:    # IDEA 2: máximo 5 segundos esperando
                respuesta = json.loads(r.read())
            return json.loads(respuesta["candidates"][0]["content"]["parts"][0]["text"])
        except TimeoutError:
            raise HTTPException(504, "La IA tardó demasiado en responder. Intenta en un momento.")
        except urllib.error.HTTPError as e:
            if intento == 0 and _fallo_transitorio(e.code):
                continue
            raise HTTPException(502, f"La IA no está disponible (respondió {e.code}). Intenta más tarde.")
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise HTTPException(504, "La IA tardó demasiado en responder. Intenta en un momento.")
            if intento == 0:
                continue
            raise HTTPException(502, "No se pudo conectar con la IA.")
        except (ValueError, KeyError, IndexError, TypeError):
            raise HTTPException(502, "La IA respondió algo que no entendemos.")
    raise HTTPException(502, "La IA no está disponible. Intenta más tarde.")



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
    preguntar_ia: Callable[[str], dict] | None = None,
) -> FastAPI:
    almacen = repositorio or RepositorioProductos()

    cuentas = usuarios if usuarios is not None else RepositorioUsuarios()
    seguridad = autenticacion if autenticacion is not None else Autenticacion(cuentas)
    ordenes = pedidos if pedidos is not None else RepositorioPedidos()
    consultar_ia = preguntar_ia if preguntar_ia is not None else preguntar_a_la_ia

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI):
        almacen.inicializar()
        cuentas.inicializar()
        ordenes.inicializar()
        yield

    app = FastAPI(title="Katea — API de productos", version="1.0.0", lifespan=ciclo_vida)
    registrar_manejadores(app)
    app.state.autenticacion = seguridad
    app.include_router(rutas_pedidos(ordenes, cuentas, consultar_ia))

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
