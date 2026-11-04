"""Punto de entrada: uvicorn main:app --reload."""

from fastapi import FastAPI, HTTPException, Response, status

from errores import registrar_manejadores
from memoria import generar_id, productos
from modelos import Producto, ProductoEntrada


def buscar_producto(id: int) -> Producto:
    if id not in productos:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return productos[id]


def comprobar_duplicado(entrada: ProductoEntrada, excluir_id: int | None = None) -> None:
    nombre = entrada.nombre.strip().casefold()
    for producto in productos.values():
        if (
            producto.id != excluir_id
            and producto.nombre.strip().casefold() == nombre
            and producto.preparacion == entrada.preparacion
        ):
            raise HTTPException(
                status_code=409,
                detail="Ya existe un producto con ese nombre y preparación",
            )


def producto_con_id(entrada: ProductoEntrada, id: int) -> Producto:
    # FastAPI ya validó la entrada y el id lo proporciona la API.
    # Evitamos revalidar el Decimal interno con el validador de números JSON.
    return Producto.model_construct(id=id, **entrada.model_dump())


def crear_app() -> FastAPI:
    app = FastAPI(title="Katea — API de productos")
    registrar_manejadores(app)

    @app.get("/productos", response_model=list[Producto])
    async def listar_productos() -> list[Producto]:
        # Esta práctica incluye también los no disponibles.
        return list(productos.values())

    @app.get("/productos/{id}", response_model=Producto)
    async def consultar_producto(id: int) -> Producto:
        return buscar_producto(id)

    @app.post("/productos", response_model=Producto, status_code=status.HTTP_201_CREATED)
    async def crear_producto(entrada: ProductoEntrada) -> Producto:
        comprobar_duplicado(entrada)
        producto = producto_con_id(entrada, generar_id())
        productos[producto.id] = producto
        return producto

    @app.put("/productos/{id}", response_model=Producto)
    async def reemplazar_producto(id: int, entrada: ProductoEntrada) -> Producto:
        buscar_producto(id)
        comprobar_duplicado(entrada, excluir_id=id)
        producto = producto_con_id(entrada, id)
        productos[id] = producto
        return producto

    @app.delete("/productos/{id}", status_code=status.HTTP_204_NO_CONTENT)
    async def eliminar_producto(id: int) -> Response:
        buscar_producto(id)
        del productos[id]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = crear_app()
