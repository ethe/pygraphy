import pytest
from examples.starwars.schema import Schema as StarwarsSchema
from examples.simple_example import Schema as SimpleSchema
from examples.complex_example import Schema as ComplexSchema


pytestmark = pytest.mark.asyncio


async def test_starwars_query():
    query = """
        query FetchLukeQuery {
          human(id: "1000") {
            name
          }
        }
    """
    assert await StarwarsSchema.execute(query, serialize=True) == \
        r'{"errors": null, "data": {"human": {"name": "foo"}}}'


async def test_simple_query():
    query = """
        query something{
          patron {
            id
            name
            age
          }
        }
    """

    assert await SimpleSchema.execute(query, serialize=True) == \
        r'{"errors": null, "data": {"patron": {"id": "1", "name": "Syrus", "age": 27}}}'


async def test_complex_query():
    query = """
        query something{
          address(geo: {lat:32.2, lng:12}) {
            latlng
          }
        }
    """

    assert await ComplexSchema.execute(query, serialize=True) == \
        r'{"errors": null, "data": {"address": {"latlng": "(32.2,12)"}}}'


async def test_complex_mutation():
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

    assert await ComplexSchema.execute(mutation, serialize=True) == \
        r'{"errors": null, "data": {"createAddress": {"latlng": "(32.2,12)", "foobar": [{}, {}, {}, {}, {}]}}}'

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

    assert await ComplexSchema.execute(mutation, serialize=True) == \
        r'{"errors": null, "data": {"createAddress": {"latlng": "(32.2,12)", "foobar": [{"a": "test"}, {"a": "test"}, {"a": "test"}, {"a": "test"}, {"a": "test"}]}}}'


async def test_raise_error():
    query = """
        query test {
            exception(content: "test")
        }
    """

    assert await SimpleSchema.execute(query, serialize=True) == \
        '{"errors": [{"message": "test", "locations": [{"line": 3, "column": 13}], "path": ["exception"]}], "data": null}'


async def test_variables():
    query = """
        query something($geo: GeoInput) {
          address(geo: $geo) {
            latlng
          }
        }
    """

    assert await ComplexSchema.execute(query, serialize=True, variables={"geo": r"{lat:32.2, lng:12}"}) == \
        r'{"errors": null, "data": {"address": {"latlng": "(32.2,12)"}}}'
