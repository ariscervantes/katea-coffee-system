"""Reintentos de la llamada externa: 5xx/429 sí, 400 y timeout no."""

from io import BytesIO
import json
import urllib.error

import pytest
from fastapi import HTTPException

import main


class RespuestaFalsa:
    def __init__(self, datos: bytes):
        self.datos = datos

    def read(self) -> bytes:
        return self.datos

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def respuesta_gemini(objeto: dict) -> bytes:
    texto = json.dumps(objeto)
    return json.dumps({"candidates": [{"content": {"parts": [{"text": texto}]}}]}).encode()


def error_http(codigo: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://externo.test", codigo, "fallo simulado", {}, BytesIO(b"{}"))


def preparar(monkeypatch, efectos):
    llamadas = []

    def urlopen(req, timeout):
        llamadas.append((req.full_url, timeout))
        efecto = efectos.pop(0)
        if isinstance(efecto, Exception):
            raise efecto
        return RespuestaFalsa(efecto)

    monkeypatch.setattr(main, "IA_URL", "http://externo.test")
    monkeypatch.setattr(main, "IA_CLAVE", "")
    monkeypatch.setattr(main.urllib.request, "urlopen", urlopen)
    return llamadas


def test_reintenta_una_vez_tras_503(monkeypatch):
    llamadas = preparar(monkeypatch, [
        error_http(503),
        respuesta_gemini({"sentimiento": "neutral", "respuesta": "Gracias"}),
    ])
    assert main.preguntar_a_la_ia("instrucción") == {"sentimiento": "neutral", "respuesta": "Gracias"}
    assert len(llamadas) == 2


def test_no_reintenta_un_400(monkeypatch):
    llamadas = preparar(monkeypatch, [error_http(400)])
    with pytest.raises(HTTPException) as error:
        main.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 502
    assert len(llamadas) == 1


def test_no_reintenta_un_timeout(monkeypatch):
    llamadas = preparar(monkeypatch, [TimeoutError()])
    with pytest.raises(HTTPException) as error:
        main.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 504
    assert len(llamadas) == 1


def test_falla_siempre_termina_en_502(monkeypatch):
    llamadas = preparar(monkeypatch, [error_http(503), error_http(503)])
    with pytest.raises(HTTPException) as error:
        main.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 502
    assert len(llamadas) == 2
