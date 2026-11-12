"""Seguridad probada con cuentas y claves efímeras, sin acceder a MySQL."""

import asyncio
from datetime import datetime, timedelta, timezone
import secrets
from typing import Annotated

import jwt
import pytest
from fastapi import Depends
import httpx

from autenticacion import (
    Autenticacion, Credenciales, Identidad, comprobar_clave, proteger_clave,
    secreto_desde_entorno, usuario_actual,
)
from main import crear_app
from usuarios import Usuario


class UsuariosFalsos:
    def __init__(self, usuarios=()):
        self.usuarios = {u.usuario: u for u in usuarios}
        self.inicios = 0

    def inicializar(self):
        self.inicios += 1

    def buscar(self, nombre):
        return self.usuarios.get(nombre)


@pytest.fixture(scope="module")
def cuenta():
    clave = secrets.token_urlsafe(18)
    return clave, proteger_clave(clave)


@pytest.fixture
def seguridad(cuenta):
    clave, hash_clave = cuenta
    repo = UsuariosFalsos([
        Usuario(1, "prueba_admin", hash_clave, "admin"),
        Usuario(2, "prueba_cliente", hash_clave, "cliente"),
    ])
    return Autenticacion(repo, secrets.token_urlsafe(48))


@pytest.fixture
def app_segura(seguridad, repositorio_falso):
    app = crear_app(repositorio_falso, seguridad.usuarios, seguridad)

    @app.get("/privado", response_model=Identidad)
    def privado(yo: Annotated[Identidad, Depends(usuario_actual)]):
        return yo

    return app


def ejecutar(app, funcion):
    async def consultar():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as cliente:
            await funcion(cliente)
    asyncio.run(consultar())


@pytest.mark.parametrize("nombre,rol", [("prueba_admin", "admin"), ("prueba_cliente", "cliente")])
def test_login_json_y_recorrido_bearer(app_segura, seguridad, cuenta, nombre, rol):
    async def comprobar(c):
        r = await c.post("/login", json={"usuario": nombre, "clave": cuenta[0]})
        assert r.status_code == 200
        cuerpo = r.json()
        assert set(cuerpo) == {"access_token", "token_type"}
        assert cuerpo["token_type"] == "bearer"
        assert cuenta[0] not in r.text and cuenta[1] not in r.text
        datos = jwt.decode(cuerpo["access_token"], seguridad.secreto, algorithms=["HS256"])
        assert datos["rol"] == rol
        assert datos["exp"] - datos["iat"] == 1800
        assert set(datos) == {"sub", "rol", "iat", "exp"}
        verificado = await c.get("/privado", headers={"Authorization": "Bearer " + cuerpo["access_token"]})
        assert verificado.status_code == 200
        assert verificado.json() == {"id": int(datos["sub"]), "rol": rol}
    ejecutar(app_segura, comprobar)


def test_error_credenciales_indistinguible(app_segura, cuenta):
    async def comprobar(c):
        respuestas = []
        for nombre, clave in [("no_existe", cuenta[0]), ("prueba_admin", cuenta[0] + "x"), ("prueba_admin", "é" * 37)]:
            r = await c.post("/login", json={"usuario": nombre, "clave": clave})
            assert r.status_code == 401
            assert r.headers["www-authenticate"] == "Bearer"
            respuestas.append(r.json())
        assert respuestas == [{"error": "Usuario o clave incorrectos", "detalles": []}] * 3
    ejecutar(app_segura, comprobar)


@pytest.mark.parametrize("encabezado", [None, "Basic invalido", "Bearer", "Bearer no-es-jwt"])
def test_bearer_faltante_o_invalido(app_segura, encabezado):
    async def comprobar(c):
        r = await c.get("/privado", headers={"Authorization": encabezado} if encabezado else {})
        assert r.status_code == 401
        assert set(r.json()) == {"error", "detalles"}
        assert r.headers["www-authenticate"] == "Bearer"
    ejecutar(app_segura, comprobar)


