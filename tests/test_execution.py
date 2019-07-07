from examples.starwars.schema import Schema as StarwarsSchema
from examples.simple_example import Schema as SimpleSchema
from examples.complex_example import Schema as ComplexSchema


def test_starwars_query():
    query = """
        query FetchLukeQuery {
          human(id: "1000") {
            name
          }
        }
    """
    assert StarwarsSchema.execute(query) == \
        '{"human": {"id": "1000", "name": "foo", "appearsIn": ["NEWHOPE", "EMPIRE"], "homePlanet": "Mars"}}'


def test_simple_query():
    query = """
        query something{
          patron {
            id
            name
            age
          }
        }
    """

    assert SimpleSchema.execute(query) == r'{"patron": {"id": "1", "name": "Syrus", "age": 27}}'


def test_complex_query():
    query = """
        query something{
          address(geo: {lat:32.2, lng:12}) {
            latlng
          }
        }
    """

    assert ComplexSchema.execute(query) == r'{"address": {"latlng": "(32.2,12)"}}'


def test_complex_mutation():
    mutation = """
        mutation addAddress{
          createAddress(geo: {lat:32.2, lng:12}) {
            latlng
          }
        }
    """

    assert ComplexSchema.execute(mutation) == r'{"createAddress": {"latlng": "(32.2,12)"}}'
