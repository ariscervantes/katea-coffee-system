"""Regresiones HTTP de imagen, errores y operaciones de productos."""

import asyncio

import httpx
import pytest

from main import crear_app
from test_base_api import datos_validos


@pytest.fixture(autouse=True)
def aislar_repositorio(repositorio_falso):
    repositorio_falso.vaciar()
    yield
    repositorio_falso.vaciar()


def cliente(repositorio_falso):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=crear_app(repositorio_falso), raise_app_exceptions=False
        ),
        base_url="http://test",
    )


def error(respuesta, codigo):
    assert respuesta.status_code == codigo, respuesta.text
    assert set(respuesta.json()) == {"error", "detalles"}
    assert isinstance(respuesta.json()["error"], str)
    assert isinstance(respuesta.json()["detalles"], list)


@pytest.mark.parametrize("imagen,valida", [
    (".jpg", False), ("/img/.png", False), ("carpeta\\.webp", False),
    (" .jpeg", False), ("\n.jpg", False), ("foto.jpg\n", False),
    ("foto\r.png", False), ("\r\nfoto.webp", False),
    ("", False), ("   ", False), ("foto.gif", False),
    ("foto.JPG", False), ("https://ejemplo.com/foto.jpg?v=1", False),
    ("foto.jpg", True), ("/img/foto.jpeg", True),
    ("https://ejemplo.com/foto.png", True), ("/img/café.webp", True),
])
def test_imagen_post_y_put(repositorio_falso, imagen, valida):
    async def comprobar():
        async with cliente(repositorio_falso) as c:
            entrada = datos_validos() | {"imagen_url": imagen}
            r = await c.post("/productos", json=entrada)
            if valida:
                assert r.status_code == 201, r.text
                ruta = f'/productos/{r.json()["id"]}'
                actualizado = await c.put(ruta, json=entrada)
                assert actualizado.status_code == 200
                assert actualizado.json()["imagen_url"] == imagen
            else:
                error(r, 422)
                assert repositorio_falso.listar() == []
                valido = await c.post("/productos", json=datos_validos())
                ruta = f'/productos/{valido.json()["id"]}'
                error(await c.put(ruta, json=entrada), 422)
                assert (await c.get(ruta)).json() == valido.json()
    asyncio.run(comprobar())


def test_errores_crud_duplicados_y_put_repetido(repositorio_falso):
    async def comprobar():
        async with cliente(repositorio_falso) as c:
            for metodo, ruta in [("POST", "/productos"), ("PUT", "/productos/999999")]:
                error(await c.request(metodo, ruta, content='{"precio":', headers={"Content-Type": "application/json"}), 400)
                error(await c.request(metodo, ruta, json={}), 422)
            for metodo in ["GET", "PUT", "DELETE"]:
                error(await c.request(metodo, "/productos/999999", **({"json": datos_validos()} if metodo == "PUT" else {})), 404)
            a = await c.post("/productos", json=datos_validos())
            assert a.status_code == 201
            entrada = datos_validos() | {"nombre": " MATCHA LATTE "}
            error(await c.post("/productos", json=entrada), 409)
            b = await c.post("/productos", json=entrada | {"preparacion": "caliente", "disponible": False})
            assert b.status_code == 201
            error(await c.put(f'/productos/{b.json()["id"]}', json=entrada), 409)
            antes = (await c.get("/productos")).json()
            assert b.json() in antes
            ruta = f'/productos/{a.json()["id"]}'
            for _ in range(2):
                r = await c.put(ruta, json=datos_validos())
                assert r.status_code == 200
                assert r.json() == a.json()
            assert (await c.get("/productos")).json() == antes
            assert (await c.delete(ruta)).status_code == 204
            error(await c.delete(ruta), 404)
            error(await c.get(ruta), 404)
    asyncio.run(comprobar())
