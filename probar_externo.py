#!/usr/bin/env python3
"""Prueba automática de un endpoint externo configurado en prueba.json.

Uso:
    python probar_externo.py [prueba.json]

La sección "externo" del JSON indica método, ruta, cuerpo y qué token usar:
    "token": "admin" | "usuario" | "otro" | false

El script hace login con la sección "auth" cuando se requiere token. Nunca
imprime claves ni tokens. Solo usa la biblioteca estándar de Python.
"""

import json
import sys
import urllib.error
import urllib.request


CONFIG = sys.argv[1] if len(sys.argv) > 1 else "prueba.json"


def cargar_configuracion() -> dict:
    try:
        with open(CONFIG, encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        sys.exit(f"No encuentro {CONFIG}.")
    except json.JSONDecodeError as error:
        sys.exit(f"{CONFIG} no es JSON válido (línea {error.lineno}): revisa comas y comillas.")


def como_json(texto: str):
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, ValueError):
        return None


def pedir(base: str, metodo: str, ruta: str, cuerpo=None, token: str | None = None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    encabezados = {"Accept": "application/json"}
    if token:
        encabezados["Authorization"] = f"Bearer {token}"
    if datos is not None:
        encabezados["Content-Type"] = "application/json"
    solicitud = urllib.request.Request(base + ruta, data=datos, method=metodo, headers=encabezados)
    try:
        with urllib.request.urlopen(solicitud, timeout=15) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        sys.exit(f"No pude conectarme a {base}: {error.reason}. ¿La API está corriendo?")
    except TimeoutError:
        sys.exit("La petición tardó más de 15 segundos. Revisa la API o la IA.")


def token_de(texto: str):
    objeto = como_json(texto)
    if isinstance(objeto, dict):
        for clave in ("access_token", "token", "jwt"):
            if isinstance(objeto.get(clave), str) and objeto[clave].count(".") == 2:
                return objeto[clave]
    return None


def iniciar_sesion(base: str, auth: dict, nombre: str) -> str:
    credenciales = auth.get(nombre)
    if not isinstance(credenciales, dict):
        sys.exit(f'Falta "auth.{nombre}" en {CONFIG} para probar un endpoint con token.')
    login = "/" + str(auth.get("login", "/login")).strip("/")
    codigo, texto = pedir(base, "POST", login, credenciales)
    token = token_de(texto)
    if codigo != 200 or not token:
        sys.exit(f'No pude iniciar sesión como "{nombre}" (-> {codigo}). Revisa "auth" en {CONFIG}.')
    return token


def main() -> int:
    config = cargar_configuracion()
    externo = config.get("externo")
    if not isinstance(externo, dict):
        sys.exit(f'Falta la sección "externo" en {CONFIG}.')

    base = str(config.get("base", "http://127.0.0.1:8000")).rstrip("/")
    metodo = str(externo.get("metodo", "POST")).upper()
    ruta = "/" + str(externo.get("ruta", "")).strip("/")
    if ruta == "/":
        sys.exit('"externo.ruta" es obligatoria.')
    cuerpo = externo.get("cuerpo")
    esperado_codigo = int(externo.get("esperado_codigo", 200))

    seleccion_token = externo.get("token", "usuario")
    sin_token = seleccion_token is False or seleccion_token is None or str(seleccion_token).lower() in {
        "", "false", "ninguno", "none", "sin",
    }
    token = None
    if not sin_token:
        auth = config.get("auth")
        if not isinstance(auth, dict):
            sys.exit(f'Falta la sección "auth" en {CONFIG} para obtener el token.')
        token = iniciar_sesion(base, auth, str(seleccion_token))

    print(f"Probando {metodo} {base}{ruta} sin token\n" if sin_token else f"Probando {metodo} {base}{ruta} como {seleccion_token}\n")
    codigo, texto = pedir(base, metodo, ruta, cuerpo, token)
    respuesta = como_json(texto)

    problemas = []
    if codigo != esperado_codigo:
        problemas.append(f"esperaba {esperado_codigo} y llegó {codigo}")
    if esperado_codigo == 200:
        if not isinstance(respuesta, dict):
            problemas.append("la respuesta no es un objeto JSON")
        else:
            sentimiento = respuesta.get("sentimiento")
            contestacion = respuesta.get("respuesta")
            if sentimiento not in ("positivo", "neutral", "negativo"):
                problemas.append(f"sentimiento inválido: {sentimiento!r}")
            if not isinstance(contestacion, str) or not contestacion.strip():
                problemas.append("respuesta vacía o de tipo incorrecto")
            esperado = externo.get("esperado")
            if isinstance(esperado, dict):
                for campo, valor in esperado.items():
                    if respuesta.get(campo) != valor:
                        problemas.append(f"{campo}: esperaba {valor!r} y llegó {respuesta.get(campo)!r}")

    if problemas:
        print(f"[X ] Falló: {'; '.join(problemas)}")
        print(f"Respuesta ({codigo}): {texto[:500]}")
        return 1

    print(f"[OK] {metodo} {ruta} -> {codigo}")
    if isinstance(respuesta, dict):
        print(f"     sentimiento={respuesta.get('sentimiento')!r} respuesta={str(respuesta.get('respuesta', ''))[:200]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
