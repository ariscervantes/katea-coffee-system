"""Pruebas del modelo, errores y registro de las rutas de productos."""

import asyncio
import math

import httpx
import pytest
from pydantic import ValidationError

from main import app, crear_app
from modelos import ProductoEntrada


def datos_validos():
    return {
        "nombre": "Matcha latte",
        "descripcion": "Bebida de té matcha con leche.",
        "precio": 65.5,
        "imagen_url": "/imagenes/matcha.jpg",
        "disponible": True,
        "preparacion": "frio",
    }


def test_normalizacion_y_serializacion():
    datos = datos_validos() | {"nombre": "  Matcha latte  ", "descripcion": "  Bebida de matcha  "}
    producto = ProductoEntrada.model_validate(datos)
    assert producto.nombre == "Matcha latte"
    assert producto.descripcion == "Bebida de matcha"
    assert producto.model_dump(mode="json")["precio"] == 65.5


@pytest.mark.parametrize("campo", list(datos_validos()))
def test_todos_los_campos_son_obligatorios(campo):
    datos = datos_validos()
    del datos[campo]
    with pytest.raises(ValidationError):
        ProductoEntrada.model_validate(datos)


@pytest.mark.parametrize("campo,valor", [
    ("nombre", " a "), ("nombre", "a" * 81), ("nombre", 25),
    ("descripcion", " abcd "), ("descripcion", "a" * 201), ("descripcion", False),
    ("precio", "25"), ("precio", True), ("precio", False),
    ("precio", 0), ("precio", -1), ("precio", 25.123),
    ("precio", math.inf), ("precio", math.nan),
    ("imagen_url", ""), ("imagen_url", "   "), ("imagen_url", 12),
    ("imagen_url", "foto.gif"), ("imagen_url", "foto.jpg?x=1"),
    ("imagen_url", ".jpg"),
    ("disponible", "true"), ("disponible", "false"),
    ("disponible", 1), ("disponible", 0),
    ("preparacion", "Frio"), ("preparacion", "helado"), ("preparacion", 1),
    ("id", 123),
    *[(campo, None) for campo in datos_validos()],
])
def test_rechaza_datos_invalidos(campo, valor):
    with pytest.raises(ValidationError):
        ProductoEntrada.model_validate(datos_validos() | {campo: valor})


@pytest.mark.parametrize("precio", [25, 25.0, 0.01, 25.12])
def test_precios_validos(precio):
    assert ProductoEntrada.model_validate(datos_validos() | {"precio": precio}).precio > 0


@pytest.mark.parametrize("extension", ["jpg", "jpeg", "png", "webp"])
@pytest.mark.parametrize("preparacion", ["frio", "caliente", "no_aplica"])
@pytest.mark.parametrize("disponible", [True, False])
def test_opciones_validas(extension, preparacion, disponible):
    ProductoEntrada.model_validate(datos_validos() | {
        "nombre": "ab", "descripcion": "abcde",
        "imagen_url": f"foto.{extension}",
        "preparacion": preparacion, "disponible": disponible,
    })
    ProductoEntrada.model_validate(datos_validos() | {"nombre": "a" * 80, "descripcion": "a" * 200})


def test_estan_registradas_las_cinco_operaciones_de_productos():
    operaciones = {
        (metodo.upper(), ruta)
        for ruta, operaciones in app.openapi()["paths"].items()
        if ruta.startswith("/productos")
        for metodo in operaciones
    }
    assert operaciones == {
        ("GET", "/productos"),
        ("GET", "/productos/{id}"),
        ("POST", "/productos"),
        ("PUT", "/productos/{id}"),
        ("DELETE", "/productos/{id}"),
    }


def test_contrato_documenta_los_codigos_http():
    operaciones = app.openapi()["paths"]
    esperados = {
        ("get", "/productos"): {200, 500},
        ("get", "/productos/{id}"): {200, 404, 422, 500},
        ("post", "/productos"): {201, 400, 409, 422, 500},
        ("put", "/productos/{id}"): {200, 400, 404, 409, 422, 500},
        ("delete", "/productos/{id}"): {204, 404, 422, 500},
    }
    for (metodo, ruta), codigos in esperados.items():
        documentados = {int(codigo) for codigo in operaciones[ruta][metodo]["responses"]}
        assert codigos <= documentados


def test_errores_http(repositorio_falso):
    temporal = crear_app(repositorio_falso)

    @temporal.post("/validar")
    async def validar(producto: ProductoEntrada):
        return producto

    async def comprobar():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=temporal), base_url="http://test") as cliente:
            correcto = await cliente.post("/validar", json=datos_validos())
            assert correcto.status_code == 200
            assert isinstance(correcto.json()["precio"], (int, float))
            for cuerpo, codigo in [(' {"nombre": ', 400), ('{}', 422), ('[]', 422), ('null', 422)]:
                respuesta = await cliente.post("/validar", content=cuerpo, headers={"Content-Type": "application/json"})
                assert respuesta.status_code == codigo
                assert set(respuesta.json()) == {"error", "detalles"}
                assert isinstance(respuesta.json()["detalles"], list)
                assert respuesta.json()["detalles"]
            invalido = await cliente.post("/validar", json=datos_validos() | {"precio": "25"})
            assert invalido.status_code == 422
            assert invalido.json()["detalles"][0]["campo"] == ["body", "precio"]
            inexistente = await cliente.get("/no-existe")
            assert inexistente.status_code == 404
            assert set(inexistente.json()) == {"error", "detalles"}

    asyncio.run(comprobar())
