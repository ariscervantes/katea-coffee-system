"""Respuestas JSON uniformes para errores de petición y errores HTTP."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.modelos.productos import RespuestaError


registrador = logging.getLogger(__name__)

# Respuestas de error documentadas en OpenAPI; comparten el esquema RespuestaError.
RESPUESTA_400 = {"model": RespuestaError, "description": "JSON mal formado"}
RESPUESTA_401 = {"model": RespuestaError, "description": "Falta un token válido o ha vencido"}
RESPUESTA_403 = {"model": RespuestaError, "description": "Se requiere rol admin"}
RESPUESTA_404 = {"model": RespuestaError, "description": "Producto no encontrado"}
RESPUESTA_409 = {"model": RespuestaError, "description": "Nombre y preparación duplicados"}
RESPUESTA_422 = {"model": RespuestaError, "description": "Datos o parámetros inválidos"}
RESPUESTA_500 = {"model": RespuestaError, "description": "Error interno del servidor"}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
        errores = exc.errors()
        json_roto = any(error["type"] == "json_invalid" for error in errores)
        # No incluimos input/ctx: pueden contener objetos no serializables.
        detalles = [
            {"campo": list(error["loc"]), "mensaje": error["msg"], "tipo": error["type"]}
            for error in errores
        ]
        return JSONResponse(
            status_code=400 if json_roto else 422,
            content={"error": "JSON mal formado" if json_roto else "Datos inválidos", "detalles": detalles},
        )

    @app.exception_handler(HTTPException)
    async def error_http(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail), "detalles": []},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def error_interno(request: Request, exc: Exception) -> JSONResponse:
        registrador.exception("Error no controlado en %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Error interno del servidor", "detalles": []},
        )
