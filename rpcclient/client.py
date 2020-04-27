import asyncio
from .wrappers import AsyncWrapper, Wrapper

class BaseClient:
    def __init__(self, host, port, **kw):
        self.host = host
        self.port = port
        self.kw = kw
        self._wrapper = None
        self._async_wrapper = None

    def __enter__(self):
        self._wrapper =  Wrapper(self)
        self._wrapper.connect()
        return self._wrapper

    def __exit__(self, *ex):
        self._wrapper.close()
        self._wrapper = None

    async def __aenter__(self):
        self._async_wrapper = AsyncWrapper(self)
        await self._async_wrapper.connect()
        return self._async_wrapper

    async def __aexit__(self, *ex):
        self._async_wrapper.close()
        self._async_wrapper = None