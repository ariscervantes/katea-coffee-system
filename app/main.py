"""Punto de entrada: python -m uvicorn app.main:app --reload."""

from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.seguridad import Autenticacion
from app.repositorios.usuarios import RepositorioUsuarios
from app.errores import registrar_manejadores
from app.repositorios.productos import RepositorioProductos
from app.repositorios.pedidos import RepositorioPedidos
from app.routers.auth import rutas_auth
from app.routers.pedidos import rutas_pedidos
from app.routers.productos import rutas_productos

# ---------- Preguntarle algo a la IA (péguenlo una vez, arriba de sus rutas) ----------
import json, os, urllib.request, urllib.error


IA_URL = os.environ.get("EXTERNO_URL", "https://generativelanguage.googleapis.com")
IA_MODELO = os.environ.get("GEMINI_MODELO", "gemini-flash-lite-latest")
IA_CLAVE = os.environ.get("GEMINI_API_KEY", "")         # IDEA 3: la clave NO va en el código


def _fallo_transitorio(codigo: int) -> bool:
    """Solo se reintentan fallos que podrían resolverse solos; un 400 no se repite."""
    return codigo == 429 or 500 <= codigo < 600


def preguntar_a_la_ia(instruccion: str) -> dict:
    """Le pregunta algo a Gemini y regresa el JSON que contestó. Si algo sale mal, responde 502/503/504."""
    if not IA_CLAVE and "googleapis.com" in IA_URL:
        raise HTTPException(503, "Falta configurar la variable de entorno GEMINI_API_KEY")
    cuerpo = {"contents": [{"parts": [{"text": instruccion}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    datos = json.dumps(cuerpo).encode()
    for intento in range(2):                                     # Un reintento ante fallos transitorios.
        req = urllib.request.Request(f"{IA_URL}/v1beta/models/{IA_MODELO}:generateContent",
                                     data=datos, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": IA_CLAVE})
        try:                                                     # IDEA 1: su API llama a otra API
            with urllib.request.urlopen(req, timeout=5) as r:    # IDEA 2: máximo 5 segundos esperando
                respuesta = json.loads(r.read())
            return json.loads(respuesta["candidates"][0]["content"]["parts"][0]["text"])
        except TimeoutError:
            raise HTTPException(504, "La IA tardó demasiado en responder. Intenta en un momento.")
        except urllib.error.HTTPError as e:
            if intento == 0 and _fallo_transitorio(e.code):
                continue
            raise HTTPException(502, f"La IA no está disponible (respondió {e.code}). Intenta más tarde.")
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise HTTPException(504, "La IA tardó demasiado en responder. Intenta en un momento.")
            if intento == 0:
                continue
            raise HTTPException(502, "No se pudo conectar con la IA.")
        except (ValueError, KeyError, IndexError, TypeError):
            raise HTTPException(502, "La IA respondió algo que no entendemos.")
    raise HTTPException(502, "La IA no está disponible. Intenta más tarde.")



def crear_app(
    repositorio: RepositorioProductos | None = None,
    usuarios: RepositorioUsuarios | None = None,
    autenticacion: Autenticacion | None = None,
    pedidos: RepositorioPedidos | None = None,
    preguntar_ia: Callable[[str], dict] | None = None,
) -> FastAPI:
    almacen = repositorio or RepositorioProductos()

    cuentas = usuarios if usuarios is not None else RepositorioUsuarios()
    seguridad = autenticacion if autenticacion is not None else Autenticacion(cuentas)
    ordenes = pedidos if pedidos is not None else RepositorioPedidos()
    consultar_ia = preguntar_ia if preguntar_ia is not None else preguntar_a_la_ia

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI):
        almacen.inicializar()
        cuentas.inicializar()
        ordenes.inicializar()
        yield

    app = FastAPI(title="Katea — API de productos", version="1.0.0", lifespan=ciclo_vida)
    # No usar "*": el navegador debe limitar el acceso a los orígenes del front.
    origenes_cors = os.environ.get(
        "CORS_ORIGENES", "http://127.0.0.1:5500,http://localhost:5500"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origen.strip() for origen in origenes_cors.split(",") if origen.strip()],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    registrar_manejadores(app)
    app.state.autenticacion = seguridad
    app.include_router(rutas_pedidos(ordenes, cuentas, consultar_ia))
    app.include_router(rutas_auth(seguridad))
    app.include_router(rutas_productos(almacen))

    return app


app = crear_app()
