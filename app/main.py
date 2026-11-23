"""Punto de entrada: python -m uvicorn app.main:app --reload."""

from contextlib import asynccontextmanager
import os
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.seguridad import Autenticacion
from app.repositorios.usuarios import RepositorioUsuarios
from app.errores import registrar_manejadores
from app.integraciones.gemini import preguntar_a_la_ia
from app.repositorios.productos import RepositorioProductos
from app.repositorios.pedidos import RepositorioPedidos
from app.routers.auth import rutas_auth
from app.routers.pedidos import rutas_pedidos
from app.routers.productos import rutas_productos


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
    # No usar "*": el navegador debe limitar el acceso a los orígenes del front.
    origenes_cors = os.environ.get(
        "CORS_ORIGENES", "http://127.0.0.1:5500,http://localhost:5500"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origen.strip() for origen in origenes_cors.split(",") if origen.strip()],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    registrar_manejadores(app)
    app.state.autenticacion = seguridad
    app.include_router(rutas_pedidos(ordenes, cuentas, consultar_ia))
    app.include_router(rutas_auth(seguridad))
    app.include_router(rutas_productos(almacen))

    return app


app = crear_app()
