import typing
from pygraphy.utils import patch_indents, is_union, is_optional, is_list


def test_patch_indents():
    assert patch_indents('test {\ntest\n}') == 'test {\ntest\n}'
    assert patch_indents('test {\ntest\n}', indent=1) == '  test {\n  test\n  }'


def test_is_union():
    assert is_union(typing.Optional[str]) is True
    assert is_union(typing.Union[str, int, None]) is True
    assert is_union(str) is False


def test_is_optional():
    assert is_optional(typing.Optional[str]) is True
    assert is_optional(typing.Union[str, None]) is True
    assert is_optional(typing.Union[str, int, None]) is False


def test_is_list():
    assert is_list(typing.List[str]) is True
    assert is_list(typing.Union[str, int, None]) is False
