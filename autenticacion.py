"""Login JSON y dependencia Bearer reutilizable para las siguientes etapas."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import os
from typing import Annotated, Literal

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from usuarios import RepositorioUsuarios, Rol, Usuario

ALGORITMO = "HS256"
DURACION = timedelta(minutes=30)


class Credenciales(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=80)]
    clave: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)] = Field(repr=False)


class Sesion(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class Identidad(BaseModel):
    id: int
    rol: Rol


def secreto_desde_entorno() -> str:
    secreto = os.getenv("JWT_SECRETO", "")
    if len(secreto.encode("utf-8")) < 32 or secreto.startswith("REEMPLAZAR"):
        raise RuntimeError("Configura JWT_SECRETO con al menos 32 bytes aleatorios en el entorno")
    return secreto


def proteger_clave(clave: str) -> str:
    datos = clave.encode("utf-8")
    if not 8 <= len(datos) <= 72:
        raise ValueError("La clave de desarrollo debe tener entre 8 y 72 bytes UTF-8")
    return bcrypt.hashpw(datos, bcrypt.gensalt(rounds=12)).decode("ascii")


@lru_cache(maxsize=1)
def _hash_ficticio() -> str:
    # También comparamos con bcrypt cuando el usuario no existe.
    return proteger_clave("comparacion-ficticia-sin-cuenta")


def comprobar_clave(clave: str, clave_hash: str) -> bool:
    try:
        datos = clave.encode("utf-8")
        if len(datos) > 72:
            return False
        return bcrypt.checkpw(datos, clave_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def no_autorizado(mensaje: str = "El token no es válido o ya expiró") -> HTTPException:
    return HTTPException(401, mensaje, headers={"WWW-Authenticate": "Bearer"})


class Autenticacion:
    def __init__(self, usuarios: RepositorioUsuarios, secreto: str | None = None):
        self.usuarios = usuarios
        self._secreto = secreto

    @property
    def secreto(self) -> str:
        # No exige configuración de seguridad al exportar OpenAPI ni consultar productos.
        return self._secreto if self._secreto is not None else secreto_desde_entorno()

    def iniciar_sesion(self, credenciales: Credenciales) -> Sesion:
        usuario = self.usuarios.buscar(credenciales.usuario)
        valido = comprobar_clave(credenciales.clave, usuario.clave_hash if usuario else _hash_ficticio())
        if not valido or usuario is None:
            raise no_autorizado("Usuario o clave incorrectos")
        return Sesion(access_token=self.crear_token(usuario))

    def crear_token(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": str(usuario.id), "rol": usuario.rol, "iat": ahora, "exp": ahora + DURACION},
            self.secreto,
            algorithm=ALGORITMO,
        )

    def verificar_token(self, token: str) -> Identidad:
        try:
            datos = jwt.decode(
                token, self.secreto, algorithms=[ALGORITMO],
                options={"require": ["sub", "rol", "iat", "exp"]},
            )
            sub = datos["sub"]
            if not isinstance(sub, str) or not sub.isascii() or not sub.isdigit() or int(sub) <= 0:
                raise ValueError("Identidad inválida")
            if datos["rol"] not in ("admin", "cliente"):
                raise ValueError("Rol inválido")
            if type(datos["exp"]) not in (int, float) or type(datos["iat"]) not in (int, float):
                raise ValueError("Fechas inválidas")
            return Identidad(id=int(sub), rol=datos["rol"])
        except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
            raise no_autorizado() from None


bearer = HTTPBearer(auto_error=False, bearerFormat="JWT", scheme_name="BearerJWT")


def usuario_actual(
    request: Request,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Identidad:
    if credenciales is None:
        raise no_autorizado("Falta un token Bearer válido")
    return request.app.state.autenticacion.verificar_token(credenciales.credentials)


def exigir_admin(yo: Annotated[Identidad, Depends(usuario_actual)]) -> Identidad:
    """Primero autentica el token; después autoriza la escritura de productos."""
    if yo.rol != "admin":
        raise HTTPException(403, "Tu rol no puede hacer esto")
    return yo
