import pytest
import asyncio
import pygraphql
from typing import Optional


pytestmark = pytest.mark.asyncio
global_var = False


class Query(pygraphql.Query):

    @pygraphql.field
    async def foo(self) -> bool:
        global global_var
        result = global_var
        await asyncio.sleep(0.1)
        global_var = True
        return result

    @pygraphql.field
    async def bar(self) -> bool:
        global global_var
        result = global_var
        await asyncio.sleep(0.1)
        global_var = True
        return result


class Schema(pygraphql.Schema):
    query: Optional[Query]


async def test_asyncio():
    query = """
        query test {
            foo
            bar
        }
    """

    # Obviously, foo and bar both return False
    assert await Schema.execute(query) == r'{"errors": null, "data": {"foo": false, "bar": false}}'
