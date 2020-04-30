import asyncio
from .wrappers import AsyncWrapper, Wrapper
from ..parsers import MutilJsonParser
from ..consts import TIMEOUT

class BaseClient:
    def __init__(self, host, port, parser_factory=MutilJsonParser,
            in_order=True, timeout=TIMEOUT, **kw):
        self.host = host
        self.port = port
        self.parser_factory=parser_factory
        self._in_order = in_order
        self._timeout = timeout
        self._kw = kw
        self._wrapper = None
        self._async_wrapper = None

    def __enter__(self):
        self._wrapper =  Wrapper(self)
        self._wrapper.connect(**self._kw)
        return self._wrapper

    def __exit__(self, *ex):
        self._wrapper.close()
        self._wrapper = None

    async def __aenter__(self):
        self._async_wrapper = AsyncWrapper(self)
        await self._async_wrapper.connect(**self._kw)
        return self._async_wrapper

    async def __aexit__(self, *ex):
        self._async_wrapper.close()
        self._async_wrapper = None