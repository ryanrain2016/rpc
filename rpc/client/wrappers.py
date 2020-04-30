import asyncio
import socket
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial

from ..exceptions import ParseError
from ..utils import to_bytes

class BaseWrapper:
    def __init__(self, client):
        self._client = client
        parser_factory = client.parser_factory
        self._parser = parser_factory(self)
        self._futs = {}
        self._is_closing = False
        self.conn = None

    def on_msg(self, msg):
        request_id = msg.get('request_id')
        if request_id not in self._futs:
            self.close()
            return
        fut = self._futs.pop(request_id)
        if msg.get('ret_code') == 200:
            fut.set_result(msg.get('result'))
        else:
            fut.set_exception(ValueError(msg.get('msg')))

    def send_init(self, **kw):
        raise NotImplementedError

    def send(self, data):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

class Wrapper(BaseWrapper):
    def __init__(self, client):
        super().__init__(client)
        self.conn = None
        self._excutor = ThreadPoolExecutor(max_workers=2)
        self._response_handler = None

    def get_response(self):
        while True:
            data = self.conn.recv(8192)
            if not data:
                break
            try:
                self._parser.feed(data)
            except ParseError:
                break
        self.close()

    def connect(self, **kw):
        self.conn = socket.create_connection((self._client.host, self._client.port))
        ssl = kw.get('ssl')
        server_hostname = kw.get('server_hostname')
        if ssl is not None:
            if server_hostname:
                self.conn = ssl.wrap_socket(self.conn, server_hostname)
            else:
                self.close()
                raise ValueError('server_hostname missing')

        self.send_init(in_order=self._client.in_order, timeout=self._client.timeout)
        self._response_handler = self._excutor.submit(self.get_response)

    def send_init(self, **kw):
        data = {'__init__': kw}
        self.send(data)

    def send(self, data):
        data = self._parser.parse(data)
        if self.conn:
            self.conn.send(data)

    def _wrapper(self, func_name):
        def inner(*args, **kw):
            request_id = str(uuid.uuid1())
            self.send({
                'request_id': request_id,
                'func_name': func_name,
                'args': args,
                'kw': kw
            })
            fut = Future()
            self._futs[request_id] = fut
            return fut
        return inner

    def call_async(self, name, *args, **kw):
        func = self._wrapper(name)
        return func(*args, **kw)

    def call(self, name, *args, **kw):
        fut = self.call_async(name, *args, **kw)
        return fut.result()

    def __getattr__(self, name):
        # def inner(*args, **kw):
        #     func = self._wrapper(name)
        #     fut = func(*args, **kw)
        #     return fut.result()
        # return inner
        return partial(self.call, name)

    def close(self):
        if self._is_closing:
            return
        self._is_closing = True
        for fut in self._futs.values():
            fut.set_exception(ConnectionAbortedError("connection abort."))
        self._futs = {}
        if self.conn is not None:
            self.send({'__quit__': True})
            self.conn.close()
            self.conn = None
        if self._response_handler:
            self._response_handler.cancel()
            self._response_handler = None
        if self._excutor:
            self._excutor.shutdown(wait=False)
            self._excutor = None

class AsyncWrapper(BaseWrapper, asyncio.Protocol):
    def __init__(self, client):
        super().__init__(client)
        self._loop = asyncio.get_event_loop()

    def close(self):
        if self._is_closing:
            return
        self._is_closing = True
        if self.conn and not self.conn.is_closing():
            self.send({'__quit__': True})
            self.conn.close()
            self.conn = None
        for fut in self._futs.values():
            fut.set_exception(ConnectionAbortedError("connection abort."))
        self._futs = {}

    def connection_made(self, transport):
        self.conn = transport

    async def connect(self, **kw):
        await self._loop.create_connection(lambda: self, self.host, self.port, **kw)
        self.send_init(in_order=self._client.in_order, timeout=self._client.timeout)

    def send_init(self, **kw):
        data = {'__init__': kw}
        self.send(data)

    def send(self, data):
        data = self._parser.parse(data)
        if self.conn:
            self.conn.write(data)

    def data_received(self, data):
        try:
            self._parser.feed(data)
        except ParseError:
            asyncio.ensure_future(self.close())

    def _wrapper(self, func_name):
        def inner(*args, **kw):
            request_id = str(uuid.uuid1())
            self.send({
                'request_id': request_id,
                'func_name': func_name,
                'args': args,
                'kw': kw
            })
            fut = self._loop.create_future()
            self._futs[request_id] = fut
            return fut
        return inner

    def __getattr__(self, name):
        # async def inner(*args, **kw):
        #     func = self._wrapper(name)
        #     fut = func(*args, **kw)
        #     return await fut
        # return inner
        return partial(self.call, name)

    async def call(self, name, *args, **kw):
        func = self._wrapper(name)
        fut = func(*args, **kw)
        return await fut
