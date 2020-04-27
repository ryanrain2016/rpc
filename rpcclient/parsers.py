import json
from .exceptions import ParseError, NeedMore
from .consts import MAX_PAYLOAD_LENGTH

_empty = object()

class BaseParser:
    def __init__(self, protocol):
        self._protocol = protocol

    def feed(self, data):
        raise NotImplementedError

class MutilJsonParser(BaseParser):
    def __init__(self, protocol):
        super().__init__(protocol)
        self._buffer = bytearray()

    def feed(self, data):
        self._buffer.extend(data)
        self.feed_buffer()

    def feed_buffer(self):
        buffer = self._buffer.decode('utf-8')
        while True:  # 每个循环解析一则消息
            try:
                msg = json.loads(buffer)
                self._buffer.clear()
                self._protocol.on_msg(msg)
                break
            except json.JSONDecodeError as e:
                pos = e.pos
                if pos == len(buffer):
                    if pos > MAX_PAYLOAD_LENGTH:
                        raise ParseError('payload is too long.')
                    self._buffer = bytearray(buffer.encode())
                    raise NeedMore
                buffer, remain = buffer[:pos], buffer[pos:]
                self._buffer = bytearray(remain.encode())
                if buffer.strip():
                    msg, buffer = json.loads(buffer), remain
                    self._protocol.on_msg(msg)
                else:
                    raise ParseError("not a json message")

    def __del__(self):
        self._buffer.clear()
        self._buffer = None

