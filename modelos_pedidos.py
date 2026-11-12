"""Contrato de pedidos: precios y dueño son calculados por la API."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

Id = Annotated[int, Field(strict=True, gt=0, le=4294967295)]
Cantidad = Annotated[int, Field(strict=True, gt=0, le=4294967295)]


class ProductoPedidoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    producto_id: Id
    cantidad: Cantidad


class PedidoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    productos: Annotated[list[ProductoPedidoEntrada], Field(min_length=1)]

    @model_validator(mode="after")
    def productos_unicos(self):
        ids = [p.producto_id for p in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez; usa cantidad")
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
