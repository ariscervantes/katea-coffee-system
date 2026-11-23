"""Conexión a MySQL y creación del esquema de productos."""

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor


load_dotenv(Path(__file__).with_name(".env"))

ESQUEMA_PRODUCTOS = """
CREATE TABLE IF NOT EXISTS productos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(80) NOT NULL,
    nombre_normalizado VARCHAR(320)
        CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    descripcion VARCHAR(200) NOT NULL,
    precio DECIMAL(65, 2) NOT NULL,
    imagen_url TEXT NOT NULL,
    disponible BOOLEAN NOT NULL,
    preparacion ENUM('frio', 'caliente', 'no_aplica') NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_productos_nombre_preparacion (nombre_normalizado, preparacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


@dataclass(frozen=True)
class ConfiguracionBD:
    host: str
    puerto: int
    usuario: str
    contrasena: str
    nombre: str

    @classmethod
    def desde_entorno(cls) -> "ConfiguracionBD":
        variables = {
            "DB_HOST": os.getenv("DB_HOST"),
            "DB_PORT": os.getenv("DB_PORT"),
            "DB_USER": os.getenv("DB_USER"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
            "DB_NAME": os.getenv("DB_NAME"),
        }
        faltantes = [nombre for nombre, valor in variables.items() if valor in (None, "")]
        if faltantes:
            raise RuntimeError(
                "Faltan variables de conexión a MySQL: " + ", ".join(faltantes)
                + ". Copia .env.example como .env y completa los datos."
            )
        try:
            puerto = int(variables["DB_PORT"])
        except ValueError:
            raise RuntimeError("DB_PORT debe ser un número entero") from None
        return cls(
            host=variables["DB_HOST"],
            puerto=puerto,
            usuario=variables["DB_USER"],
            contrasena=variables["DB_PASSWORD"],
            nombre=variables["DB_NAME"],
        )


class BaseDatos:
    """Abre una conexión por operación y administra su transacción."""

    def __init__(self, configuracion: ConfiguracionBD | None = None) -> None:
        self._configuracion = configuracion

    @property
    def configuracion(self) -> ConfiguracionBD:
        if self._configuracion is None:
            self._configuracion = ConfiguracionBD.desde_entorno()
        return self._configuracion

    @contextmanager
    def conexion(self) -> Iterator[DictCursor]:
        config = self.configuracion
        conexion = pymysql.connect(
            host=config.host,
            port=config.puerto,
            user=config.usuario,
            password=config.contrasena,
            database=config.nombre,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=5,
        )
        try:
            with conexion.cursor() as cursor:
                yield cursor
            conexion.commit()
        except BaseException:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def inicializar(self) -> None:
        """Crea la tabla si todavía no existe (DDL fijo, sin datos externos)."""
        with self.conexion() as cursor:
            cursor.execute(ESQUEMA_PRODUCTOS)
