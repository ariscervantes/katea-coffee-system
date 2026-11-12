"""Rutas y repositorio reales con SQL aislado: no conecta a MySQL."""

import asyncio
from decimal import Decimal, localcontext
import json
from pathlib import Path
import secrets
from unittest.mock import MagicMock, Mock

import httpx
import pytest

from almacen_pedidos import AlmacenAislado
from autenticacion import Autenticacion
from basedatos import BaseDatos, ConfiguracionBD
from main import crear_app
from modelos_pedidos import PedidoEntrada
from repositorio import RepositorioProductos
from repositorio_pedidos import (
    ESQUEMA_DETALLES, ESQUEMA_PEDIDOS, MAX_IMPORTE, RepositorioPedidos,
)
from usuarios import RepositorioUsuarios, Usuario

VALIDO = {"productos": [{"producto_id": 1, "cantidad": 2}, {"producto_id": 3, "cantidad": 3}]}


@pytest.fixture
def escenario(monkeypatch):
    almacen = AlmacenAislado()
    monkeypatch.setattr("basedatos.pymysql.connect", almacen.conectar)
    base = BaseDatos(ConfiguracionBD("aislado", 3306, "prueba", "solo-pruebas", "aislado"))
    repo = RepositorioPedidos(base)
    usuarios = Mock(spec=RepositorioUsuarios)
    seguridad = Autenticacion(usuarios, secrets.token_urlsafe(48))
    app = crear_app(RepositorioProductos(base), usuarios, seguridad, pedidos=repo)
    encabezados = {
        nombre: {"Authorization": "Bearer " + seguridad.crear_token(Usuario(id, nombre, "", rol))}
        for nombre, id, rol in [("admin", 1, "admin"), ("A", 2, "cliente"), ("B", 3, "cliente")]
    }
    yield app, almacen, repo, encabezados
    almacen.db.close()


def ejecutar(app, funcion):
    async def consultar():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as c:
            await funcion(c)
    asyncio.run(consultar())


@pytest.mark.parametrize("nombre,dueno", [("A", 2), ("B", 3), ("admin", 1)])
def test_creacion_total_y_precio_historico(escenario, nombre, dueno):
    app, almacen, _, h = escenario
    async def comprobar(c):
        r = await c.post("/pedidos", json=VALIDO, headers=h[nombre])
        assert r.status_code == 201
        pedido = r.json()
        assert pedido == {"id": pedido["id"], "usuario_id": dueno, "estado": "pendiente", "total": "20.80", "productos": [
            {"producto_id": 1, "cantidad": 2, "precio_unitario": "10.10"},
            {"producto_id": 3, "cantidad": 3, "precio_unitario": "0.20"},
        ]}
        assert almacen.conteo("pedidos") == 1 and almacen.conteo("pedido_detalles") == 2
        assert almacen.commits == 1 and almacen.rollbacks == 0
        # Cambio del catálogo: el pedido conserva precio y total de compra.
        almacen.db.execute("UPDATE productos SET precio = '99.00' WHERE id = 1")
        almacen.db.commit()
        consultado = await c.get(f'/pedidos/{pedido["id"]}', headers=h[nombre])
        assert consultado.json() == pedido
    ejecutar(app, comprobar)


@pytest.mark.parametrize("cuerpo", [
    {}, {"productos": []}, {"productos": None},
    *[{"productos": [{"producto_id": 1, "cantidad": v}]} for v in [0, -1, 1.5, True, "2", 4294967296, None]],
    {"productos": [{"producto_id": True, "cantidad": 1}]},
    {"productos": [{"producto_id": "1", "cantidad": 1}]},
    {"productos": [{"producto_id": 1, "cantidad": 1}] * 2},
    *[VALIDO | {campo: 3} for campo in ["usuario_id", "dueno", "dueño", "total", "precio", "estado"]],
    {"productos": [{"producto_id": 1, "cantidad": 1, "precio_unitario": 0.01}]},
])
def test_entrada_invalida_no_crea_pedido(escenario, cuerpo):
    app, almacen, _, h = escenario
    async def comprobar(c):
        r = await c.post("/pedidos", json=cuerpo, headers=h["A"])
        assert r.status_code == 422
        assert set(r.json()) == {"error", "detalles"}
        assert almacen.conteo("pedidos") == almacen.conteo("pedido_detalles") == 0
        assert almacen.consultas == []
    ejecutar(app, comprobar)


