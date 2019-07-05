import sys
import json
import inspect
import dataclasses
from typing import (
    Mapping,
    Optional,
    _eval_type,
    ForwardRef,
    Union as PythonUnion,
    List
)
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


class GraphQLEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Object):
            attrs = {}
            for field in obj.__fields__.values():
                snake_name = to_snake_case(field.name)
                if isinstance(field, ResolverField):
                    if snake_name in obj.resolver_results:
                        attrs[field.name] = obj.resolver_results[snake_name]
                elif isinstance(field, Field):
                    if hasattr(obj, snake_name):
                        attrs['snake_name'] = getattr(obj, snake_name)
            return attrs
        return super().default(obj)


@dataclasses.dataclass
class Field:
    _obj: 'Object'
    name: str
    _ftype: type
    description: Optional[str]

    def __str__(self):
        literal = f'{self.name}: {print_type(self.ftype)}'
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
                return PythonUnion[tuple(args)]
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
            except NameError:
                continue
        if not actual_type:
            raise NameError(f'Can not find type {forwarded_type}')
        return actual_type


@dataclasses.dataclass
class ResolverField(Field):
    _params: Mapping[str, type]

    @property
    def params(self):
        param_dict = {}
        for name, param in self._params.items():
            param_dict[name] = self.replace_forwarded_type(param)
        return param_dict

    def __str__(self):
        if not self.params:
            literal = f'{self.name}(): {print_type(self.ftype)}'
        else:
            literal = f'{self.name}' \
                + '(\n' \
                + patch_indents(self.print_args(), indent=1) \
                + f'\n): {print_type(self.ftype)}'
        if self.description:
            literal = f'"{self.description}"\n' + literal
        return literal

    def print_args(self):
        literal = ''
        for name, param in self.params.items():
            literal += f'{name}: {print_type(param)}\n'
        return literal[:-1]


class GraphQLType(type):
    pass


