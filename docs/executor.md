Pygraphy can be used as a GraphQL schema declaration and query executor library, same with graphql-core. Call the `execute` method of a custom Schema and get the query response.

```python
import asyncio
import pygraphy
from typing import Optional


class Patron(pygraphy.Object):
    id: str
    name: str
    age: int


class Query(pygraphy.Query):

    @pygraphy.field
    def patron(self) -> Patron:
        return Patron(id='1', name='Gwo', age=25)

    @pygraphy.field
    def exception(self, content: str) -> str:
        raise RuntimeError(content)


class Schema(pygraphy.Schema):
    query: Optional[Query]


query = """
    query something {
      patron {
        id
        name
        age
      }
    }
"""

loop = asyncio.get_event_loop()
result = loop.run_until_complete(Schema.execute(query))
assert result == {
    'errors': None,
    'data': {'patron': {'id': '1', 'name': 'Gwo', 'age': 25}}
}
```

the `Schema.execute` method is defined like below:
```python
async def execute(
    cls,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    request: Optional[Any] = None,
    serialize: bool = False
)
```

Parameters:

- query: GraphQL query string.
- variables: A dict of query variables, pass it if there are some variables in query string.
- request: the request instance, it could be got from query context in resolver fields. It is useful if you want to get the request info in resolvers, such as HTTP headers.
- serialize: If it is true, executor would return a JSON string which as already been dumped. Return a Python dict result as default.

## Asynchronous Executor

Pygraphy fully supports `asyncio`, the Python native parallel model. Just define the resolver field as a coroutine function, Pygraphy would automatically executes it as a coroutine task. All resolver fields in a same Object would be executed parallel.

```python
import asyncio
import pygraphy
from typing import Optional


global_var = False


class Query(pygraphy.Query):

    @pygraphy.field
    async def foo(self) -> bool:
        global global_var
        result = global_var
        await asyncio.sleep(0.1)
        global_var = True
        return result

    @pygraphy.field
    async def bar(self) -> bool:
        global global_var
        result = global_var
        await asyncio.sleep(0.1)
        global_var = True
        return result


class Schema(pygraphy.Schema):
    query: Optional[Query]


query = """
    query test {
        foo
        bar
    }
"""


loop = asyncio.get_event_loop()
result = loop.run_until_complete(Schema.execute(query))
# Obviously, foo and bar both return False, cause they are executed parallel.
assert result == {
    'errors': None,
    'data': {'foo': False, 'bar': False}
}

```

**Attention:** do not mix asynchronous resolvers and non-asynchronous resolvers together. the non-asynchronous resolvers would block the query process, it is a design of Python `asyncio`.
