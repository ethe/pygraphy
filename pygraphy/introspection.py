import inspect
import json
from typing import List, Optional
from .types import (
    Enum,
    Object,
    field,
    Schema as BaseSchema,
    context,
    Interface,
    Union,
    Input,
    ResolverField
)
from .types.base import print_type
from .utils import (
    meta,
    is_optional,
    is_list,
    is_union,
    to_camel_case
)


@meta
class DirectiveLocation(Enum):
    QUERY = 0
    MUTATION = 1
    SUBSCRIPTION = 2
    FIELD = 3
    FRAGMENT_DEFINITION = 4
    FRAGMENT_SPREAD = 5
    INLINE_FRAGMENT = 6
    SCHEMA = 7
    SCALAR = 8
    OBJECT = 9
    FIELD_DEFINITION = 10
    ARGUMENT_DEFINITION = 11
    INTERFACE = 12
    UNION = 13
    ENUM = 14
    ENUM_VALUE = 15
    INPUT_OBJECT = 16
    INPUT_FIELD_DEFINITION = 17


@meta
class Directive(Object):
    name: str
    description: Optional[str]
    locations: List[DirectiveLocation]
    args: List['InputValue']


@meta
class TypeKind(Enum):
    SCALAR = 0
    OBJECT = 1
    INTERFACE = 2
    UNION = 3
    ENUM = 4
    INPUT_OBJECT = 5
    LIST = 6
    NON_NULL = 7


@meta
class EnumValue(Object):
    name: str
    description: Optional[str]
    is_deprecated: bool
    deprecation_reason: Optional[str]


@meta
class InputValue(Object):

    @field
    def name(self) -> str:
        return to_camel_case(self._name)

    @field
    def description(self) -> Optional[str]:
        """
        Not support yet
        """
        return None

    @field
    def type(self) -> 'Type':
        t = Type()
        t._type = self.param
        return t

    @field
    def default_value(self) -> Optional[str]:
        default = self._param.default
        return json.dumps(default) if default != inspect._empty else None


@meta
class Field(Object):

    @field
    def name(self) -> str:
        return to_camel_case(self._field.name)

    @field
    def description(self) -> Optional[str]:
        return self._field.description

    @field
    def args(self) -> List[InputValue]:
        if not isinstance(self._field, ResolverField):
            return []
        args = []
        for name, param in self._field.params.items():
            value = InputValue()
            value._name = name
            value.param = param
            value._param = self._field._params[name]
            args.append(value)
        return args

    @field
    def type(self) -> 'Type':
        t = Type()
        t._type = self._field.ftype
        return t

    @field
    def is_deprecated(self) -> bool:
        """
        Not support yet
        """
        return False

    @field
    def deprecation_reason(self) -> Optional[str]:
        """
        Not support yet
        """
        return None


@meta
class Type(Object):

    @field
    def name(self) -> Optional[str]:
        if not is_optional(self._type):
            return None
        else:
            if is_list(self.type):
                return None
            return print_type(self.type, nonnull=False)

    @field
    def kind(self) -> TypeKind:
        if not is_optional(self._type):
            return TypeKind.NON_NULL
        type = self._type.__args__[0]
        if is_list(self.type):
            return TypeKind.LIST
        if issubclass(type, (str, int, float, bool)):
            return TypeKind.SCALAR
        elif issubclass(type, Object):
            return TypeKind.OBJECT
        elif issubclass(type, Interface):
            return TypeKind.INTERFACE
        elif issubclass(type, Union):
            return TypeKind.UNION
        elif issubclass(type, Enum):
            return TypeKind.ENUM
        elif issubclass(type, Input):
            return TypeKind.INPUT_OBJECT

    @field
    def description(self) -> Optional[str]:
        return self.type.__description__ if hasattr(self.type, '__description__') else self.type.__doc__

    @field
    def interfaces(self) -> Optional[List['Type']]:
        """
        OBJECT only
        """
        if not is_optional(self._type) and is_list(self._type):
            return None
        if issubclass(self.type, Object):
            interfaces = []
            for base in self.type.__bases__:
                if issubclass(base, Interface):
                    t = Type()
                    t._type = Optional[base]
                    interfaces.append(t)
            return interfaces
        return None

    @field
    def possible_types(self) -> Optional[List['Type']]:
        """
        INTERFACE and UNION only
        """
        if not is_optional(self._type) and is_list(self._type):
            return None
        if issubclass(self.type, Interface):
            types = []
            for subclass in self.type.__subclasses__():
                t = Type()
                t._type = subclass
                types.append(t)
            return types
        if issubclass(self.type, Union):
            types = []
            for member in list(self.type.members):
                t = Type()
                t._type = subclass
                types.append(t)
            return types
        return None

    @field
    def input_fields(self) -> Optional[List[InputValue]]:
        """
        INPUT_OBJECT only
        """
        if not is_optional(self._type) and is_list(self._type):
            return None
        if issubclass(self.type, Input):
            values = []
            for tfield in self.type.__fields__:
                values.append(InputValue(
                    name=tfield.name,
                    description=tfield.description,
                    default_value=None
                ))
            return values
        return None

    @field
    def of_type(self) -> Optional['Type']:
        """
        NON_NULL and LIST only
        """
        if not is_optional(self._type):
            of = Type()
            of._type = Optional[self._type]
            return of

        if is_list(self._type.__args__[0]):
            of = Type()
            of._type = self._type.__args__[0].__args__[0]
            return of
        return None

    @field
    def enum_values(self, include_deprecated: Optional[bool] = False) -> Optional[List[EnumValue]]:
        """
        ENUM only
        """
        if not is_optional(self._type) and is_list(self._type):
            return None
        if issubclass(self.type, Enum):
            values = []
            for attr in dir(self.type):
                if attr.startswith('_'):
                    continue
                values.append(attr)
            return [EnumValue(
                name=i,
                description=None,
                is_deprecated=False,
                deprecation_reason=None
            ) for i in values]

    @field
    def fields(self, include_deprecated: Optional[bool] = False) -> Optional[List[Field]]:
        """
        OBJECT and INTERFACE only
        """
        if not is_optional(self._type) and is_list(self._type):
            return None
        if issubclass(self.type, Object) or issubclass(self.type, Interface):
            fields = []
            for n, f in self.type.__fields__.items():
                field = Field()
                field._field = f
                fields.append(field)
            return fields
        return None

    @property
    def type(self):
        if is_union(self._type):
            return self._type.__args__[0]
        else:
            return self._type


@meta
class Schema(Object):

    @field
    def directives(self) -> List[Directive]:
        return []

    @field
    def query_type(self) -> Type:
        """
        The type that query operations will be rooted at.
        """
        schema = context.get().schema
        type = Type()
        type._type = schema.__fields__['query'].ftype
        return type

    @field
    def mutation_type(self) -> Optional[Type]:
        """
        If this server supports mutation, the type that mutation operations will be rooted at.
        """
        schema = context.get().schema
        if 'mutation' not in schema.__fields__:
            return None
        type = Type()
        type._type = schema.__fields__['mutation'].ftype
        return type

    @field
    def subscription_type(self) -> Optional[Type]:
        """
        Not support yet
        """
        return None

    @field
    def types(self) -> List[Type]:
        types = []
        for t in context.get().schema.registered_type:
            type = Type()
            type._type = Optional[t]
            types.append(type)
        return types


class Query(Object):

    @field
    def __type(self, name: str) -> Optional[Type]:
        return None

    @field
    def __schema(self) -> Schema:
        return Schema()


class WithMetaSchema(BaseSchema):
    query: Optional[Query]
