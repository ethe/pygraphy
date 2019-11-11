import pygraphy
from typing import Optional, List


class Patron(pygraphy.Object):
    id: str
    name: str
    age: int


class Query(pygraphy.Query):

    @pygraphy.field
    def patron(self) -> Patron:
        return Patron(id='1', name='Syrus', age=27)

    @pygraphy.field
    def patrons(self, ids: List[int]) -> List[Patron]:
        return [Patron(id=str(i), name='Syrus', age=27) for i in ids]

    @pygraphy.field
    def exception(self, content: str) -> str:
        raise RuntimeError(content)


class Schema(pygraphy.Schema):
    query: Optional[Query]
