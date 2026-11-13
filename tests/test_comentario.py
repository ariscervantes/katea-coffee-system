"""Endpoint de comentarios: sesión obligatoria, contexto del usuario y validación de la IA."""

import asyncio
import secrets
from unittest.mock import Mock

import httpx
import pytest

from autenticacion import Autenticacion
from main import crear_app
from repositorio_pedidos import RepositorioPedidos
from usuarios import Usuario


class UsuariosFalsos:
    def __init__(self):
        self.cuentas = {
            1: Usuario(1, "ana_cliente", "", "cliente"),
            2: Usuario(2, "beto_admin", "", "admin"),
        }

    def inicializar(self):
        pass

    def buscar(self, nombre):
        return next((u for u in self.cuentas.values() if u.usuario == nombre), None)

    def obtener(self, id):
        return self.cuentas.get(id)


class IAFalsa:
    def __init__(self, respuesta=None):
        self.respuesta = respuesta
        self.instrucciones = []

    def __call__(self, instruccion):
        self.instrucciones.append(instruccion)
        return self.respuesta


def crear_escenario(cuentas, respuesta_ia):
    seguridad = Autenticacion(cuentas, secrets.token_urlsafe(48))
    ia = IAFalsa(respuesta_ia)
    app = crear_app(
        usuarios=cuentas,
        autenticacion=seguridad,
        pedidos=Mock(spec=RepositorioPedidos),
        preguntar_ia=ia,
    )
    encabezados = {
        nombre: {"Authorization": "Bearer " + seguridad.crear_token(usuario)}
        for nombre, usuario in [("cliente", cuentas.cuentas[1]), ("admin", cuentas.cuentas[2])]
    }
    return app, ia, encabezados


def ejecutar(app, funcion):
    async def consultar():
        transporte = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transporte, base_url="http://test") as cliente:
            await funcion(cliente)

    asyncio.run(consultar())


@pytest.mark.parametrize("nombre,id,rol", [("cliente", 1, "cliente"), ("admin", 2, "admin")])
def test_comentario_incluye_al_usuario_del_token(nombre, id, rol):
    cuentas = UsuariosFalsos()
    app, ia, h = crear_escenario(cuentas, {"sentimiento": "positivo", "respuesta": "  ¡Gracias por tu comentario!  "})

    async def comprobar(c):
        r = await c.post("/pedidos/comentario", json={"comentario": "El café estaba delicioso"}, headers=h[nombre])
        assert r.status_code == 200
        assert r.json() == {"sentimiento": "positivo", "respuesta": "¡Gracias por tu comentario!"}
        assert len(ia.instrucciones) == 1
        instruccion = ia.instrucciones[0]
        assert f"usuario={cuentas.cuentas[id].usuario!r}" in instruccion
        assert f"id={id}" in instruccion and f"rol={rol}" in instruccion
        assert "El café estaba delicioso" in instruccion

    ejecutar(app, comprobar)


@pytest.mark.parametrize("encabezado", [None, "Bearer invalido"])
def test_comentario_exige_sesion(encabezado):
    app, ia, _ = crear_escenario(UsuariosFalsos(), {"sentimiento": "neutral", "respuesta": "Gracias"})

    async def comprobar(c):
        r = await c.post(
            "/pedidos/comentario",
            json={"comentario": "Todo bien"},
            headers={"Authorization": encabezado} if encabezado else {},
        )
        assert r.status_code == 401
        assert r.headers["www-authenticate"] == "Bearer"
        assert set(r.json()) == {"error", "detalles"}
        assert ia.instrucciones == []

    ejecutar(app, comprobar)


@pytest.mark.parametrize("cuerpo", [
    {}, {"comentario": ""}, {"comentario": "a"}, {"comentario": "   "},
    {"comentario": "a" * 301}, {"comentario": 12}, {"comentario": True},
    {"comentario": "Todo bien", "usuario_id": 2},
])
def test_comentario_invalido_no_llama_a_la_ia(cuerpo):
    app, ia, h = crear_escenario(UsuariosFalsos(), {"sentimiento": "neutral", "respuesta": "Gracias"})

    async def comprobar(c):
        r = await c.post("/pedidos/comentario", json=cuerpo, headers=h["cliente"])
        assert r.status_code == 422
        assert set(r.json()) == {"error", "detalles"}
        assert ia.instrucciones == []

    ejecutar(app, comprobar)


@pytest.mark.parametrize("respuesta_ia", [
    None, [], "texto", {},
    {"sentimiento": "feliz", "respuesta": "Gracias"},
    {"sentimiento": "positivo"},
    {"sentimiento": "positivo", "respuesta": ""},
    {"sentimiento": "positivo", "respuesta": "   "},
    {"sentimiento": "positivo", "respuesta": 42},
])
def test_respuesta_inesperada_de_la_ia_da_502(respuesta_ia):
    app, _, h = crear_escenario(UsuariosFalsos(), respuesta_ia)

    async def comprobar(c):
        r = await c.post("/pedidos/comentario", json={"comentario": "Todo bien"}, headers=h["cliente"])
        assert r.status_code == 502
        assert r.json() == {"error": "La IA respondió algo inesperado.", "detalles": []}

    ejecutar(app, comprobar)


def test_respuesta_de_la_ia_se_recorta_a_200_caracteres():
    app, _, h = crear_escenario(UsuariosFalsos(), {"sentimiento": "neutral", "respuesta": "x" * 250})

    async def comprobar(c):
        r = await c.post("/pedidos/comentario", json={"comentario": "Todo bien"}, headers=h["cliente"])
        assert r.status_code == 200
        assert r.json()["respuesta"] == "x" * 200

    ejecutar(app, comprobar)