class ObjectType(GraphQLType):

    def __new__(cls, name, bases, attrs):
        attrs['__fields__'] = {}
        attrs['__description__'] = None
        attrs['__validated__'] = True
        cls = dataclasses.dataclass(type.__new__(cls, name, bases, attrs))
        sign = inspect.signature(cls)
        cls.__description__ = inspect.getdoc(cls)
        for name, t in sign.parameters.items():
            cls.__fields__[to_camel_case(name)] = Field(
                name=to_camel_case(name), _ftype=t.annotation, description=None, _obj=cls
            )
        for name, attr in attrs.items():
            if hasattr(attr, '__is_field__'):
                sign = inspect.signature(attr)
                cls.__fields__[to_camel_case(name)] = ResolverField(
                    name=to_camel_case(name),
                    _ftype=sign.return_annotation,
                    _params=cls.remove_self(sign.parameters),
                    description=inspect.getdoc(attr),
                    _obj=cls
                )
        return cls

    def __str__(cls):
        return (
            f'{cls.print_description()}'
            + f'type {cls.__name__} '
            + '{\n'
            + f'{patch_indents(cls.print_field(), indent=1)}'
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

    def print_field(cls, indent=0):
        literal = ''
        for _, field in cls.__fields__.items():
            literal += f'{field}\n'
        return patch_indents(literal[:-1], indent)

    def validate(cls):
        if cls.__validated__:
            return
        cls.__validated__ = True
        for _, field in cls.__fields__.items():
            if not isinstance(field, (Field, ResolverField)):
                raise ValueError(f'{field} is an invalid field type')
            print_type(field.ftype, except_types=(InputType))
            if isinstance(field, ResolverField):
                for gtype in field.params.values():
                    print_type(gtype)
            if isinstance(field.ftype, ObjectType):
                field.ftype.validate()


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
                slot = field.params.get(arg.name.value)
                if not slot:
                    raise ValueError(f'Can not find {arg.value.name} as param in {field.name}')
                slot_type = slot if slot in VALID_BASIC_TYPES else slot.ftype
                kwargs[to_snake_case(arg.name.value)] = load_literal_value(arg, slot_type)
            result = resolver(**kwargs)
            if isinstance(result, Object):
                result.__resolve__(node.selection_set.selections)
            self.resolver_results[to_snake_case(name)] = resolver(**kwargs)


class SchemaType(ObjectType):
    VALID_ROOT_TYPES = {'query', 'mutation'}

    def __new__(cls, name, bases, attrs):
        attrs['registered_type'] = []
        cls = ObjectType.__new__(cls, name, bases, attrs)
        cls.validated_type = []
        cls.validate()
        cls.register_fields_type(cls.__fields__.values())
        return cls

    def register_fields_type(cls, fields):
        param_return_types = []
        for field in fields:
            param_return_types.append(field.ftype)
            if isinstance(field, ResolverField):
                param_return_types.extend(field.params.values())
        cls.register_types(param_return_types)

    def register_types(cls, types):
        for ptype in types:
            if ptype in cls.validated_type:
                continue
            cls.validated_type.append(ptype)

            if isinstance(ptype, ObjectType):
                cls.registered_type.append(ptype)
                cls.register_fields_type(ptype.__fields__.values())
            elif is_union(ptype) or is_list(ptype):
                cls.register_types(ptype.__args__)
            elif isinstance(ptype, UnionType):
                cls.registered_type.append(ptype)
                cls.register_types(ptype.members)
            elif isinstance(ptype, InputType):
                cls.registered_type.append(ptype)
                cls.register_fields_type(ptype.__fields__.values())
            else:
                # Other basic types, do not need be handled
                pass

    def validate(cls):
        for name, field in cls.__fields__.items():
            if name not in cls.VALID_ROOT_TYPES:
                raise ValueError(
                    f'The valid root type must be {cls.VALID_ROOT_TYPES}, rather than {name}'
                )
            if not isinstance(field, Field):
                raise ValueError(f'{field} is an invalid field type')
            if not isinstance(field.ftype, ObjectType):
                raise ValueError(f'Root type must be an Object, rather than {field.ftype}')
        ObjectType.validate(cls)

    def __str__(cls):
        string = ''
        for rtype in cls.registered_type:
            string += (str(rtype) + '\n\n')
        schema = (
            f'{cls.print_description()}'
            + f'schema '
            + '{\n'
            + f'{patch_indents(cls.print_field(), indent=1)}'
            + '\n}'
        )
        return string + schema


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
                return json.dumps(query_object, cls=GraphQLEncoder)


class UnionType(GraphQLType):

    def __new__(cls, name, bases, attrs):
        if 'members' not in attrs:
            raise RuntimeError('Union type must has members attribute')
        if not isinstance(attrs['members'], tuple):
            raise RuntimeError('Members must be tuple')
        for member in attrs['members']:
            if not isinstance(member, ObjectType):
                raise RuntimeError('The member of Union type must be Object')
        return type.__new__(cls, name, bases, attrs)

    def __str__(cls):
        description = inspect.getdoc(cls)
        description_literal = f'"""\n{inspect.getdoc(cls)}\n"""\n' if description else ''
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


class EnumType(GraphQLType):

    def __str__(cls):
        description = inspect.getdoc(cls)
        description_literal = f'"""\n{inspect.getdoc(cls)}\n"""\n' if description else ''
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
            if name.startswith('__'):
                continue
            literal += (name + '\n')
        return literal[:-1] if literal.endswith('\n') else literal


class Enum(metaclass=EnumType):
    pass


class InputType(GraphQLType):

    def __new__(cls, name, bases, attrs):
        attrs['__fields__'] = {}
        attrs['__description__'] = None
        cls = dataclasses.dataclass(type.__new__(cls, name, bases, attrs))
        sign = inspect.signature(cls)
        cls.__description__ = inspect.getdoc(cls)
        for name, t in sign.parameters.items():
            cls.__fields__[to_camel_case(name)] = Field(
                name=to_camel_case(name), _ftype=t.annotation, description=None, _obj=cls
            )
        cls.validate()
        return cls

    def validate(cls):
        for _, field in cls.__fields__.items():
            if not isinstance(field, Field):
                raise ValueError(f'{field} is an invalid field type')
            try:
                print_type(field.ftype, except_types=(ObjectType, UnionType))
            except ValueError:
                raise ValueError(
                    f'Field type needs be object or built-in type, rather than {field.ftype}'
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

    def print_description(cls, indent=0):
        return patch_indents(
            f'"""\n{cls.__description__}\n"""\n' if cls.__description__ else '',
            indent=indent
        )

    def print_field(cls, indent=0):
        literal = ''
        for _, field in cls.__fields__.items():
            literal += f'{field}\n'
        return patch_indents(literal[:-1], indent)


class Input(metaclass=InputType):

    @classmethod
    def __load__(cls, node):
        data = {}
        for field in node.fields:
            data[field.name.value] = load_literal_value(field, cls)
        return cls(**data)


def load_literal_value(node, ptype):
    if isinstance(node.value, IntValueNode):
        return int(node.value.value)
    elif isinstance(node.value, FloatValueNode):
        return float(node.value.value)
    elif isinstance(node.value, BooleanValueNode):
        return bool(node.value.value)
    elif isinstance(node.value, StringValueNode):
        return node.value.value
    elif isinstance(node.value, NullValueNode):
        return None
    elif isinstance(node.value, ListValueNode):
        return [load_literal_value(v) for v in node.value.values]
    elif isinstance(node.value, EnumValueNode):
        value = getattr(ptype, node.value.value)
        if not value:
            raise ValueError(
                f'{node.value.value} is not a valid member of {type}'
            )
    elif isinstance(node.value, ObjectValueNode):
        return ptype.__fields__[node.name.value].__load__(node.value.fields)
    raise ValueError(f'Can not convert {node.value.value}')


VALID_BASIC_TYPES = {
    str: 'String',
    int: 'Int',
    float: 'Float',
    bool: 'Boolean',
}


def print_type(gtype, nonnull=True, except_types=()):
    if isinstance(gtype, except_types):
        raise ValueError(f'{gtype} is not a valid type')
    literal = None
    if is_union(gtype):
        if is_optional(gtype):
            return f'{print_type(gtype.__args__[0], nonnull=False, except_types=except_types)}'
        else:
            raise ValueError(f'Native Union type is not supported except Optional')
    elif is_list(gtype):
        literal = f'[{print_type(gtype.__args__[0], except_types=except_types)}]'
    elif isinstance(gtype, ObjectType):
        literal = f'{gtype.__name__}'
    elif gtype in VALID_BASIC_TYPES:
        literal = VALID_BASIC_TYPES[gtype]
    elif gtype is None or gtype == type(None):  # noqa
        return 'null'
    elif isinstance(gtype, UnionType):
        literal = f'{gtype.__name__}'
    elif isinstance(gtype, EnumType):
        literal = f'{gtype.__name__}'
    elif isinstance(gtype, InputType):
        literal = f'{gtype.__name__}'
    else:
        raise ValueError(f'Can not convert type {gtype} to GraphQL type')

    if nonnull:
        literal += '!'
    return literal