@pytest.mark.parametrize("producto,codigo,mensaje", [(99999, 422, "Producto no encontrado"), (2, 409, "Producto no disponible")])
def test_validacion_catalogo_revierte(escenario, producto, codigo, mensaje):
    app, almacen, _, h = escenario
    async def comprobar(c):
        r = await c.post("/pedidos", json={"productos": [{"producto_id": 1, "cantidad": 1}, {"producto_id": producto, "cantidad": 1}]}, headers=h["A"])
        assert r.status_code == codigo
        assert r.json() == {"error": mensaje, "detalles": []}
        assert almacen.conteo("pedidos") == almacen.conteo("pedido_detalles") == 0
        assert almacen.rollbacks == 1
    ejecutar(app, comprobar)


def test_propiedad_y_admin_en_listado_consulta_y_borrado(escenario):
    app, almacen, _, h = escenario
    async def comprobar(c):
        a = (await c.post("/pedidos", json=VALIDO, headers=h["A"])).json()
        b = (await c.post("/pedidos", json=VALIDO, headers=h["B"])).json()
        assert a["usuario_id"] == 2 and b["usuario_id"] == 3
        for nombre, propio, ajeno in [("A", a, b), ("B", b, a)]:
            assert (await c.get("/pedidos", headers=h[nombre])).json() == [propio]
            assert (await c.get(f'/pedidos/{propio["id"]}', headers=h[nombre])).json() == propio
            for metodo in ["GET", "DELETE"]:
                r = await c.request(metodo, f'/pedidos/{ajeno["id"]}', headers=h[nombre])
                inexistente = await c.request(metodo, "/pedidos/999999", headers=h[nombre])
                assert r.status_code == inexistente.status_code == 404
                assert r.json() == inexistente.json() == {"error": "Pedido no encontrado", "detalles": []}
        assert almacen.conteo("pedidos") == 2
        assert (await c.get("/pedidos", headers=h["admin"])).json() == [a, b]
        for pedido in [a, b]:
            assert (await c.get(f'/pedidos/{pedido["id"]}', headers=h["admin"])).json() == pedido
        # El dueño borra el suyo; admin borra el otro.
        for pedido, nombre in [(a, "A"), (b, "admin")]:
            r = await c.delete(f'/pedidos/{pedido["id"]}', headers=h[nombre])
            assert r.status_code == 204 and r.content == b""
            assert (await c.delete(f'/pedidos/{pedido["id"]}', headers=h[nombre])).status_code == 404
        assert almacen.conteo("pedidos") == almacen.conteo("pedido_detalles") == 0
    ejecutar(app, comprobar)


@pytest.mark.parametrize("metodo,ruta", [("GET", "/pedidos"), ("GET", "/pedidos/1"), ("POST", "/pedidos"), ("DELETE", "/pedidos/1")])
@pytest.mark.parametrize("encabezado", [None, "Bearer invalido"])
def test_pedidos_exigen_sesion(escenario, metodo, ruta, encabezado):
    app, almacen, _, _ = escenario
    async def comprobar(c):
        r = await c.request(metodo, ruta, headers={"Authorization": encabezado} if encabezado else {}, **({"json": VALIDO} if metodo == "POST" else {}))
        assert r.status_code == 401
        assert r.headers["www-authenticate"] == "Bearer"
        assert set(r.json()) == {"error", "detalles"}
        assert almacen.consultas == []
    ejecutar(app, comprobar)


def test_fallo_segundo_detalle_hace_rollback_real(escenario):
    app, almacen, _, h = escenario
    almacen.fallar_detalle = 2
    async def comprobar(c):
        r = await c.post("/pedidos", json=VALIDO, headers=h["A"])
        assert r.status_code == 500
        assert r.json() == {"error": "Error interno del servidor", "detalles": []}
        # Ya se habían ejecutado INSERT del pedido y del primer detalle.
        assert almacen.detalles_insertados == 2
        assert almacen.conteo("pedidos") == almacen.conteo("pedido_detalles") == 0
        assert almacen.commits == 0 and almacen.rollbacks == 1 and almacen.cierres == 1
    ejecutar(app, comprobar)


