import sys
import json
import typing
import inspect
import dataclasses
from typing import (
    Mapping,
    Optional,
    _eval_type,
    ForwardRef,
    Union as PyUnion,
    List
)
from pygraphy.utils import (
    patch_indents,
    is_union,
    is_list,
    to_camel_case,
    to_snake_case
)
from pygraphy.exceptions import ValidationError
from .base import print_type, GraphQLType


if typing.TYPE_CHECKING:
    from .object import Object


def field(method):
    """
    Mark class method as a resolver
    """
    method.__is_field__ = True
    return method


@dataclasses.dataclass
class Field:
    _obj: 'Object'
    name: str
    _ftype: type
    description: Optional[str]

    def __str__(self):
        literal = f'{to_camel_case(self.name)}: {print_type(self.ftype)}'
        if self.description:
            literal = f'"{self.description}"\n' + literal
        return literal

    @property
    def ftype(self):
        return self.replace_forwarded_type(self._ftype)

    def replace_forwarded_type(self, ptype):
        if hasattr(ptype, '__args__'):
            args = [self.replace_forwarded_type(t) for t in ptype.__args__]
            if is_union(ptype):
                return PyUnion[tuple(args)]
            elif is_list(ptype):
                return List[tuple(args)]
        elif isinstance(ptype, (str, ForwardRef)):
            return self.get_type(ptype)
        return ptype

    def get_type(self, forwarded_type):
        actual_type = None
        for base in self._obj.__mro__:
            base_globals = sys.modules[base.__module__].__dict__
            ref = forwarded_type
            if isinstance(forwarded_type, str):
                ref = ForwardRef(forwarded_type, is_argument=False)
            try:
                actual_type = _eval_type(ref, base_globals, None)
                break
            except NameError:
                continue
        if not actual_type:
            raise ValidationError(f'Can not find type {forwarded_type}')
        return actual_type


@dataclasses.dataclass
class ResolverField(Field):
    _params: Mapping[str, inspect.Parameter]

    @property
    def params(self):
        param_dict = {}
        for name, param in self._params.items():
            param_dict[name] = self.replace_forwarded_type(param.annotation)
        return param_dict

    def __str__(self):
        if not self.params:
            literal = f'{to_camel_case(self.name)}: {print_type(self.ftype)}'
        else:
            literal = f'{to_camel_case(self.name)}' \
                + '(\n' \
                + patch_indents(self.print_args(), indent=1) \
                + f'\n): {print_type(self.ftype)}'
        if self.description:
            literal = f'"{self.description}"\n' + literal
        return literal

    def print_args(self):
        literal = ''
        for name, param in self.params.items():
            literal += f'{to_camel_case(name)}:' \
                       f' {print_type(param)}' \
                       f'{self.print_default_value(name)}\n'  # noqa
        return literal[:-1]

    def print_default_value(self, name):
        default = self._params[name].default
        return f' = {json.dumps(default)}' if default != inspect._empty else ''


class FieldableType(GraphQLType):

    def __new__(cls, name, bases, attrs):
        attrs['__fields__'] = {}
        attrs['__description__'] = None
        attrs['__validated__'] = False
        cls = dataclasses.dataclass(super().__new__(cls, name, bases, attrs))
        sign = inspect.signature(cls)
        cls.__description__ = inspect.getdoc(cls)
        for name, t in sign.parameters.items():
            cls.__fields__[to_snake_case(name)] = Field(
                name=to_snake_case(name), _ftype=t.annotation, description=None, _obj=cls
            )
        return cls

    def print_field(cls, indent=0):
        literal = ''
        for _, field in cls.__fields__.items():
            literal += f'{field}\n'
        return patch_indents(literal[:-1], indent)
