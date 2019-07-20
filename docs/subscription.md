The Schema type does not support subscription method, because subscription needs a stateful connection between client and server, subscribable schema needs a different way of query executing. You can use `SubscribableSchema` if you have to implement a subscription API.
```python
import asyncio
import pygraphy
from starlette.applications import Starlette
import uvicorn


app = Starlette(debug=True)


class Beat(pygraphy.Object):
    beat: int

    @pygraphy.field
    def foo(self, arg: int) -> int:
        return arg * self.beat


class Subscription(pygraphy.Object):

    @pygraphy.field
    async def beat(self) -> Beat:
        start = 0
        for _ in range(10):
            await asyncio.sleep(0.1)
            yield Beat(beat=start)
            start += 1


@app.websocket_route('/ws')
class SubSchema(pygraphy.SubscribableSchema):
    subscription: Optional[Subscription]


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

```

Root fields of Subscription should be a resolver field, and it must be an [asynchronous generator](https://www.python.org/dev/peps/pep-0525/).
```python
@pygraphy.field
async def beat(self) -> Beat:
    start = 0
    for _ in range(10):
        await asyncio.sleep(0.1)
        yield Beat(beat=start)
        start += 1
```

Each returned of generator would be sent to client as a subscription result.

## Behaviors of Subscription

The `SubscribableSchema` is a subclass of Starlette `WebsocketEndpoint` if you use default Starlette integration, and it uses Websocket to maintain the state between client and server. `SubscribableSchema` also supports query and mutation method. Once Websocket connection established, it can be used to multiple query and mutation request. However, one Websocket connection can be only used to single subscription request, if a connection is handling a subscription, it does not response other request any more.

The connection will be closed if a subscription is canceled by server. If a client does not want to subscribe the existing subscription, closing the connection is fine.
