import pygraphql
from typing import Optional


class Foo(pygraphql.Object):
    a: str


class Bar(pygraphql.Object):
    b: int


class FooBar(pygraphql.Union):
    members = (Foo, Bar)


class GeoInput(pygraphql.Input):
    lat: float
    lng: float

    @property
    def latlng(self):
        return "({},{})".format(self.lat, self.lng)


class Address(pygraphql.Object):
    latlng: str

    @pygraphql.field
    def foobar(self) -> FooBar:
        return Foo(a='test')


class Query(pygraphql.Object):

    @pygraphql.field
    def address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Mutation(pygraphql.Object):

    @pygraphql.field
    def create_address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Schema(pygraphql.Schema):
    query: Optional[Query]
    mutation: Optional[Mutation]
