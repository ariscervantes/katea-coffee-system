"""Contrato de entrada y representación de un producto almacenado."""

from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, field_serializer, field_validator


Nombre = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=2, max_length=80)]
Descripcion = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=5, max_length=200)]


class ProductoEntrada(BaseModel):
    # Todos los campos son obligatorios: ninguno tiene valor por defecto.
    model_config = ConfigDict(extra="forbid")

    nombre: Nombre
    descripcion: Descripcion
    precio: Decimal
    imagen_url: Annotated[str, StringConstraints(strict=True, min_length=1)]
    disponible: StrictBool
    preparacion: Literal["frio", "caliente", "no_aplica"]

    @field_validator("precio", mode="before")
    @classmethod
    def validar_precio(cls, valor: object) -> Decimal:
        # bool hereda de int en Python: comprobar el tipo exacto evita aceptar true.
        if type(valor) not in (int, float):
            raise ValueError("precio debe ser un número, sin comillas")
        try:
            numero = Decimal(str(valor))
        except InvalidOperation:
            raise ValueError("precio debe ser un número válido") from None
        if not numero.is_finite() or numero <= 0:
            raise ValueError("precio debe ser finito y mayor que cero")
        # Descontar ceros finales sin redondear: 25.000 equivale a 25.
        _, digitos, exponente = numero.as_tuple()
        for digito in reversed(digitos):
            if digito != 0:
                break
            exponente += 1
        if exponente < -2:
            raise ValueError("precio debe tener máximo dos decimales")
        return numero

    @field_serializer("precio", when_used="json")
    def serializar_precio(self, valor: Decimal) -> float:
        # Decimal es interno; en JSON el contrato exige un número, no texto.
        return float(valor)

    @field_validator("imagen_url")
    @classmethod
    def validar_imagen(cls, valor: str) -> str:
        if not valor.endswith((".jpg", ".jpeg", ".png", ".webp")):
            raise ValueError("imagen_url debe terminar en .jpg, .jpeg, .png o .webp")
        return valor


class Producto(ProductoEntrada):
    id: Annotated[int, Field(strict=True, gt=0)]
