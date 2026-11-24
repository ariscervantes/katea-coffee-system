"""Llamada a Gemini: reintentos ante 5xx/429, 502/503/504 y EXTERNO_TIMEOUT."""

from io import BytesIO
import json
import urllib.error

import pytest
from fastapi import HTTPException

from app.integraciones import gemini


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

    monkeypatch.setattr(gemini, "IA_URL", "http://externo.test")
    monkeypatch.setattr(gemini, "IA_CLAVE", "")
    monkeypatch.setattr(gemini.urllib.request, "urlopen", urlopen)
    return llamadas


def test_reintenta_una_vez_tras_503(monkeypatch):
    llamadas = preparar(monkeypatch, [
        error_http(503),
        respuesta_gemini({"sentimiento": "neutral", "respuesta": "Gracias"}),
    ])
    assert gemini.preguntar_a_la_ia("instrucción") == {"sentimiento": "neutral", "respuesta": "Gracias"}
    assert len(llamadas) == 2


def test_no_reintenta_un_400(monkeypatch):
    llamadas = preparar(monkeypatch, [error_http(400)])
    with pytest.raises(HTTPException) as error:
        gemini.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 502
    assert len(llamadas) == 1


def test_no_reintenta_un_timeout(monkeypatch):
    llamadas = preparar(monkeypatch, [TimeoutError()])
    with pytest.raises(HTTPException) as error:
        gemini.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 504
    assert len(llamadas) == 1


def test_falla_siempre_termina_en_502(monkeypatch):
    llamadas = preparar(monkeypatch, [error_http(503), error_http(503)])
    with pytest.raises(HTTPException) as error:
        gemini.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 502
    assert len(llamadas) == 2


def test_sin_clave_responde_503_sin_llamar_a_gemini(monkeypatch):
    llamadas = preparar(monkeypatch, [])
    monkeypatch.setattr(gemini, "IA_URL", gemini.URL_GEMINI)
    with pytest.raises(HTTPException) as error:
        gemini.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 503
    assert llamadas == []


@pytest.mark.parametrize("cuerpo", [b"no es json", json.dumps({"candidates": []}).encode()])
def test_respuesta_invalida_responde_502(monkeypatch, cuerpo):
    llamadas = preparar(monkeypatch, [cuerpo])
    with pytest.raises(HTTPException) as error:
        gemini.preguntar_a_la_ia("instrucción")
    assert error.value.status_code == 502
    assert len(llamadas) == 1


def test_cada_intento_usa_el_timeout_configurado(monkeypatch):
    llamadas = preparar(monkeypatch, [
        error_http(500),
        respuesta_gemini({"sentimiento": "positivo", "respuesta": "Gracias"}),
    ])
    monkeypatch.setattr(gemini, "IA_TIMEOUT", 2.5)
    gemini.preguntar_a_la_ia("instrucción")
    assert [timeout for _, timeout in llamadas] == [2.5, 2.5]


def test_externo_timeout_vale_5_por_omision_o_si_es_invalido(monkeypatch):
    monkeypatch.delenv("EXTERNO_TIMEOUT", raising=False)
    assert gemini._timeout_desde_entorno() == 5
    monkeypatch.setenv("EXTERNO_TIMEOUT", "1.5")
    assert gemini._timeout_desde_entorno() == 1.5
    for invalido in ("abc", "", "0", "-3"):
        monkeypatch.setenv("EXTERNO_TIMEOUT", invalido)
        assert gemini._timeout_desde_entorno() == 5
