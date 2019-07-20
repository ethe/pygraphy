Inspired by [Strawberry](https://github.com/strawberry-graphql/strawberry), Pygraphy uses dataclass to define the schema. All type classes can be printed as a valid GraphQL SDL. Pygraphy would try to translate all fields name from snake case to camel case.

```python
import pygraphy


class Patron(pygraphy.Object):
    id: str
    name: str
    age: int


class Query(pygraphy.Query):
    """
    Query doc also can be printed
    """

    @pygraphy.field
    async def patron(self) -> Patron:
        """
        Return the patron
        """
        return Patron(id='1', name='Gwo', age=25)

    @pygraphy.field
    async def exception(self, content: str) -> str:
        raise RuntimeError(content)

```

## Object

Declare Object schema by inheriting `pygraphy.Object`, Pygraphy checks the type signature by using [Python type annotation](https://docs.python.org/3/library/typing.html) and generate the SDL. Pygraphy supports adding the description to an Object class and its resolver fields.
```python
from pygraphy import Object, field
from typing import Optional


class Node(Object):
    """
    A node with at most one sub node.
    """
    value: int
    description: str

    @field
    def sub_node(self, description: str = 'A node') -> Optional['Node']:
        """
        The resolver of getting sub node.
        """
        if self.value != 0:
            return Node(value-1, description=description)
        return None


assert str(Node) == '''"""
A node with at most one sub node.
"""
type Node {
  value: Int!
  description: String!
  "The resolver of getting sub node."
  subNode(
    description: String! = "A node"
  ): Node
}'''
```

A class method marked with `pygraphy.field` decorator would be treated as a resolver field.

## Query

Query type is a subclass of Object, and it implements two built-in resolver fields: `__schema` and `__type` to support GraphQL Introspection.
```python
from pygraphy import Query as BaseQuery, field


class Query(BaseQuery):
    """
    Query object
    """

    @field
    async def foo(self) -> int:
        """
        Return an int
        """
        return 1
```

Please note that Query class must not contain any non-resolver field.

## Schema

A Schema class contains two non-resolver field: query and mutation.
```python
from pygraphy import Schema as BaseSchema


class Schema(pygraphy.Schema):
    query: Optional[Query]
    mutation: Optional[Mutation]
```

Both query and mutation field must be optional, because of following the GraphQL Spec, every root node of query should be allowed to return `null` when an error raising during the request.

Types which are referenced with a Schema definition whether directly or indirectly would be all registered into Schema class, the SDL of those types will be generated with Schema class together.
```python
import pygraphy
from typing import List, Optional


class Episode(pygraphy.Enum):
    NEWHOPE = 4
    EMPIRE = 5
    JEDI = 6


class Character(pygraphy.Interface):
    """
    Character interface contains human and droid
    """
    id: str
    name: str
    appears_in: List[Episode]

    @pygraphy.field
    def friends(self) -> Optional[List['Character']]:
        return None


class Human(pygraphy.Object, Character):
    """
    Human object
    """
    home_planet: str


class Droid(pygraphy.Object, Character):
    """
    Driod object
    """
    primary_function: str


class Query(pygraphy.Query):

    @pygraphy.field
    def hero(self, episode: Episode) -> Optional[Character]:
        return None

    @pygraphy.field
    def human(self, id: str = '1234') -> Optional[Human]:
        return Human(
            id=id, name='foo', appears_in=[Episode.NEWHOPE, Episode.EMPIRE], home_planet='Mars'
        )

    @pygraphy.field
    def droid(self, id: str) -> Optional[Droid]:
        return None


class Schema(pygraphy.Schema):
    query: Optional[Query]


print(Schema)
'''
Query()
"""
type Query {
  __schema: __Schema!
  __type(
    name: String!
  ): __Type
  droid(
    id: String!
  ): Droid
  hero(
    episode: Episode!
  ): Character
  human(
    id: String! = "1234"
  ): Human
}

(...other built-in types)

"""
Driod object
"""
type Droid implements Character {
  id: String!
  name: String!
  appearsIn: [Episode!]!
  primaryFunction: String!
  friends: [Character!]
}

"""
An enumeration.
"""
enum Episode {
  NEWHOPE
  EMPIRE
  JEDI
}

"""
Character interface contains human and droid
"""
interface Character {
  id: String!
  name: String!
  appearsIn: [Episode!]!
  friends: [Character!]
}

"""
Human object
"""
type Human implements Character {
  id: String!
  name: String!
  appearsIn: [Episode!]!
  homePlanet: String!
  friends: [Character!]
}

"""
Schema(query: Union[__main__.Query, NoneType])
"""
schema {
  query: Query
}
'''
```

### Subscribable Schema

Schema class does not support the subscription method of GraphQL, the Subscribable Schema and subscription will be introduced later.


## Enum

Enum type is supported like a Python enum class.
```python
from pygraphy import Enum


class Episode(pygraphy.Enum):
    NEWHOPE = 4
    EMPIRE = 5
    JEDI = 6


print(Episode)
'''
"""
An enumeration.
"""
enum Episode {
  NEWHOPE
  EMPIRE
  JEDI
}
'''
```

## Input

The argument of resolver fields can be Input type.
```python
class GeoInput(pygraphy.Input):
    lat: float
    lng: float

    @property
    def latlng(self):
        return "({},{})".format(self.lat, self.lng)


class Address(pygraphy.Object):
    latlng: str


class Query(pygraphy.Query):

    @pygraphy.field
    def address(self, geo: GeoInput) -> Address:
        return Address(latlng=geo.latlng)


class Schema(pygraphy.Schema):
    query: Optional[Query]

```

Input type can not be the return type of a resolver.

## Interface

An Interface type can be inherited to an Object type like a mixin class, all fields inside an Interface will be injected into each Object subclass.
```python
from typing import Optional, List
from pygraphy import Interface, Object, field


class Character(Interface):
    """
    Character interface contains human and droid
    """
    id: str
    name: str

    @field
    def friends(self) -> Optional[List['Character']]:
        return None


class Human(Object, Character):
    """
    Human object
    """
    home_planet: str


class Droid(Object, Character):
    """
    Droid object
    """
    primary_function: str


print(Human)
'''
"""
Human object
"""
type Human implements Character {
  id: String!
  name: String!
  homePlanet: String!
  friends: [Character!]
}
'''
```

## Union

Union type also be supported in Pygraphy.
```python
import pygraphy
from typing import Optional, List


class Foo(pygraphy.Object):
    a: str


class Bar(pygraphy.Object):
    b: int


class FooBar(pygraphy.Union):
    members = (Foo, Bar)


class Query(pygraphy.Object):

    @pygraphy.field
    def get_foobar(self) -> List[FooBar]:
        return [Foo(a='test') for _ in range(5)]


print(FooBar)
'''
union FooBar =
 | Foo
 | Bar
'''
```
