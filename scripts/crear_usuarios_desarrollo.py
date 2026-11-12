#!/usr/bin/env python3
"""Crea tres cuentas locales por solicitud explícita, sin imprimir credenciales."""

from getpass import getpass
import os
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import pymysql

from autenticacion import proteger_clave
from usuarios import RepositorioUsuarios

CUENTAS = (("dev_admin", "admin"), ("dev_cliente1", "cliente"), ("dev_cliente2", "cliente"))


def preparar_cuentas(leer_clave=getpass):
    if os.getenv("KATEA_ENTORNO") != "desarrollo":
        raise RuntimeError("Este comando requiere KATEA_ENTORNO=desarrollo y una base de desarrollo")
    cuentas = []
    for nombre, rol in CUENTAS:
        clave = leer_clave(f"Clave exclusiva de pruebas para {nombre} (sin eco): ")
        confirmacion = leer_clave("Repetir clave (sin eco): ")
        if clave != confirmacion:
            raise ValueError("Las claves no coinciden; no se creó ninguna cuenta")
        cuentas.append((nombre, proteger_clave(clave), rol))
    return cuentas


def main() -> int:
    try:
        cuentas = preparar_cuentas()
        repositorio = RepositorioUsuarios()
        repositorio.inicializar()
        repositorio.crear_cuentas_desarrollo(cuentas)
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except pymysql.err.IntegrityError:
        print("No se crearon cuentas: un nombre ya existe o hay un conflicto. No se reemplazaron datos.", file=sys.stderr)
        return 1
    except pymysql.MySQLError:
        print("No se pudo completar la operación en MySQL. Revisa la configuración local.", file=sys.stderr)
        return 1
    print("Creadas dev_admin (admin), dev_cliente1 y dev_cliente2 (cliente). No se muestran sus claves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
