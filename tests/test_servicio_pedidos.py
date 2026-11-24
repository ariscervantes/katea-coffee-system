"""Reglas de pedidos probadas sin HTTP: funciones puras del servicio y rollback del repositorio."""

from decimal import Decimal, localcontext
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

from pydantic import ValidationError
import pytest

from almacen_pedidos import AlmacenAislado
from app.db.conexion import BaseDatos, ConfiguracionBD
from app.modelos.pedidos import PedidoEntrada
from app.repositorios.pedidos import RepositorioPedidos
from app.servicios.pedidos import (
    MAX_IMPORTE, ImporteFueraDeRango, PedidoNoEncontrado, ProductoNoDisponible, ProductoPedidoInexistente,
    ProductoRepetido, RespuestaIAInvalida, consultar_pedido, eliminar_pedido, listar_pedidos,
    precio_de_compra, sumar_al_total, validar_respuesta_ia, verificar_productos_unicos,
)


def test_producto_no_disponible_se_rechaza():
    with pytest.raises(ProductoNoDisponible):
        precio_de_compra({"id": 2, "precio": "5.00", "disponible": 0})


def test_producto_inexistente_se_rechaza():
    with pytest.raises(ProductoPedidoInexistente):
        precio_de_compra(None)


def test_precio_historico_es_decimal_exacto():
    assert precio_de_compra({"id": 1, "precio": Decimal("10.10"), "disponible": 1}) == Decimal("10.10")


def test_lista_vacia_se_rechaza_antes_de_llegar_al_servicio():
    with pytest.raises(ValidationError):
        PedidoEntrada(productos=[])


def test_producto_repetido_se_rechaza():
    with pytest.raises(ProductoRepetido):
        verificar_productos_unicos([1, 3, 1])
    verificar_productos_unicos([1, 3])
    with pytest.raises(ValidationError, match="Cada producto debe aparecer una sola vez"):
        PedidoEntrada(productos=[{"producto_id": 1, "cantidad": 1}] * 2)


def test_total_con_dos_decimales_sin_errores_de_float():
    total = Decimal("0.00")
    total = sumar_al_total(total, Decimal("10.10"), 2)
    total = sumar_al_total(total, Decimal("0.10"), 3)
    assert total == Decimal("20.50")
    assert format(total, ".2f") == "20.50" and total.as_tuple().exponent == -2


def test_total_no_puede_pasar_el_tope():
    with localcontext() as contexto:
        contexto.prec = 90  # Con 28 dígitos, MAX_IMPORTE - 1 se redondearía hacia arriba.
        casi_tope = MAX_IMPORTE - 1
    assert sumar_al_total(casi_tope, Decimal("1.00"), 1) == MAX_IMPORTE
    with pytest.raises(ImporteFueraDeRango):
        sumar_al_total(MAX_IMPORTE, Decimal("0.01"), 1)


def test_rollback_si_un_producto_no_esta_disponible(monkeypatch):
    almacen = AlmacenAislado()
    monkeypatch.setattr("app.db.conexion.pymysql.connect", almacen.conectar)
    repo = RepositorioPedidos(BaseDatos(ConfiguracionBD("aislado", 3306, "prueba", "solo-pruebas", "aislado")))
    entrada = PedidoEntrada(productos=[{"producto_id": 1, "cantidad": 1}, {"producto_id": 2, "cantidad": 1}])
    with pytest.raises(ProductoNoDisponible):
        repo.crear(entrada, usuario_id=2)
    assert almacen.rollbacks == 1 and almacen.commits == 0
    assert almacen.conteo("pedidos") == almacen.conteo("pedido_detalles") == 0
    almacen.db.close()


def test_admin_ve_todos_y_cliente_solo_los_propios():
    repo = Mock(spec=RepositorioPedidos)
    listar_pedidos(repo, 1, "admin")
    repo.listar_todos.assert_called_once_with()
    listar_pedidos(repo, 2, "cliente")
    repo.listar_propios.assert_called_once_with(2)


def test_pedido_ajeno_o_inexistente_no_se_encuentra():
    repo = Mock(spec=RepositorioPedidos)
    repo.obtener_propio.return_value = None
    repo.eliminar_propio.return_value = False
    with pytest.raises(PedidoNoEncontrado):
        consultar_pedido(repo, 5, 2, "cliente")
    with pytest.raises(PedidoNoEncontrado):
        eliminar_pedido(repo, 5, 2, "cliente")
    repo.obtener_propio.assert_called_once_with(5, 2)
    repo.obtener_cualquiera.assert_not_called()


def test_respuesta_ia_valida_se_limpia_y_recorta():
    assert validar_respuesta_ia({"sentimiento": "positivo", "respuesta": "  Gracias  "}) == {
        "sentimiento": "positivo", "respuesta": "Gracias",
    }
    assert len(validar_respuesta_ia({"sentimiento": "neutral", "respuesta": "x" * 250})["respuesta"]) == 200


@pytest.mark.parametrize("ia", [
    ["no es dict"], {"sentimiento": "feliz", "respuesta": "ok"},
    {"sentimiento": "neutral", "respuesta": "   "}, {"sentimiento": "neutral", "respuesta": 5}, {},
])
def test_respuesta_ia_invalida_se_rechaza(ia):
    with pytest.raises(RespuestaIAInvalida):
        validar_respuesta_ia(ia)


def test_servicio_no_depende_de_fastapi():
    raiz = Path(__file__).resolve().parents[1]
    codigo = "import sys, app.servicios.pedidos; assert 'fastapi' not in sys.modules"
    subprocess.run([sys.executable, "-c", codigo], cwd=raiz, check=True)
