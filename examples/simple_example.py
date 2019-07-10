import pygraphql
from typing import Optional


class Patron(pygraphql.Object):
    id: str
    name: str
    age: int


class Query(pygraphql.Query):

    @pygraphql.field
    def patron(self) -> Patron:
        return Patron(id='1', name='Syrus', age=27)

    @pygraphql.field
    def exception(self, content: str) -> str:
        raise RuntimeError(content)


class Schema(pygraphql.Schema):
    query: Optional[Query]
