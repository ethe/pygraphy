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
        '{"human": {"name": "foo"}}'


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
            foobar {
              ... on Bar {
                b
              }
            }
          }
        }
    """

    assert ComplexSchema.execute(mutation) == r'{"createAddress": {"latlng": "(32.2,12)", "foobar": {}}}'

    mutation = """
        mutation addAddress{
          createAddress(geo: {lat:32.2, lng:12}) {
            latlng
            foobar {
              ... on Foo {
                a
              }
            }
          }
        }
    """

    assert ComplexSchema.execute(mutation) == r'{"createAddress": {"latlng": "(32.2,12)", "foobar": {"a": "test"}}}'


def test_raise_error():
    query = """
        query test {
            exception(content: "test")
        }
    """

    assert SimpleSchema.execute(query) == '{"errors": [{"message": "test", "locations": [{"line": 3, "column": 13}], "path": ["exception"]}], "data": null}'
