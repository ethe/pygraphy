import inspect
import dataclasses
from typing import Mapping, Optional
from graphql.language import parse
from graphql.language.ast import OperationDefinitionNode, OperationType
from graphql.language.ast import (
    IntValueNode,
    FloatValueNode,
    BooleanValueNode,
    StringValueNode,
    NullValueNode,
    EnumValueNode,
    ListValueNode,
    ObjectValueNode
)
from .utils import (
    patch_indents,
    is_union,
    is_optional,
    is_list,
    to_camel_case,
    to_snake_case
)
from .exceptions import GraphQLError


@dataclasses.dataclass
class Field:
    name: str
    ftype: type
    description: Optional[str]

    def __str__(self):
        literal = f'{self.name}: {convert_type(self.ftype)}'
        if self.description:
            literal = f'"{self.description}"\n' + literal
        return literal


@dataclasses.dataclass
class ResolverField(Field):
    params: Mapping[str, type]

    def __str__(self):
        if not self.params:
            literal = f'{self.name}(): {convert_type(self.ftype)}'
        else:
            literal = f'{self.name}' \
                + '(\n' \
                + patch_indents(self.print_args(), indent=1) \
                + f'\n): {convert_type(self.ftype)}'
        if self.description:
            literal = f'"{self.description}"\n' + literal
        return literal

    def print_args(self):
        literal = ''
        for name, param in self.params.items():
            literal += f'{name}: {convert_type(param)}\n'
        return literal[:-1]


class ObjectType(type):

    def __new__(cls, name, bases, attrs):
        attrs['__fields__'] = {}
        attrs['__description__'] = None
        cls = dataclasses.dataclass(type.__new__(cls, name, bases, attrs))
        sign = inspect.signature(cls)
        cls.__description__ = inspect.getdoc(cls)
        for name, t in sign.parameters.items():
            cls.__fields__[to_camel_case(name)] = Field(
                name=to_camel_case(name), ftype=t.annotation, description=None
            )
        for name, attr in attrs.items():
            if hasattr(attr, '__is_field__'):
                sign = inspect.signature(attr)
                cls.__fields__[to_camel_case(name)] = ResolverField(
                    name=to_camel_case(name),
                    ftype=sign.return_annotation,
                    params=cls.remove_self(sign.parameters),
                    description=inspect.getdoc(attr)
                )
        cls.check()
        return cls

    def __str__(cls):
        return (
            f'{cls.print_description()}'
            + f'type {cls.__name__} '
            + '{\n'
            + f'{patch_indents(cls.print_resolver_field(), indent=1)}'
            + '\n}'
        )

    @staticmethod
    def remove_self(param_dict):
        result = {}
        first_param = True
        for name, param in param_dict.items():
            if first_param:
                first_param = False
                continue
            result[name] = param.annotation
        return result

    def print_description(cls, indent=0):
        return patch_indents(
            f'"""\n{cls.__description__}\n"""\n' if cls.__description__ else '',
            indent=indent
        )

    def print_resolver_field(cls, indent=0):
        literal = ''
        for _, field in cls.__fields__.items():
            literal += f'{field}\n'
        return patch_indents(literal[:-1], indent)

    def check(cls):
        for _, field in cls.__fields__.items():
            if not isinstance(field, (Field, ResolverField)):
                raise ValueError(f'{field} is an invalid field type')
            try:
                convert_type(field.ftype)
            except ValueError:
                raise ValueError(
                    f'Field type needs be object or built-in type, rather than {field.ftype}'
                )
            if isinstance(field.ftype, ObjectType):
                field.ftype.check()