@pytest.mark.parametrize("caso", ["alterado", "vencido", "otra_firma", "otro_algoritmo", "sin_firma", "sin_exp", "sin_rol", "rol_falso", "sub_invalido", "exp_texto", "futuro"])
def test_token_rechazado_por_http(app_segura, seguridad, caso):
    ahora = datetime.now(timezone.utc)
    datos = {"sub": "2", "rol": "cliente", "iat": ahora, "exp": ahora + timedelta(minutes=30)}
    algoritmo, clave = "HS256", seguridad.secreto
    if caso == "vencido":
        datos.update(iat=ahora - timedelta(hours=1), exp=ahora - timedelta(seconds=1))
    elif caso == "otra_firma": clave = secrets.token_urlsafe(48)
    elif caso == "otro_algoritmo": algoritmo = "HS384"
    elif caso == "sin_firma": algoritmo, clave = "none", None
    elif caso == "sin_exp": del datos["exp"]
    elif caso == "sin_rol": del datos["rol"]
    elif caso == "rol_falso": datos["rol"] = "superadmin"
    elif caso == "sub_invalido": datos["sub"] = "-1"
    elif caso == "exp_texto": datos["exp"] = "9999999999"
    elif caso == "futuro": datos["iat"] = ahora + timedelta(hours=1)
    token = jwt.encode(datos, clave, algorithm=algoritmo)
    if caso == "alterado":
        token = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]
    async def comprobar(c):
        r = await c.get("/privado", headers={"Authorization": "Bearer " + token})
        assert r.status_code == 401
        assert r.json() == {"error": "El token no es válido o ya expiró", "detalles": []}
    ejecutar(app_segura, comprobar)


def test_hash_con_sal_y_limites_utf8(cuenta):
    otro = proteger_clave(cuenta[0])
    assert cuenta[1] != otro
    assert comprobar_clave(cuenta[0], otro)
    assert not comprobar_clave(cuenta[0] + "x", otro)
    assert not comprobar_clave(cuenta[0], "hash-corrupto")
    for clave in ["corta", "é" * 37]:
        with pytest.raises(ValueError): proteger_clave(clave)


def test_configuracion_no_tiene_secreto_predeterminado(monkeypatch):
    monkeypatch.delenv("JWT_SECRETO", raising=False)
    with pytest.raises(RuntimeError): secreto_desde_entorno()
    monkeypatch.setenv("JWT_SECRETO", "REEMPLAZAR_CON_SECRETO_ALEATORIO_DE_AL_MENOS_32_BYTES")
    with pytest.raises(RuntimeError): secreto_desde_entorno()
    secreto = secrets.token_urlsafe(48)
    monkeypatch.setenv("JWT_SECRETO", secreto)
    assert secreto_desde_entorno() == secreto


def test_validacion_login_y_openapi(app_segura):
    async def comprobar(c):
        for cuerpo, codigo in [('{}', 422), ('{"usuario":', 400), ('{"usuario": 1, "clave": true}', 422)]:
            r = await c.post("/login", content=cuerpo, headers={"Content-Type": "application/json"})
            assert r.status_code == codigo
            assert set(r.json()) == {"error", "detalles"}
        esquema = (await c.get("/openapi.json")).json()
        assert esquema["components"]["securitySchemes"]["BearerJWT"] == {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        assert esquema["paths"]["/privado"]["get"]["security"] == [{"BearerJWT": []}]
        assert "security" not in esquema["paths"]["/login"]["post"]
        assert "401" in esquema["paths"]["/login"]["post"]["responses"]
        assert esquema["paths"]["/productos"]["post"]["security"] == [{"BearerJWT": []}]
    ejecutar(app_segura, comprobar)


def test_creacion_cuentas_solo_desarrollo(monkeypatch):
    from scripts.crear_usuarios_desarrollo import preparar_cuentas
    monkeypatch.setenv("KATEA_ENTORNO", "produccion")
    def no_leer(_): pytest.fail("No debe pedir claves fuera de desarrollo")
    with pytest.raises(RuntimeError): preparar_cuentas(no_leer)
    monkeypatch.setenv("KATEA_ENTORNO", "desarrollo")
    valores = iter(["solo-pruebas-efimeras"] * 6)
    cuentas = preparar_cuentas(lambda _: next(valores))
    assert [(n, r) for n, _, r in cuentas] == [("dev_admin", "admin"), ("dev_cliente1", "cliente"), ("dev_cliente2", "cliente")]
    assert len({h for _, h, _ in cuentas}) == 3
    assert all(comprobar_clave("solo-pruebas-efimeras", h) for _, h, _ in cuentas)
