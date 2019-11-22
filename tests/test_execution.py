import pytest
from typing import Optional
from pygraphy.types import (
    Object,
    Input,
    Schema,
    field
)
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
        query something {
          patron {
            id
            name
            age
          }
        }
    """

    assert await SimpleSchema.execute(query, serialize=True) == \
        r'{"errors": null, "data": {"patron": {"id": "1", "name": "Syrus", "age": 27}}}'


    query = """
        query {
          patrons(ids: [1, 2, 3]) {
            id
            name
            age
          }
        }
    """

    assert await SimpleSchema.execute(query, serialize=True) == \
        r'{"errors": null, "data": {"patrons": [{"id": "1", "name": "Syrus", "age": 27}, {"id": "2", "name": "Syrus", "age": 27}, {"id": "3", "name": "Syrus", "age": 27}]}}'


async def test_alias_field():
    query = """
        query something {
          user: patron {
            id
            firstName: name
            age
          }
        }
    """

    assert await SimpleSchema.execute(query) == {
        'data': {
            'user': {
                'age': 27, 'firstName': 'Syrus', 'id': '1'
            }
        }, 'errors': None
    }


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

    assert await ComplexSchema.execute(query, serialize=True, variables={"geo": {"lat":32.2, "lng":12}}) == \
        r'{"errors": null, "data": {"address": {"latlng": "(32.2,12)"}}}'

    query = """
        query something($patron: [int]) {
          patrons(ids: $patron) {
            id
            name
            age
          }
        }
    """
    assert await SimpleSchema.execute(query, serialize=True, variables={"patron": [1, 2, 3]}) == \
        r'{"errors": null, "data": {"patrons": [{"id": "1", "name": "Syrus", "age": 27}, {"id": "2", "name": "Syrus", "age": 27}, {"id": "3", "name": "Syrus", "age": 27}]}}'


async def test_field_name_case():
    class FooInput(Input):
        snake_case: str
        camelCase: str

    class Foo(Object):
        snake_case: str
        camelCase: str

    class Query(Object):
        @field
        def get_foo(self, foo: FooInput) -> Foo:
            return Foo(snake_case=foo.snake_case,
                       camelCase=foo.camelCase)

    class PySchema(Schema):
        query: Optional[Query]

    query = """
        query something($foo: FooInput) {
          get_foo (foo: {
            snakeCase: "sth"
            camelCase: "sth"
          }) {
            snakeCase
            camelCase
          }
        }
    """
    assert await PySchema.execute(query, serialize=True) == \
        r'{"errors": null, "data": {"get_foo": {"snakeCase": "sth", "camelCase": "sth"}}}'


async def test_field_name_case_with_vars():

    class FooInput(Input):
        snake_case: str
        camelCase: str

    class Foo(Object):
        snake_case: str
        camelCase: str

    class Query(Object):
        @field
        def get_foo(self, foo: FooInput) -> Foo:
            return Foo(snake_case=foo.snake_case,
                       camelCase=foo.camelCase)

    class PySchema(Schema):
        query: Optional[Query]

    query = """
        query something($foo: FooInput) {
          get_foo (foo: $foo) {
            snake_case
            camelCase
          }
        }
    """
    assert await PySchema.execute(query, serialize=True, variables={"foo": {"snakeCase":"sth", "camelCase":"sth"}}) == \
        r'{"errors": null, "data": {"get_foo": {"snake_case": "sth", "camelCase": "sth"}}}'
