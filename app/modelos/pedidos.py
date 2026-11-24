"""Contrato de pedidos: precios y dueño son calculados por la API."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_serializer, model_validator

from app.servicios.pedidos import verificar_productos_unicos

Id = Annotated[int, Field(strict=True, gt=0, le=4294967295)]
Cantidad = Annotated[int, Field(strict=True, gt=0, le=4294967295)]
Comentario = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=2, max_length=300)]
Sentimiento = Literal["positivo", "neutral", "negativo"]


class ProductoPedidoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    producto_id: Id
    cantidad: Cantidad


class PedidoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    productos: Annotated[list[ProductoPedidoEntrada], Field(min_length=1)]

    @model_validator(mode="after")
    def productos_unicos(self):
        # La regla vive en el servicio; su ProductoRepetido (ValueError) se vuelve 422 aquí.
        verificar_productos_unicos([p.producto_id for p in self.productos])
        return self


class DetallePedido(BaseModel):
    producto_id: Id
    cantidad: Cantidad
    precio_unitario: Decimal = Field(description="Precio de compra; texto decimal exacto con dos decimales")

    @field_serializer("precio_unitario", when_used="json")
    def serializar_precio(self, valor: Decimal) -> str:
        return format(valor, ".2f")


class Pedido(BaseModel):
    id: Id
    usuario_id: Id = Field(description="Dueño obtenido del token, no del cuerpo")
    estado: Literal["pendiente"]
    total: Decimal = Field(description="Suma exacta de cantidad por precio unitario; texto con dos decimales")
    productos: list[DetallePedido]

    @field_serializer("total", when_used="json")
    def serializar_total(self, valor: Decimal) -> str:
        return format(valor, ".2f")


class EntradaPedidosComentario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comentario: Comentario


class RespuestaComentario(BaseModel):
    sentimiento: Sentimiento
    respuesta: Annotated[str, Field(min_length=1, max_length=200)]
