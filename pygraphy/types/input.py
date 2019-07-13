from pygraphy.exceptions import ValidationError
from pygraphy.utils import patch_indents
from .base import print_type, load_literal_value
from .object import ObjectType
from .field import Field, FieldableType
from .union import UnionType


class InputType(FieldableType):

    def validate(cls):
        for _, field in cls.__fields__.items():
            if not isinstance(field, Field):
                raise ValidationError(f'{field} is an invalid field type')
            try:
                print_type(
                    field.ftype, except_types=(ObjectType, UnionType)
                )
            except ValueError:
                raise ValidationError(
                    f'Field type needs be object or built-in type,'
                    f' rather than {field.ftype}'
                )
            if isinstance(field.ftype, InputType):
                field.ftype.validate()

    def __str__(cls):
        return (
            f'{cls.print_description()}'
            + f'input {cls.__name__} '
            + '{\n'
            + f'{patch_indents(cls.print_field(), indent=1)}'
            + '\n}'
        )

    def print_field(cls, indent=0):
        literal = ''
        for _, field in cls.__fields__.items():
            literal += f'{field}\n'
        return patch_indents(literal[:-1], indent)


class Input(metaclass=InputType):

    @classmethod
    def __resolve__(cls, node):
        data = {}
        for field in node.fields:
            data[field.name.value] = load_literal_value(field.value, cls)
        return cls(**data)
