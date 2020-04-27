import asyncio
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps

from .exceptions import ParseError, NeedMore
from .logger import logger
from .parsers import MutilJsonParser
from .utils import to_bytes, to_str


class BaseProtocol(asyncio.Protocol):
    def __init__(self, app):
        self._app = app
        self.transport: asyncio.BaseTransport = None

    def connection_made(self, transport):
        self.transport = transport
        return super().connection_made(transport)

    def connection_lost(self, exc):
        self.close()
        return super().connection_lost(exc)

    def data_received(self, data):
        return super().data_received(data)

    def close(self):
        if not self.transport.is_closing():
            self.transport.close()

    def on_msg(self, msg):
        pass

class RPCProtocol(BaseProtocol):
    def __init__(self, app, parser_factory=MutilJsonParser):
        super().__init__(app)
        self.parser = parser_factory(self)
        self._task_queue = asyncio.Queue()
        self._cumsumer = asyncio.ensure_future(self.write_back())
        self._in_order = True
        self._tasks = set()

    @property
    def _client_address(self):
        if self.transport is None:
            return 'Unknown Client'
        host, port = self.transport.get_extra_info('peername', 'Unknown Client')
        return "%s:%d" % (host, port)

    def on_msg(self, msg):
        logger.info('[%s] Message recv: %s' % (self._client_address, json.dumps(msg)))
        if '__init__' in msg:
            init = msg.get('__init__')
            self._in_order = init.get('in_order', True)
            return
        if '__quit__' in msg:
            self.close()
            return
        fut = asyncio.ensure_future(self.handler_msg(msg))
        if self._in_order:
            self._task_queue.put_nowait(fut)
        else:
            self._add_task(fut)

    def _future_cb(self, fut):
        self._tasks.remove(fut)
        ret = fut.result()
        self.write(ret)

    def _add_task(self, fut: asyncio.Future):
        fut.add_done_callback(self._future_cb)
        self._tasks.add(fut)

    def write(self, data):
        data = to_bytes(data)
        transport: asyncio.BaseTransport = self.transport
        if transport and not transport.is_closing():
            logger.info('[%s] Message write: %s' % (self._client_address, to_str(data)))
            transport.write(data)

    def data_received(self, data):
        try:
            self.parser.feed(data)
        except ParseError:
            self.close()
        except NeedMore:
            pass

    def _async_wrapper(self, func):
        @wraps(func)
        async def inner(*args, **kw):
            nonlocal func
            func = partial(func, *args, **kw)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func)
        return inner

    async def _call(self, func, *args, **kw):
        if not inspect.iscoroutinefunction(func):
            func = self._async_wrapper(func)
        ret = await func(*args, **kw)
        while inspect.isawaitable(ret):
            ret = await ret
        return ret

    def get_callable(self, name):
        return self._app._handler_map.get(name)

    async def handler_msg(self, msg):
        request_id = msg.get('request_id')
        func_name = msg.get('func_name')
        args = msg.get('args', ())
        kwargs = msg.get('kwargs', {})
        ret = {
            "request_id": request_id,
            "func_name": func_name,
            "ret_code": 200,
            "result": None,
            "msg": ""
        }
        func = self.get_callable(func_name)
        if func is None:
            ret.update(ret_code=404, msg="method [%s] not found" % func_name)
            return ret
        call = self._call(func, *args, **kwargs)
        try:
            result = await call
        except Exception as e:
            ret.update({
                'result': None,
                'ret_code': 500,
                'msg': str(e)
            })
        else:
            ret.update({
                "ret_code": 200,
                "result": result
            })
        return ret

    async def write_back(self):
        while True:
            try:
                fut = await self._task_queue.get()
                ret = await fut
            except asyncio.CancelledError:
                break
            self.write(ret)

    def close(self):
        super().close()
        self.parser = None
        if self._cumsumer:
            self._cumsumer.cancel()
            self._cumsumer = None
