import pygraphql


class Patron(pygraphql.Object):
    id: str
    name: str
    age: int


class Query(pygraphql.Object):

    @pygraphql.field
    def patron(self) -> Patron:
        return Patron(id='1', name='Syrus', age=27)


class Schema(pygraphql.Schema):
    query: Query
