from typing import Optional, Union, Dict, List
from pygraphql import Object, Field, ResolverField


def test_model_definition():
    class Foo(Object):
        "description bar"
        a: str
        @Object.field
        def foo(a: int) -> Optional[str]:
            "description foo"
            pass

    assert Foo.__fields__ == {
        'a': Field(name='a', ftype=str, description=None),
        'foo': ResolverField(
            name='foo',
            ftype=Union[str, None],
            description='description foo', params={'a': int}
        )
    }
    assert Foo.__description__ == "description bar"

    try:
        class Foo(Object):
            @Object.field
            def foo(a: int) -> Dict:
                "description foo"
                pass
    except ValueError:
        return
    assert False  # never reached


def test_resolver_field_definition():
    class Foo(Object):
        "description bar"
        a: str
        @Object.field
        def foo(a: int) -> Optional[str]:
            "description foo"
            pass

    foo_field = Foo.__fields__['foo']
    assert foo_field.description == "description foo"
    assert foo_field.params['a'] == int


def test_field_definition():
    class Foo(Object):
        "description bar"
        a: Optional[str]

    assert Foo.__fields__['a'].ftype == Optional[str]


def test_model_literal():
    class Foo(Object):
        "description bar"
        a: str
        @Object.field
        def foo(a: int) -> Optional[List[str]]:
            "description foo"
            pass
    assert str(Foo) == '"""\ndescription bar\n"""\ntype Foo {\n  a: String!\n  "description foo"\n  foo(\n    a: Int!\n  ): [String!]\n}'
