# 介绍
一个rpc框架的实现，灵感来自于`sanic`，实现了python rpc调用方法。

# 使用示例
server_demo.py:
```python
import asyncio
from time import sleep

from rpc.server import App

app = App()

# register可以添加名字，修饰同步函数或者协程函数， 同步的函数会在ThreadPoolExecutor中执行
@app.register('sleep')
def some_func(n):
    sleep(n)
    return 'sleep %s s' % n

# register也可以直接修饰函数，这时名字为函数名
@app.register
async def async_sleep(n):
    await asyncio.sleep(n)
    return 'async sleep %s s' % n

if __name__ == "__main__":
    app.run('0.0.0.0', 9090)
```
client_demo.py
```python
from rpc.client import Client
import time, asyncio

# 同步代码
# in_order参数表示，rpc是否按照请求的顺序从服务器端返回，默认为True
# 注意一个客户端同时异步执行多个函数，那么函数的执行是并发的，返回的顺序与in_order参数有关
with Client('127.0.0.1', 9090, in_order=False, timeout=60) as c:
    r = c.sleep(2)  # 阻塞执行
    r1 = c.sleep(1)  # 阻塞执行
    print(r1) # sleep 1 s
    print(r) # sleep 2 s
    r = c.call_async('sleep', 2)
    r1 = c.call_async('sleep', 1)
    print(r1.result())  # 等待1s之后打印 sleep 1 s
    print(r.result())   # 再次等待1s 之后打印 sleep 2 s

async def main():
    # 异步代码
    async with Client('127.0.0.1', 9090, in_order=False, timeout=60) as c:
        r = await c.async_sleep(1)   # 等待1s
        print(r)
        r1 = await c.call('async_sleep', 2) # 等待2s
        print(r1)
        t = time.time()
        print(await asyncio.gather(c.async_sleep(1), c.async_sleep(2)))
        print(time.time() - t)  # 2s

if __name__ == "__main__":
    asyncio.run(main())
```

# 扩展
1. 自定义parser类可以实现自定义的协议方式
```python
from rpc.parsers import BaseParser

class SomeParser(BaseParser):
    def feed(self, data):
        # 反序列化字节流
        # 每解析一条消息需要调用self.on_msg方法
        # 注意处理tcp粘包
        pass

    def parse(self, msg):
        # 每则消息序列化
        pass

    def on_msg(self, msg):
        # 解析出一条消息后调用的方法， 默认是调用self._protocol.on_msg方法
        pass

app.run(host, port, parser_factory=SomeParser)
```
客户端也需要同样的解析器

# TODO
1. 并发控制
2. 签名校验（可通过自定义解析器实现）