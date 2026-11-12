"""Matriz de productos mediante JWT reales y repositorio aislado."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import secrets
from unittest.mock import Mock

import httpx
import jwt
import pytest

from autenticacion import Autenticacion
from main import crear_app
from modelos import ProductoEntrada
from test_base_api import datos_validos
from usuarios import RepositorioUsuarios, Usuario


@pytest.fixture
def escenario(repositorio_falso):
    usuarios = Mock(spec=RepositorioUsuarios)
    seguridad = Autenticacion(usuarios, secrets.token_urlsafe(48))
    app = crear_app(repositorio_falso, usuarios, seguridad)
    inicial = repositorio_falso.crear(ProductoEntrada.model_validate(datos_validos() | {"nombre": "Producto inicial"}))
    # Espías para comprobar que el rechazo ni siquiera llama a las escrituras.
    for nombre in ("crear", "reemplazar", "eliminar"):
        setattr(repositorio_falso, nombre, Mock(wraps=getattr(repositorio_falso, nombre)))
    return app, seguridad, repositorio_falso, inicial.id


def ejecutar(app, comprobacion):
    async def consultar():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as cliente:
            await comprobacion(cliente)
    asyncio.run(consultar())


def token_para(seguridad, caso):
    ahora = datetime.now(timezone.utc)
    datos = {"sub": "1", "rol": "admin", "iat": ahora, "exp": ahora + timedelta(minutes=30)}
    if caso == "sin_token": return None
    if caso == "mal_formado": return "no-es-un-jwt"
    if caso == "cliente": datos["rol"] = "cliente"
    if caso == "vencido": datos.update(iat=ahora - timedelta(hours=1), exp=ahora - timedelta(seconds=1))
    if caso.startswith("sin_"): del datos[caso[4:]]
    if caso == "rol_invalido": datos["rol"] = ["admin"]
    if caso == "identidad_invalida": datos["sub"] = "cero"
    if caso == "exp_invalido": datos["exp"] = {"fecha": "futura"}
    algoritmo = "HS384" if caso == "algoritmo_invalido" else "HS256"
    clave = secrets.token_urlsafe(48) if caso == "firma_invalida" else seguridad.secreto
    token = jwt.encode(datos, clave, algorithm=algoritmo)
    if caso == "alterado": token = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]
    return token


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE"])
@pytest.mark.parametrize("caso,codigo", [
    ("sin_token", 401), ("mal_formado", 401), ("cliente", 403),
    ("alterado", 401), ("vencido", 401), ("firma_invalida", 401),
    ("algoritmo_invalido", 401), ("sin_sub", 401), ("sin_rol", 401),
    ("sin_exp", 401), ("sin_iat", 401), ("rol_invalido", 401),
    ("identidad_invalida", 401), ("exp_invalido", 401),
])
def test_rechazos_no_modifican_productos(escenario, metodo, caso, codigo):
    app, seguridad, repo, id = escenario
    antes = [p.model_dump() for p in repo.listar()]
    token = token_para(seguridad, caso)
    ruta = "/productos" if metodo == "POST" else f"/productos/{id}"
    async def comprobar(c):
        r = await c.request(
            metodo, ruta,
            headers={"Authorization": "Bearer " + token} if token else {},
            **({"json": datos_validos()} if metodo != "DELETE" else {}),
        )
        assert r.status_code == codigo
        assert set(r.json()) == {"error", "detalles"}
        assert r.json()["detalles"] == []
        if codigo == 401: assert r.headers["www-authenticate"] == "Bearer"
        else:
            assert r.json()["error"] == "Tu rol no puede hacer esto"
            assert "www-authenticate" not in r.headers
        assert [p.model_dump() for p in repo.listar()] == antes
        for nombre in ("crear", "reemplazar", "eliminar"):
            getattr(repo, nombre).assert_not_called()
    ejecutar(app, comprobar)


@pytest.mark.parametrize("encabezado", [None, "Bearer invalido"])
def test_get_publicos_no_exigen_sesion(escenario, encabezado):
    app, _, _, id = escenario
    async def comprobar(c):
        for ruta in ["/productos", f"/productos/{id}"]:
            r = await c.get(ruta, headers={"Authorization": encabezado} if encabezado else {})
            assert r.status_code == 200
        assert (await c.get("/productos/999999")).status_code == 404
    ejecutar(app, comprobar)


def test_admin_crea_reemplaza_y_elimina(escenario):
    app, seguridad, repo, _ = escenario
    token = seguridad.crear_token(Usuario(1, "admin_aislado", "", "admin"))
    async def comprobar(c):
        encabezados = {"Authorization": "Bearer " + token}
        r = await c.post("/productos", json=datos_validos(), headers=encabezados)
        assert r.status_code == 201
        ruta = f'/productos/{r.json()["id"]}'
        cambio = datos_validos() | {"precio": 80}
        r = await c.put(ruta, json=cambio, headers=encabezados)
        assert r.status_code == 200 and r.json()["precio"] == 80
        assert (await c.get(ruta)).json()["precio"] == 80
        r = await c.delete(ruta, headers=encabezados)
        assert r.status_code == 204 and r.content == b""
        assert (await c.get(ruta)).status_code == 404
        repo.crear.assert_called_once()
        repo.reemplazar.assert_called_once()
        repo.eliminar.assert_called_once()
    ejecutar(app, comprobar)


def test_contrato_publico_protegido_y_exportacion(escenario):
    app, _, _, _ = escenario
    esquema = app.openapi()
    assert esquema == json.loads((Path(__file__).resolve().parents[1] / "docs/openapi.json").read_text())
    assert "security" not in esquema
    assert esquema["components"]["securitySchemes"]["BearerJWT"] == {
        "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
    }
    for ruta in ["/productos", "/productos/{id}"]:
        assert "security" not in esquema["paths"][ruta]["get"]
    for ruta, metodo in [("/productos", "post"), ("/productos/{id}", "put"), ("/productos/{id}", "delete")]:
        operacion = esquema["paths"][ruta][metodo]
        assert operacion["security"] == [{"BearerJWT": []}]
        for codigo in ["401", "403"]:
            assert operacion["responses"][codigo]["content"]["application/json"]["schema"]["$ref"].endswith("/RespuestaError")
