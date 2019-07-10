import pygraphy
from typing import Optional, List


class Foo(pygraphy.Object):
    a: str


class Bar(pygraphy.Object):
    b: int


class FooBar(pygraphy.Union):
    members = (Foo, Bar)


class GeoInput(pygraphy.Input):
    lat: float
    lng: float

    @property
    def latlng(self):
        return "({},{})".format(self.lat, self.lng)


class Address(pygraphy.Object):
    latlng: str

    @pygraphy.field
    def foobar(self) -> List[FooBar]:
        return [Foo(a='test') for _ in range(5)]


class Query(pygraphy.Query):

    @pygraphy.field
    def address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Mutation(pygraphy.Object):

    @pygraphy.field
    def create_address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Schema(pygraphy.Schema):
    query: Optional[Query]
    mutation: Optional[Mutation]
