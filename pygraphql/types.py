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
from enum import EnumMeta, Enum as PyEnum
from graphql.language import parse
from graphql.language.ast import (
    OperationDefinitionNode,
    OperationType,
    IntValueNode,
    FloatValueNode,
    BooleanValueNode,
    StringValueNode,
    NullValueNode,
    EnumValueNode,
    ListValueNode,
    ObjectValueNode,
    InlineFragmentNode,
    FragmentSpreadNode
)
from .utils import (
    patch_indents,
    is_union,
    is_optional,
    is_list,
    to_camel_case,
    to_snake_case
)
from .exceptions import RuntimeError, ValidationError
from .encoder import GraphQLEncoder


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
            literal += f'{to_camel_case(name)}: {print_type(param)}{self.print_default_value(name)}\n'  # noqa
        return literal[:-1]

    def print_default_value(self, name):
        default = self._params[name].default
        return f' = {json.dumps(default)}' if default != inspect._empty else ''


class GraphQLType(type):

    def print_description(cls, indent=0):
        return patch_indents(
            f'"""\n{cls.__description__}\n"""\n' if cls.__description__ else '',  # noqa
            indent=indent
        )


def field(method):
    """
    Mark class method as a resolver
    """
    method.__is_field__ = True
    return method


class FieldableType(GraphQLType):

    def __new__(cls, name, bases, attrs):
        attrs['__fields__'] = {}
        attrs['__description__'] = None
        attrs['__validated__'] = True
        cls = dataclasses.dataclass(super().__new__(cls, name, bases, attrs))
        sign = inspect.signature(cls)
        cls.__description__ = inspect.getdoc(cls)
        for name, t in sign.parameters.items():
            cls.__fields__[name] = Field(
                name=name, _ftype=t.annotation, description=None, _obj=cls
            )
        return cls

    def print_field(cls, indent=0):
        literal = ''
        for _, field in cls.__fields__.items():
            literal += f'{field}\n'
        return patch_indents(literal[:-1], indent)


class InterfaceType(FieldableType):

    def __new__(cls, name, bases, attrs):
        cls = super().__new__(cls, name, bases, attrs)
        for name, attr in attrs.items():
            if hasattr(attr, '__is_field__'):
                sign = inspect.signature(attr)
                cls.__fields__[name] = ResolverField(
                    name=name,
                    _ftype=sign.return_annotation,
                    _params=cls.remove_self(sign.parameters),
                    description=inspect.getdoc(attr),
                    _obj=cls
                )
        return cls

    @staticmethod
    def remove_self(param_dict):
        result = {}
        first_param = True
        for name, param in param_dict.items():
            if first_param:
                first_param = False
                continue
            result[name] = param
        return result

    def __str__(cls):
        return (
            f'{cls.print_description()}'
            + f'interface {cls.__name__} '
            + '{\n'
            + f'{patch_indents(cls.print_field(), indent=1)}'
            + '\n}'
        )


class Interface(metaclass=InterfaceType):
    pass


class ObjectType(InterfaceType):

    def __str__(cls):
        return (
            f'{cls.print_description()}'
            + f'type {cls.__name__}{cls.print_interface_implement()} '
            + '{\n'
            + f'{patch_indents(cls.print_field(), indent=1)}'
            + '\n}'
        )

    def print_interface_implement(cls):
        literal = ''
        for base in cls.__bases__:
            if isinstance(base, ObjectType):
                continue
            if not literal:
                literal = f' implements {base.__name__}'
            else:
                literal += f' & {base.__name__}'
        return literal

    def validate(cls):
        if cls.__validated__:
            return
        cls.__validated__ = True
        for _, field in cls.__fields__.items():
            if not isinstance(field, (Field, ResolverField)):
                raise ValidationError(f'{field} is an invalid field type')
            print_type(field.ftype, except_types=(InputType))
            if isinstance(field, ResolverField):
                for gtype in field.params.values():
                    print_type(gtype)
            if isinstance(field.ftype, ObjectType):
                field.ftype.validate()


