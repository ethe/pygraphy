import pygraphy
from typing import Optional


class Patron(pygraphy.Object):
    id: str
    name: str
    age: int


class Query(pygraphy.Query):

    @pygraphy.field
    def patron(self) -> Patron:
        return Patron(id='1', name='Syrus', age=27)

    @pygraphy.field
    def exception(self, content: str) -> str:
        raise RuntimeError(content)


class Schema(pygraphy.Schema):
    query: Optional[Query]
