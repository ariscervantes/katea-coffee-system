"""Contrato SQL y transacciones con conexión simulada; no toca datos reales."""

from unittest.mock import MagicMock

import pymysql
import pytest

from basedatos import BaseDatos, ConfiguracionBD
from usuarios import ESQUEMA_USUARIOS, RepositorioUsuarios


@pytest.fixture
def sql(monkeypatch):
    conexion = MagicMock()
    cursor = conexion.cursor.return_value.__enter__.return_value
    monkeypatch.setattr("basedatos.pymysql.connect", lambda **_: conexion)
    base = BaseDatos(ConfiguracionBD("aislado", 3306, "prueba", "no-es-una-credencial-real", "prueba"))
    return RepositorioUsuarios(base), conexion, cursor


def test_busqueda_parametrizada_y_conversion(sql):
    repo, conexion, cursor = sql
    nombre = "nombre' OR '1'='1"
    cursor.fetchone.return_value = {"id": 7, "usuario": nombre, "clave_hash": "hash-simulado", "rol": "cliente"}
    usuario = repo.buscar(nombre)
    consulta, parametros = cursor.execute.call_args.args
    assert nombre not in consulta
    assert "WHERE usuario = %s" in consulta
    assert parametros == (nombre,)
    assert usuario.id == 7 and usuario.rol == "cliente"
    assert "hash-simulado" not in repr(usuario)
    conexion.commit.assert_called_once()
    conexion.close.assert_called_once()
    cursor.fetchone.return_value = None
    assert repo.buscar("ausente") is None


def test_busqueda_por_id_parametrizada(sql):
    repo, conexion, cursor = sql
    cursor.fetchone.return_value = {"id": 7, "usuario": "cliente", "clave_hash": "hash-simulado", "rol": "cliente"}
    usuario = repo.obtener(7)
    consulta, parametros = cursor.execute.call_args.args
    assert "WHERE id = %s" in consulta
    assert parametros == (7,)
    assert usuario.id == 7 and usuario.usuario == "cliente"
    conexion.commit.assert_called_once()
    conexion.close.assert_called_once()
    cursor.fetchone.return_value = None
    assert repo.obtener(999) is None


def test_creacion_tabla_sin_semillas(sql):
    repo, _, cursor = sql
    repo.inicializar()
    cursor.execute.assert_called_once_with(ESQUEMA_USUARIOS)
    assert "INSERT" not in ESQUEMA_USUARIOS
    assert "UNIQUE" in ESQUEMA_USUARIOS


def test_cuentas_insertan_solo_hashes_y_hacen_commit(sql):
    repo, conexion, cursor = sql
    cuentas = [("dev_admin", "hash-a", "admin"), ("dev_cliente1", "hash-b", "cliente"), ("dev_cliente2", "hash-c", "cliente")]
    repo.crear_cuentas_desarrollo(cuentas)
    assert cursor.execute.call_count == 3
    for llamada, cuenta in zip(cursor.execute.call_args_list, cuentas):
        consulta, parametros = llamada.args
        assert "VALUES (%s, %s, %s)" in consulta
        assert parametros == cuenta
        assert "UPDATE" not in consulta and "IGNORE" not in consulta
    conexion.commit.assert_called_once()
    conexion.rollback.assert_not_called()
    conexion.close.assert_called_once()


def test_conflicto_revierte_transaccion_sin_sobrescribir(sql):
    repo, conexion, cursor = sql
    cursor.execute.side_effect = [None, pymysql.err.IntegrityError(1062, "Duplicado simulado")]
    with pytest.raises(pymysql.err.IntegrityError):
        repo.crear_cuentas_desarrollo([("dev_admin", "hash-a", "admin"), ("dev_cliente1", "hash-b", "cliente")])
    conexion.commit.assert_not_called()
    conexion.rollback.assert_called_once()
    conexion.close.assert_called_once()
