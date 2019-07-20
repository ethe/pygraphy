# Pygraphy

*A modern and pythonic approach of GraphQL, painless GraphQL developing experience for Pythonista.*

[![Build Status](https://travis-ci.org/ethe/pygraphy.svg?branch=master)](https://travis-ci.org/ethe/pygraphy)
[![codecov](https://codecov.io/gh/ethe/pygraphy/branch/master/graph/badge.svg)](https://codecov.io/gh/ethe/pygraphy)
[![pypi](https://badge.fury.io/py/pygraphy.svg)](https://pypi.org/project/pygraphy/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pygraphy.svg)](https://pypi.org/project/pygraphy/)

---

## Introduction

Pygraphy is another Python approach of GraphQL. Compare with Graphql-Core-(Next), Pygraphy is totally rewrite the GraphQL model declaration system in pythonic way, rather than copying GraphQL.js 1:1. Therefore, Pygraphy is able to provide native developing experience with Pythonic way.

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
    Droid object
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

## Requirements

Python 3.7+

## Installation

Pygraphy supports two installation mode:

1. `pip install 'pygraphy[web]'` for users want to use Pygraphy with built-in web app together like quickstart.
1. `pip install 'pygraphy'` for users want to use bare Pygraphy executor and model declaration system.
