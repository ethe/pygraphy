import pygraphql


class GeoInput(pygraphql.Input):
    lat: float
    lng: float

    @property
    def latlng(self):
        return "({},{})".format(self.lat, self.lng)


class Address(pygraphql.Object):
    latlng: str


class Query(pygraphql.Object):

    @pygraphql.field
    def address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Mutation(pygraphql.Object):

    @pygraphql.field
    def create_address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Schema(pygraphql.Schema):
    query: Query
    mutation: Mutation
