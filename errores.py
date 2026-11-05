"""Respuestas JSON uniformes para errores de petición y errores HTTP."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


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
