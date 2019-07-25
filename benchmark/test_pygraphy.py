import asyncio
import pygraphy
from typing import Optional


class Patron(pygraphy.Object):
    id: str
    name: str
    age: int


class Query(pygraphy.Query):

    @pygraphy.field
    async def patron(self) -> Patron:
        await asyncio.sleep(0)
        return Patron(id='1', name='Syrus', age=27)


class Schema(pygraphy.Schema):
    query: Optional[Query]


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    query = """
        query something{
          patron {
            id
            name
            age
          }
        }
    """

    futures = [
        asyncio.ensure_future(
            Schema.execute(query), loop=loop
        ) for _ in range(10000)
    ]
    gathered = asyncio.gather(*futures, loop=loop, return_exceptions=True)
    loop.run_until_complete(gathered)
