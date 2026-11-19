"""Pruebas de acceso CORS desde el front local."""

import asyncio

import httpx

from main import crear_app


def test_cors_permite_origen_local_y_preflight(repositorio_falso, monkeypatch):
    monkeypatch.delenv("CORS_ORIGENES", raising=False)
    app = crear_app(repositorio_falso)

    async def comprobar():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as cliente:
            respuesta = await cliente.get(
                "/productos", headers={"Origin": "http://127.0.0.1:5500"}
            )
            assert respuesta.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"

            ajeno = await cliente.get(
                "/productos", headers={"Origin": "http://sitio-ajeno.example"}
            )
            assert "access-control-allow-origin" not in ajeno.headers

            preflight = await cliente.options(
                "/productos",
                headers={
                    "Origin": "http://127.0.0.1:5500",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization, content-type",
                },
            )
            assert preflight.status_code == 200
            assert "authorization" in preflight.headers["access-control-allow-headers"].lower()

    asyncio.run(comprobar())
