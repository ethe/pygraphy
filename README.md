# Pygraphy
A modern pythonic GraphQL implementation, painless GraphQL developing experience for Pythonista.

[![Build Status](https://travis-ci.org/ethe/pygraphy.svg?branch=master)](https://travis-ci.org/ethe/pygraphy)
[![codecov](https://codecov.io/gh/ethe/pygraphy/branch/master/graph/badge.svg)](https://codecov.io/gh/ethe/pygraphy)


## Quick Review
All the behaviors of Pygraphy are no difference from your intuition.
```python
import asyncio
import pygraphy
from typing import List, Optional
from starlette.applications import Starlette
import uvicorn


app = Starlette(debug=True)


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
        return []


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
    async def hero(self, episode: Episode) -> Optional[Character]:
        await asyncio.sleep(1)
        return Droid(
            id="2001",
            name="R2-D2",
            appears_in=[Episode.NEWHOPE, Episode.EMPIRE, Episode.JEDI],
            primary_function="Astromech",
        )


@app.route('/')
class Schema(pygraphy.Schema):
    query: Optional[Query]


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

```

## Installation

`pip install pygraphy`


## Feature

### Dataclass Model

Inspired by [Strawberry](https://github.com/strawberry-graphql/strawberry), Pygraphy uses dataclass to define the model.
```python
class Patron(pygraphy.Object):
    id: str
    name: str
    age: int


class Query(pygraphy.Query):
    """
    Query doc also can be printed
    """

    @pygraphy.field
    def patron(self) -> Patron:
        """
        Return the patron
        """
        return Patron(id='1', name='Gwo', age=25)

    @pygraphy.field
    def exception(self, content: str) -> str:
        raise RuntimeError(content)

print(Query)  # Have a try!
'''
"""
Query doc also can be printed
"""
type Query {
  __schema: __Schema!
  __type(
    name: String!
  ): __Type
  exception(
    content: String!
  ): String!
  "Return the patron"
  patron: Patron!
}
'''
```

### Asyncio Support

Pygraphy supports async/await; executions of queries are asynchronous. Also, it implements the Starlette endpoint as a built-in Web interface, and users can use a full set of Python native solutions of concurrency.
```python
import asyncio


class Query(pygraphy.Query):

    @pygraphy.field
    async def foo(self) -> bool:
        """
        Sample of asyncio
        """
        await asyncio.sleep(0.1)
        return True

    @pygraphy.field
    async def bar(self) -> bool:
        """
        Run concurrent with foo
        """
        await asyncio.sleep(0.1)
        return True

```

### Context Management

Pygraphy uses [ContextVars](https://docs.python.org/3/library/contextvars.html#module-contextvars) to manage the context of queries, it is easier to use than pass context everywhere.
```python
from pygraphy import context


class Schema(Object):

    @field
    def query_type(self):
        """
        The type that query operations will be rooted at.
        """
        schema = context.get().schema
        query_type = schema.__fields__['query'].ftype
        # Do whatever you want
```

### Introspection and Playground

Pygraphy implements the [GraphQL introspection specification](https://graphql.github.io/graphql-spec/June2018/#sec-Introspection) and it also development by itself, see [pygraphy/introspection.py](pygraphy/introspection.py) and get more informations.

[GraphQL Playground](https://github.com/prisma/graphql-playground) is also integrated into Pygraphy, run the Starlette server, and use browser request the API you defined, make API testing easier.


## Comparation with GraphQL-Core(-Next)

### Advantages
[GraphQL-Core-Next](https://github.com/graphql-python/graphql-core-next) is the official supporting implementation of GraphQL, and it is only a basic library. Generally, you would use Graphene or other wrapper libraries bases on it. Pygraphy is an integrated library that includes data mapping and model definition.

GraphQL-Core-Next is directly translated from GraphQL.js, this leads to some weird behaviors such as [graphql-core-next/issues/37](https://github.com/graphql-python/graphql-core-next/issues/37#issuecomment-503499643), and it is too tough to make a wrapper for walking around. Pygraphy is another implementation wrote in a more pythonic way, it is friendlier to developers.

### Disadvantages

Pygraphy is still in pre-alpha version, buggy and need stable, welcome feedback.

Pygraphy **does not support** full features of GraphQL according to Spec right now, the rest part of Spec will be integrated literally in the future, it contains
  - Derectives
  - Subscribe Method
  - ID Scalar
  - Type Extensions
  - Some Validation Check

Most of features are already implemented so do not panic.
