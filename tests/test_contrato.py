"""Contrato publicado y ciclo de vida con repositorio inyectado."""

import asyncio

import httpx

from main import crear_app
from unittest.mock import Mock
from usuarios import RepositorioUsuarios
from repositorio_pedidos import RepositorioPedidos


def test_documentacion_y_ciclo_de_vida(repositorio_falso):
    inicios = []
    repositorio_falso.inicializar = lambda: inicios.append(True)
    cuentas = Mock(spec=RepositorioUsuarios)
    pedidos = Mock(spec=RepositorioPedidos)
    app = crear_app(repositorio_falso, cuentas, pedidos=pedidos)
    async def consultar():
        async with app.router.lifespan_context(app):
            assert inicios == [True]
            cuentas.inicializar.assert_called_once_with()
            pedidos.inicializar.assert_called_once_with()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as cliente:
                assert (await cliente.get('/docs')).status_code == 200
                return (await cliente.get('/openapi.json')).json()
    esquema = asyncio.run(consultar())
    entrada = esquema['components']['schemas']['ProductoEntrada']
    assert 'string' not in str(entrada['properties']['precio'])
    for ruta, metodo, codigos in [
        ('/productos', 'post', ['201', '400', '401', '403', '409', '422', '500']),
        ('/productos/{id}', 'put', ['200', '400', '401', '403', '404', '409', '422', '500']),
        ('/productos/{id}', 'delete', ['204', '401', '403', '404', '422', '500']),
    ]:
        respuestas = esquema['paths'][ruta][metodo]['responses']
        assert set(codigos) <= respuestas.keys()
        for codigo in codigos:
            if int(codigo) >= 400:
                assert respuestas[codigo]['content']['application/json']['schema']['$ref'].endswith('/RespuestaError')
