from __future__ import annotations
import pygraphy
from typing import Optional


class WhereInput(pygraphy.Input):
    _and: Optional[WhereInput] = None


class Query(pygraphy.Query):

    @pygraphy.field
    def foo(self, arg: WhereInput) -> int:
        return 0


class Schema(pygraphy.Schema):
    query: Optional[Query]


def test_recursive_definition():
    print(str(Schema))
