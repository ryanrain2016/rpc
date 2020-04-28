import asyncio
from ..parsers import MutilJsonParser
from .protocol import RPCProtocol

class App:
    def __init__(self, protocol_factory=RPCProtocol, parser_factory=MutilJsonParser):
        self.protocol_factory = protocol_factory
        self.parser_factory = parser_factory
        self._handler_map = {}

    async def async_run(self, host, port, protocol_factory=None, parser_factory=None):
        protocol_factory = protocol_factory or self.protocol_factory
        parser_factory = parser_factory or self.parser_factory
        loop = asyncio.get_event_loop()
        server = await loop.create_server(
            lambda: protocol_factory(self, parser_factory),
            host, port)
        async with server:
            await server.serve_forever()

    def run(self, host, port, protocol_factory=None, parser_factory=None):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.async_run(host, port, protocol_factory, parser_factory))
        finally:
            loop.close()

    def register(self, func_or_name):
        if callable(func_or_name):
            name = func_or_name.__name__
            return self.register(name)(func_or_name)
        else:
            name = func_or_name
            def wrapper(func):
                if name in self._handler_map:
                    raise ValueError('func with the same name [%s] has been already registered' % name)
                self._handler_map[name] = func
                return func
            return wrapper

