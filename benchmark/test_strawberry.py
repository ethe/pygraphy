import asyncio
from graphql import graphql
import strawberry


@strawberry.type
class Patron:
    id: int
    name: str
    age: int


@strawberry.type
class Query:
    @strawberry.field
    async def patron(self, info) -> Patron:
        await asyncio.sleep(0)
        return Patron(id=1, name="Patrick", age=100)


schema = strawberry.Schema(query=Query)

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
            graphql(schema, query), loop=loop
        ) for _ in range(1000)
    ]
    gathered = asyncio.gather(*futures, loop=loop, return_exceptions=True)
    loop.run_until_complete(gathered)
