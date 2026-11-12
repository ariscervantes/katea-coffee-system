"""Persistencia de identidades; las contraseñas en claro nunca llegan al SQL."""

from dataclasses import dataclass, field
from typing import Literal

from basedatos import BaseDatos

Rol = Literal["admin", "cliente"]

ESQUEMA_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL UNIQUE,
    clave_hash VARCHAR(60) NOT NULL,
    rol ENUM('admin', 'cliente') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


@dataclass(frozen=True)
class Usuario:
    id: int
    usuario: str
    clave_hash: str = field(repr=False)
    rol: Rol = "cliente"


class RepositorioUsuarios:
    def __init__(self, base_datos: BaseDatos | None = None):
        self._base_datos = base_datos or BaseDatos()

    def inicializar(self) -> None:
        with self._base_datos.conexion() as cursor:
            cursor.execute(ESQUEMA_USUARIOS)

    def buscar(self, usuario: str) -> Usuario | None:
        with self._base_datos.conexion() as cursor:
            cursor.execute(
                "SELECT id, usuario, clave_hash, rol FROM usuarios WHERE usuario = %s",
                (usuario,),
            )
            fila = cursor.fetchone()
        return Usuario(**fila) if fila else None

    def crear_cuentas_desarrollo(self, cuentas: list[tuple[str, str, Rol]]) -> None:
        """Inserción atómica: si un nombre existe, rollback sin reemplazarlo."""
        with self._base_datos.conexion() as cursor:
            for usuario, clave_hash, rol in cuentas:
                cursor.execute(
                    "INSERT INTO usuarios (usuario, clave_hash, rol) VALUES (%s, %s, %s)",
                    (usuario, clave_hash, rol),
                )
