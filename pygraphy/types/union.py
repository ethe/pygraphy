import inspect
from pygraphy.utils import patch_indents
from pygraphy.exceptions import ValidationError
from .base import GraphQLType
from .object import ObjectType


class UnionType(GraphQLType):

    def __new__(cls, name, bases, attrs):
        if 'members' not in attrs:
            raise ValidationError('Union type must has members attribute')
        if not isinstance(attrs['members'], tuple):
            raise ValidationError('Members must be tuple')
        for member in attrs['members']:
            if not isinstance(member, ObjectType):
                raise ValidationError('The member of Union type must be Object')
        return super().__new__(cls, name, bases, attrs)

    def __str__(cls):
        description = inspect.getdoc(cls)
        description_literal = f'"""\n{description}\n"""\n' if description else ''  # noqa
        return (
            description_literal
            + f'union {cls.__name__} =\n'
            + f'{patch_indents(cls.print_union_member(), indent=1)}'
        )

    def print_union_member(cls):
        literal = ''
        for ptype in cls.members:
            literal += f'| {ptype.__name__}\n'
        return literal[:-1] if literal.endswith('\n') else literal


class Union(metaclass=UnionType):
    members = ()
