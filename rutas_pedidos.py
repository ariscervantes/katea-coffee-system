"""Rutas autenticadas: el cliente usa filtros SQL; admin tiene acceso global explícito."""

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, HTTPException, Response

from autenticacion import Identidad, usuario_actual
from modelos import RespuestaError
from modelos_pedidos import EntradaPedidosComentario, Pedido, PedidoEntrada, RespuestaComentario
from repositorio_pedidos import (
    ImporteFueraDeRango, ProductoNoDisponible, ProductoPedidoInexistente, RepositorioPedidos,
)
from usuarios import RepositorioUsuarios


SesionActual = Annotated[Identidad, Depends(usuario_actual)]

INSTRUCCION_IA = (
    "Clasifica el comentario de un cliente sobre su pedido. Responde SOLO un JSON con la forma "
    '{"sentimiento": "positivo" | "neutral" | "negativo", "respuesta": "una respuesta amable '
    'para el cliente, máximo 25 palabras en español"}.\n'
)


def error(descripcion: str) -> dict:
    return {"model": RespuestaError, "description": descripcion}


def datos_del_cliente(yo: Identidad, usuarios: RepositorioUsuarios) -> str:
    """Completa el contexto de la IA con la identidad verificada, nunca con datos del cuerpo."""
    obtener = getattr(usuarios, "obtener", None)
    usuario = obtener(yo.id) if obtener is not None else None
    nombre = getattr(usuario, "usuario", f"id {yo.id}")
    return f"usuario={nombre!r}, id={yo.id}, rol={yo.rol}"


def rutas_pedidos(
    repositorio: RepositorioPedidos,
    usuarios: RepositorioUsuarios,
    preguntar_ia: Callable[[str], dict],
) -> APIRouter:
    router = APIRouter(prefix="/pedidos", tags=["Pedidos"], responses={
        401: error("Falta un token válido o ha vencido"),
        500: error("Error interno del servidor"),
    })

    @router.post("/comentario", response_model=RespuestaComentario, responses={
        400: error("JSON mal formado"),
        422: error("Comentario vacío o fuera de 2–300 caracteres"),
        502: error("La IA respondió algo inesperado o no está disponible"),
        503: error("Falta configurar la IA"),
        504: error("La IA tardó demasiado en responder"),
    }, description="Clasifica un comentario del cliente autenticado y redacta una respuesta amable.")
    def comentario(datos: EntradaPedidosComentario, yo: SesionActual) -> RespuestaComentario:
        instruccion = (
            INSTRUCCION_IA
            + f"Datos del cliente autenticado: {datos_del_cliente(yo, usuarios)}.\n"
            + f"Comentario del cliente: {datos.comentario}"
        )
        ia = preguntar_ia(instruccion)
        if (
            not isinstance(ia, dict)
            or ia.get("sentimiento") not in ("positivo", "neutral", "negativo")
            or not isinstance(ia.get("respuesta"), str)
            or not ia["respuesta"].strip()
        ):
            raise HTTPException(502, "La IA respondió algo inesperado.")
        return RespuestaComentario(
            sentimiento=ia["sentimiento"],
            respuesta=ia["respuesta"].strip()[:200],
        )

    @router.get("", response_model=list[Pedido], description="Cliente: solo propios. Admin: todos.")
    def listar(yo: SesionActual) -> list[Pedido]:
        return repositorio.listar_todos() if yo.rol == "admin" else repositorio.listar_propios(yo.id)

    @router.get("/{id}", response_model=Pedido, responses={
        404: error("Pedido inexistente o ajeno"), 422: error("ID inválido"),
    })
    def consultar(id: int, yo: SesionActual) -> Pedido:
        pedido = repositorio.obtener_cualquiera(id) if yo.rol == "admin" else repositorio.obtener_propio(id, yo.id)
        if pedido is None:
            raise HTTPException(404, "Pedido no encontrado")
        return pedido

    @router.post("", response_model=Pedido, status_code=201, responses={
        400: error("JSON mal formado"),
        409: error("Algún producto no está disponible"),
        422: error("Lista vacía, datos inválidos, producto inexistente, campos extra, producto repetido o importe fuera de rango"),
    }, description="El dueño se obtiene del token; precios y total se calculan en una transacción. Estado inicial pendiente.")
    def crear(entrada: PedidoEntrada, yo: SesionActual) -> Pedido:
        try:
            return repositorio.crear(entrada, yo.id)
        except ProductoPedidoInexistente:
            raise HTTPException(422, "Producto no encontrado") from None
        except ProductoNoDisponible:
            raise HTTPException(409, "Producto no disponible") from None
        except ImporteFueraDeRango:
            raise HTTPException(422, "El total supera el importe máximo de un pedido") from None

    @router.delete("/{id}", status_code=204, responses={
        404: error("Pedido inexistente o ajeno"), 422: error("ID inválido"),
    })
    def eliminar(id: int, yo: SesionActual) -> Response:
        eliminado = repositorio.eliminar_cualquiera(id) if yo.rol == "admin" else repositorio.eliminar_propio(id, yo.id)
        if not eliminado:
            raise HTTPException(404, "Pedido no encontrado")
        return Response(status_code=204)

    return router
