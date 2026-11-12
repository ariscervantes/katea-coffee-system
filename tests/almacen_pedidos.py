"""Adaptador SQL exclusivamente de pruebas, en memoria y con transacciones reales.

Ejecuta las consultas del repositorio traduciendo %s a ? y quitando FOR UPDATE.
No pretende validar DDL, bloqueo ni concurrencia de MySQL/InnoDB.
"""

from decimal import Decimal
import sqlite3

import pymysql


class AlmacenAislado:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.consultas = []
        self.commits = 0
        self.rollbacks = 0
        self.cierres = 0
        self.fallar_detalle = None
        self.detalles_insertados = 0
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE usuarios (id INTEGER PRIMARY KEY);
            INSERT INTO usuarios VALUES (1), (2), (3);
            CREATE TABLE productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, nombre_normalizado TEXT,
                descripcion TEXT, precio TEXT NOT NULL, imagen_url TEXT,
                disponible INTEGER NOT NULL, preparacion TEXT
            );
            CREATE TABLE pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
                estado TEXT NOT NULL, total TEXT NOT NULL
            );
            CREATE TABLE pedido_detalles (
                pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                producto_id INTEGER REFERENCES productos(id) ON DELETE RESTRICT,
                cantidad INTEGER NOT NULL, precio_unitario TEXT NOT NULL,
                PRIMARY KEY (pedido_id, producto_id)
            );
        """)
        for id, precio, disponible in [(1, "10.10", 1), (2, "5.00", 0), (3, "0.20", 1)]:
            self.db.execute(
                "INSERT INTO productos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (id, f"Producto {id}", f"producto {id}", "Descripción de prueba", precio, "foto.png", disponible, "frio"),
            )
        self.db.commit()

    def conectar(self, **_):
        return Conexion(self)

    def conteo(self, tabla):
        # Solo nombres fijos internos de la prueba; nunca vienen de HTTP.
        assert tabla in ("pedidos", "pedido_detalles")
        return self.db.execute("SELECT COUNT(*) FROM " + tabla).fetchone()[0]


class Conexion:
    def __init__(self, almacen):
        self.almacen = almacen

    def cursor(self):
        return Cursor(self.almacen)

    def commit(self):
        self.almacen.db.commit()
        self.almacen.commits += 1

    def rollback(self):
        self.almacen.db.rollback()
        self.almacen.rollbacks += 1

    def close(self):
        self.almacen.cierres += 1


class Cursor:
    def __init__(self, almacen):
        self.almacen = almacen
        self.cursor = almacen.db.cursor()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cursor.close()

    def execute(self, consulta, parametros=()):
        self.almacen.consultas.append((consulta, parametros))
        if consulta.startswith("INSERT INTO pedido_detalles"):
            self.almacen.detalles_insertados += 1
            if self.almacen.detalles_insertados == self.almacen.fallar_detalle:
                raise pymysql.err.OperationalError(2013, "Fallo simulado al insertar un detalle")
        valores = tuple(str(v) if isinstance(v, Decimal) else v for v in parametros)
        try:
            return self.cursor.execute(consulta.replace("%s", "?").replace(" FOR UPDATE", ""), valores)
        except sqlite3.IntegrityError:
            codigo = 1451 if consulta.startswith("DELETE") else 1452
            raise pymysql.err.IntegrityError(codigo, "Restricción simulada") from None

    def fetchone(self):
        fila = self.cursor.fetchone()
        return dict(fila) if fila else None

    def fetchall(self):
        return [dict(f) for f in self.cursor.fetchall()]

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        return self.cursor.lastrowid