def test_filtro_de_dueno_en_sql_y_acceso_global_explicito(escenario):
    _, almacen, repo, _ = escenario
    a = repo.crear(PedidoEntrada.model_validate(VALIDO), 2)
    repo.crear(PedidoEntrada.model_validate(VALIDO), 3)
    almacen.consultas.clear()
    repo.listar_propios(2)
    repo.obtener_propio(a.id, 2)
    repo.eliminar_propio(a.id, 3)
    for sql, parametros in almacen.consultas:
        assert "usuario_id = %s" in sql
        assert parametros[-1] in (2, 3)
    almacen.consultas.clear()
    assert len(repo.listar_todos()) == 2
    assert repo.obtener_cualquiera(a.id) is not None
    assert repo.eliminar_cualquiera(a.id)
    assert all("usuario_id = %s" not in sql for sql, _ in almacen.consultas)


def test_producto_referenciado_no_se_borra(escenario):
    app, almacen, _, h = escenario
    async def comprobar(c):
        pedido = (await c.post("/pedidos", json=VALIDO, headers=h["A"])).json()
        r = await c.delete("/productos/1", headers=h["admin"])
        assert r.status_code == 409
        assert r.json() == {"error": "El producto está asociado a un pedido", "detalles": []}
        assert almacen.conteo("pedidos") == 1 and almacen.conteo("pedido_detalles") == 2
        assert (await c.get(f'/pedidos/{pedido["id"]}', headers=h["A"])).json() == pedido
        assert (await c.delete(f'/pedidos/{pedido["id"]}', headers=h["A"])).status_code == 204
        assert (await c.delete("/productos/1", headers=h["admin"])).status_code == 204
    ejecutar(app, comprobar)


def test_precision_decimal_y_limite_del_total(escenario):
    app, almacen, _, h = escenario
    precio = "1234567890123456789012345678901234567890.12"
    almacen.db.execute("UPDATE productos SET precio = ? WHERE id = 1", (precio,))
    almacen.db.commit()
    async def comprobar(c):
        r = await c.post("/pedidos", json={"productos": [{"producto_id": 1, "cantidad": 3}]}, headers=h["A"])
        assert r.status_code == 201
        with localcontext() as contexto:
            contexto.prec = 90
            assert r.json()["total"] == format(Decimal(precio) * 3, ".2f")
        almacen.db.execute("UPDATE productos SET precio = ? WHERE id = 1", (str(MAX_IMPORTE),))
        almacen.db.commit()
        r = await c.post("/pedidos", json={"productos": [{"producto_id": 1, "cantidad": 2}]}, headers=h["A"])
        assert r.status_code == 422
        assert almacen.conteo("pedidos") == 1
    ejecutar(app, comprobar)


def test_ddl_documentado_y_contrato(escenario):
    app, _, _, _ = escenario
    base = MagicMock()
    cursor = base.conexion.return_value.__enter__.return_value
    RepositorioPedidos(base).inicializar()
    assert [c.args[0] for c in cursor.execute.call_args_list] == [ESQUEMA_PEDIDOS, ESQUEMA_DETALLES]
    raiz = Path(__file__).resolve().parents[1]
    sql = (raiz / "sql/esquema.sql").read_text()
    assert ESQUEMA_PEDIDOS.strip() in sql and ESQUEMA_DETALLES.strip() in sql
    esquema = app.openapi()
    assert esquema == json.loads((raiz / "docs/openapi.json").read_text())
    for ruta, metodo, codigos in [
        ("/pedidos", "get", ["200", "401", "500"]),
        ("/pedidos", "post", ["201", "400", "401", "409", "422", "500"]),
        ("/pedidos/{id}", "get", ["200", "401", "404", "422", "500"]),
        ("/pedidos/{id}", "delete", ["204", "401", "404", "422", "500"]),
    ]:
        operacion = esquema["paths"][ruta][metodo]
        assert operacion["security"] == [{"BearerJWT": []}]
        assert set(codigos) <= operacion["responses"].keys()
        for codigo in codigos:
            if int(codigo) >= 400:
                assert operacion["responses"][codigo]["content"]["application/json"]["schema"]["$ref"].endswith("/RespuestaError")
    entrada = esquema["components"]["schemas"]["PedidoEntrada"]
    assert entrada["additionalProperties"] is False
    assert entrada["properties"]["productos"]["minItems"] == 1
    assert esquema["components"]["schemas"]["ProductoPedidoEntrada"]["properties"]["cantidad"]["type"] == "integer"
    assert "409" in esquema["paths"]["/productos/{id}"]["delete"]["responses"]