class Object(metaclass=ObjectType):

    def __resolve__(self, root_node, nodes, error_collector, path=[]):
        self.resolver_results = {}
        for node in nodes:
            name = node.name.value
            path.append(name)

            self.__resolve_fragment__(root_node, node, error_collector, path)

            snake_cases = to_snake_case(name)
            field = self.__fields__.get(snake_cases)

            resolver = self.__get_resover__(name, node, field)
            if not resolver:
                continue

            kwargs = self.__package_args__(node, field)

            try:
                result = resolver(**kwargs)
            except Exception as e:
                e.location = node.loc.source.get_location(node.loc.start)
                e.path = path
                error_collector.append(e)
                result = None

            if not self.__check_return_type__(resolver, result):
                if result is None and error_collector:
                    return None
                raise RuntimeError(
                    f'{result} is not a valid return value to'
                    f' {resolver.__name__}',
                    node
                )

            if isinstance(result, Object):
                result.__resolve__(root_node, node.selection_set.selections, error_collector, path)
            self.resolver_results[snake_cases] = result

    def __resolve_fragment__(self, root_node, node, error_collector, path):
        if isinstance(node, InlineFragmentNode):
            if node.type_condition == self.__class__.__name__:
                self.__resolve__(
                    root_node,
                    node.selection_set.selections,
                    error_collector,
                    path
                )
        elif isinstance(node, FragmentSpreadNode):
            for subroot_node in root_node:
                if node.name.value == subroot_node.name.value:
                    path.append(subroot_node.name.value)
                    self.__resolve__(
                        root_node,
                        subroot_node.selection_set.selections,
                        error_collector,
                        path
                    )
                    break

    def __get_resover__(self, name, node, field):
        snake_cases = to_snake_case(name)
        if not field:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node
            )
        if not isinstance(field, ResolverField):
            return None
        resolver = getattr(self, snake_cases, None)
        if not resolver:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node
            )
        return resolver

    def __package_args__(self, node, field):
        kwargs = {}
        for arg in node.arguments:
            slot = field.params.get(arg.name.value)
            if not slot:
                raise RuntimeError(
                    f'Can not find {arg.value.name}'
                    f' as param in {field.name}',
                    node
                )
            kwargs[to_snake_case(arg.name.value)] = load_literal_value(
                arg, slot
            )
        return kwargs

    @staticmethod
    def __check_return_type__(resolver, result):
        return_type = inspect.signature(resolver).return_annotation
        if is_union(return_type) or is_list(return_type):
            for type_arg in return_type.__args__:
                if isinstance(result, type_arg):
                    return True
        elif isinstance(result, return_type):
            return True

        return False


class SchemaType(ObjectType):
    VALID_ROOT_TYPES = {'query', 'mutation'}

    def __new__(cls, name, bases, attrs):
        attrs['registered_type'] = []
        cls = super().__new__(cls, name, bases, attrs)
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
            elif isinstance(ptype, InterfaceType):
                cls.registered_type.append(ptype)
                cls.register_fields_type(ptype.__fields__.values())
                cls.register_types(ptype.__subclasses__())
            else:
                # Other basic types, do not need be handled
                pass

    def validate(cls):
        for name, field in cls.__fields__.items():
            if name not in cls.VALID_ROOT_TYPES:
                raise ValidationError(
                    f'The valid root type must be {cls.VALID_ROOT_TYPES},'
                    f' rather than {name}'
                )
            if not isinstance(field, Field):
                raise ValidationError(f'{field} is an invalid field type')
            if not is_optional(field.ftype):
                raise ValidationError(
                    f'The return type of root object should be Optional'
                )
            if not isinstance(field.ftype.__args__[0], ObjectType):
                raise ValidationError(
                    f'The typt of root object must be an Object, rather than {field.ftype}'
                )
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

    FIELD_MAP = {
        OperationType.QUERY: 'query',
        OperationType.MUTATION: 'mutation'
    }

    @classmethod
    def execute(cls, query):
        document = parse(query)
        for definition in document.definitions:
            if not isinstance(definition, OperationDefinitionNode):
                continue
            if definition.operation in (
                OperationType.QUERY,
                OperationType.MUTATION
            ):
                query_object = cls.__fields__[
                    cls.FIELD_MAP[definition.operation]
                ].ftype.__args__[0]()
                error_collector = []
                try:
                    query_object.__resolve__(
                        document.definitions,
                        definition.selection_set.selections,
                        error_collector
                    )
                except Exception as e:
                    error_collector.append(e)
                if error_collector:
                    return_root = {
                        'errors': error_collector,
                        'data': query_object
                    }
                else:
                    return_root = query_object
                return json.dumps(return_root, cls=GraphQLEncoder)


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
            raise RuntimeError(
                f'{node.value.value} is not a valid member of {type}',
                node
            )
    elif isinstance(node.value, ObjectValueNode):
        return ptype.__resolve__(node.value)
    raise RuntimeError(f'Can not convert {node.value.value}', node)


VALID_BASIC_TYPES = {
    str: 'String',
    int: 'Int',
    float: 'Float',
    bool: 'Boolean',
}


def print_type(gtype, nonnull=True, except_types=()):
    if isinstance(gtype, except_types):
        raise ValidationError(f'{gtype} is not a valid type')
    literal = None
    if is_union(gtype):
        if is_optional(gtype):
            return f'{print_type(gtype.__args__[0], nonnull=False, except_types=except_types)}'  # noqa
        else:
            raise ValidationError(
                f'Native Union type is not supported except Optional'
            )
    elif is_list(gtype):
        literal = f'[{print_type(gtype.__args__[0], except_types=except_types)}]'  # noqa
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
    elif isinstance(gtype, InterfaceType):
        literal = f'{gtype.__name__}'
    else:
        raise ValidationError(f'Can not convert type {gtype} to GraphQL type')

    if nonnull:
        literal += '!'
    return literal