class SchemaType(ObjectType):
    VALID_ROOT_TYPES = {'query', 'mutation'}

    def __new__(cls, name, bases, attrs):
        attrs['registered_type'] = []
        cls = ObjectType.__new__(cls, name, bases, attrs)
        cls.register_types(cls.__fields__)
        return cls

    def register_types(cls, fields):
        for _, field in fields.items():
            checking_type = None
            if hasattr(field, 'ftype'):
                if isinstance(field.ftype, ObjectType):
                    checking_type = field.ftype
                elif is_union(field.ftype) or is_list(field.ftype):
                    cls.register_types({str(t): t for t in field.ftype.__args__})
            elif isinstance(field, ObjectType):
                checking_type = field
            elif is_union(field) or is_list(field):
                cls.register_types({str(t): t for t in field.__args__})

            if checking_type:
                cls.registered_type.append(checking_type)
                if isinstance(checking_type, ResolverField):
                    # register params
                    cls.register_types(checking_type.params)
                cls.register_types(checking_type.__fields__)

                if is_union(checking_type) or is_list(checking_type):
                    cls.register_types({str(t): t for t in checking_type.__args__})

    def check(cls):
        for name, field in cls.__fields__.items():
            if name not in cls.VALID_ROOT_TYPES:
                raise ValueError(
                    f'The valid root type must be {cls.VALID_ROOT_TYPES}, rather than {name}'
                )
            if not isinstance(field, (Field, ResolverField)):
                raise ValueError(f'{field} is an invalid field type')
            if not isinstance(field.ftype, ObjectType):
                raise ValueError(f'Root type must be an Object, rather than {field.ftype}')
        ObjectType.check(cls)

    def __str__(cls):
        string = ''
        for rtype in cls.registered_type:
            string += (str(rtype) + '\n\n')
        schema = (
            f'{cls.print_description()}'
            + f'schema '
            + '{\n'
            + f'{patch_indents(cls.print_resolver_field(), indent=1)}'
            + '\n}'
        )
        return string + schema


class Object(metaclass=ObjectType):

    @classmethod
    def field(cls, method):
        """
        Mark class method as a resolver
        """
        method.__is_field__ = True
        return method

    def __resolve__(self, nodes):
        self.resolver_results = {}
        for node in nodes:
            name = node.name.value
            field = self.__fields__.get(name)
            if not field:
                raise GraphQLError(
                    f"Cannot query field '{name}' on type '{type(self)}'.",
                    node.loc.source.get_location(node.name.loc.start)
                )
            if not isinstance(field, ResolverField):
                continue
            resolver = getattr(self, to_snake_case(name), None)
            if not resolver:
                raise GraphQLError(
                    f"Cannot query field '{name}' on type '{type(self)}'.",
                    node.loc.source.get_location(node.name.loc.start)
                )
            kwargs = {}
            for arg in node.arguments:
                kwargs[to_snake_case(arg.name.value)] = self.__convert_graphql_type__(arg.value, field)
            result = resolver(**kwargs)
            if isinstance(result, Object):
                result.__resolve__(node.selection_set.selections)
            self.resolver_results[to_snake_case(name)] = resolver(**kwargs)

    def __convert_graphql_type__(self, value, field):
        if isinstance(value, IntValueNode):
            return int(value.value)
        elif isinstance(value, FloatValueNode):
            return float(value.value)
        elif isinstance(value, BooleanValueNode):
            return bool(value.value)
        elif isinstance(value, StringValueNode):
            return value.value
        elif isinstance(value, NullValueNode):
            return None
        elif isinstance(value, ListValueNode):
            return [self.__convert_graphql_type__(v) for v in value.values]
        elif isinstance(value, EnumValueNode):
            pass
        elif isinstance(value, ObjectValueNode):
            pass
        raise ValueError(f'Can not convert {value} to basic type')


class Schema(metaclass=SchemaType):

    @classmethod
    def execute(cls, query):
        document = parse(query)
        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue
            if definition.operation is OperationType.QUERY:
                query_object = cls.__fields__['query'].ftype()
                query_object.__resolve__(
                    definition.selection_set.selections
                )
                return query_object


VALID_BASIC_TYPES = {
    str: 'String',
    int: 'Int',
    float: 'Float',
    bool: 'Boolean',
}


def convert_type(gtype, nonnull=True):
    literal = None
    if is_union(gtype):
        if is_optional(gtype):
            return f'{convert_type(gtype.__args__[0], nonnull=False)}'
    elif is_list(gtype):
        literal = f'[{convert_type(gtype.__args__[0])}]'
    elif isinstance(gtype, ObjectType):
        literal = f'{gtype.__name__}'
    elif gtype in VALID_BASIC_TYPES:
        literal = VALID_BASIC_TYPES[gtype]
    elif gtype is None or gtype == type(None):  # noqa
        return 'null'
    else:
        raise ValueError(f'Can not convert type {gtype} to GraphQL type')

    if nonnull:
        literal += '!'
    return literal
