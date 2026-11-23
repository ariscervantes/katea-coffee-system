"""Ruta pública de inicio de sesión: recibe credenciales JSON y entrega un JWT."""

from fastapi import APIRouter

from app.errores import RESPUESTA_400, RESPUESTA_422, RESPUESTA_500
from app.modelos.productos import RespuestaError
from app.seguridad import Autenticacion, Credenciales, Sesion


def rutas_auth(seguridad: Autenticacion) -> APIRouter:
    router = APIRouter(tags=["Autenticación"], responses={500: RESPUESTA_500})

    @router.post(
        "/login", response_model=Sesion,
        responses={400: RESPUESTA_400, 401: {"model": RespuestaError, "description": "Usuario o clave incorrectos"},
                   422: RESPUESTA_422},
        description="Recibe credenciales JSON y devuelve un JWT válido durante 30 minutos.",
    )
    def login(credenciales: Credenciales) -> Sesion:
        return seguridad.iniciar_sesion(credenciales)

    return router
