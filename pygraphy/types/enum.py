import inspect
from enum import EnumMeta, Enum as PyEnum
from pygraphy.utils import patch_indents


class EnumType(EnumMeta):

    def __str__(cls):
        description = inspect.getdoc(cls)
        description_literal = f'"""\n{description}\n"""\n' if description else ''  # noqa
        return (
            description_literal
            + f'enum {cls.__name__} '
            + '{\n'
            + f'{patch_indents(cls.print_enum_values(), indent=1)}'
            + '\n}'
        )

    def print_enum_values(cls):
        literal = ''
        for name, _ in cls.__dict__.items():
            if name.startswith('_'):
                continue
            literal += (name + '\n')
        return literal[:-1] if literal.endswith('\n') else literal


class Enum(PyEnum, metaclass=EnumType):
    pass
