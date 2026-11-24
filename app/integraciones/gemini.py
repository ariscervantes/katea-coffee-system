"""Cliente de Gemini: pieza 7b (servicio externo) de "Anatomía de una API REST".

Responde 503 si falta GEMINI_API_KEY, 504 si la IA tarda más que EXTERNO_TIMEOUT
y 502 si falla o contesta algo inesperado. Reintenta una vez solo ante 429/5xx.
"""

import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from dotenv import load_dotenv
from fastapi import HTTPException


# app/integraciones/gemini.py -> parents[2] es la raíz del proyecto, donde vive .env.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

URL_GEMINI = "https://generativelanguage.googleapis.com"
TIMEOUT_POR_OMISION = 5.0


def _timeout_desde_entorno() -> float:
    """Lee EXTERNO_TIMEOUT; si falta, no es número o no es positivo, usa 5 segundos."""
    try:
        segundos = float(os.environ.get("EXTERNO_TIMEOUT", TIMEOUT_POR_OMISION))
    except ValueError:
        return TIMEOUT_POR_OMISION
    return segundos if segundos > 0 else TIMEOUT_POR_OMISION


# Único lugar donde se leen las variables del servicio externo. La clave nunca va en el código.
IA_URL = os.environ.get("EXTERNO_URL", URL_GEMINI)
IA_MODELO = os.environ.get("GEMINI_MODELO", "gemini-flash-lite-latest")
IA_CLAVE = os.environ.get("GEMINI_API_KEY", "")
IA_TIMEOUT = _timeout_desde_entorno()


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
        try:
            with urllib.request.urlopen(req, timeout=IA_TIMEOUT) as r:   # Límite de espera por intento.
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
