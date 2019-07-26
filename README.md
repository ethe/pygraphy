# Pygraphy
A modern pythonic GraphQL implementation, painless GraphQL developing experience for Pythonista.

[![Build Status](https://travis-ci.org/ethe/pygraphy.svg?branch=master)](https://travis-ci.org/ethe/pygraphy)
[![codecov](https://codecov.io/gh/ethe/pygraphy/branch/master/graph/badge.svg)](https://codecov.io/gh/ethe/pygraphy)
[![pypi](https://badge.fury.io/py/pygraphy.svg)](https://pypi.org/project/pygraphy/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pygraphy.svg)](https://pypi.org/project/pygraphy/)


## Document

See [official docs](https://pygraphy.org/).


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

### Web Server Required
`pip install 'pygraphy[web]'`

### Standalone Model and Query Handler
`pip install 'pygraphy'`


## Features

- Clean room Pythonic schema definition system
- Model definition bases on Python Dataclass
- Python Asyncio support
- Context management bases on Python Context Variables
- Introspection and GraphQL Playground support


## Comparation with GraphQL-Core(-Next)

### Advantages

[GraphQL-Core-Next](https://github.com/graphql-python/graphql-core-next) is the official supporting implementation of GraphQL, and it is only a basic library. Generally, you should use Graphene or other wrapper libraries bases on it. Pygraphy is an integrated library that includes data mapping and model definition.

GraphQL-Core-Next is directly translated from GraphQL.js, this leads to some weird behaviors such as [graphql-core-next/issues/37](https://github.com/graphql-python/graphql-core-next/issues/37#issuecomment-511633135), and it is too tough to make a wrapper for walking around. Pygraphy rewrites the schema definition system in a more pythonic way. By using Python Metaclass, Pygraphy supports class-style schema definition naturally. There is no more inharmony between lambda function resolver (ugly Js style) and instance method resolver.

By using Context Variables which is added into Python in version 3.7, Pygraphy does not need to pass context through the call chain like graphql-core-next.

Also, Pygraphy is faster than graphql-core-next, you can check benchmark results as below.

And more, Pygraphy clearly support stateful subscription method with Python Asynchronous Generators, which is not elaborate in graphql-core-next.

### Disadvantages

Pygraphy is still in pre-alpha version, and need stable, welcome feedback.

Pygraphy **does not support** full features of GraphQL according to Spec right now, the rest part of Spec will be integrated literally in the future, it contains
  - Derectives
  - ID Scalar
  - Type Extensions
  - Some Validation Check

Most of features are already implemented so do not panic.


## Benchmark

Compare with Strawberry / graphql-core-next, Pygraphy is 4.5 times faster than it.

```
↳ uname -a
Darwin Workstation.local 19.0.0 Darwin Kernel Version 19.0.0: Thu Jul 11 18:37:36 PDT 2019; root:xnu-6153.0.59.141.4~1/RELEASE_X86_64 x86_64
↳ python -V
Python 3.7.2
↳ time python benchmark/test_pygraphy.py
python benchmark/test_pygraphy.py  3.48s user 0.10s system 99% cpu 3.596 total
↳ time python benchmark/test_strawberry.py
python benchmark/test_strawberry.py  16.05s user 0.16s system 99% cpu 16.257 total
```
