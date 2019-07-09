from typing import List, Optional
from .types import (
    Enum,
    Object,
    field,
    Schema as BaseSchema,
    context,
    Interface,
    Union,
    Enum,
    Input
)
from .types.base import print_type
from .utils import meta, is_optional, is_list, is_union


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
    name: str
    description: Optional[str]
    type: 'Type'
    default_value: Optional[str]

    @field
    def type(self) -> 'Type':
        pass


@meta
class Field(Object):
    name: str
    description: Optional[str]
    args: List[InputValue]
    type: 'Type'
    is_deprecated: bool
    deprecation_reason: str


@meta
class Type(Object):

    @field
    def name(self) -> Optional[str]:
        return print_type(self._type, nonnull=False)

    @field
    def kind(self) -> TypeKind:
        if not is_optional(self._type):
            return TypeKind.NON_NULL
        if is_list(self._type):
            return TypeKind.LIST
        type = self._type.__args__[0]
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
        return self.type.__description__

    @field
    def interfaces(self) -> Optional[List['Type']]:
        """
        OBJECT only
        """
        if not is_optional(self._type) and is_list(self._type):
            return None
        if issubclass(self.type, Object):
            interfaces = []
            for base in self.type.bases:
                if issubclass(base, Interface):
                    interfaces.append(base)
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
            return self.type.__subclasses__()
        if issubclass(self.type, Union):
            return list(self.type.members)
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
            for field in self.type.__fields__:
                values.append(InputValue(
                    name=field.name,
                    description=field.description,
                    default_value=None
                ))
        return None

    @field
    def of_type(self) -> Optional['Type']:
        """
        NON_NULL and LIST only
        """
        if not is_optional(self._type):
            of = Type()
            of._type = self._type
            return of
        elif is_list(self._type):
            of = Type()
            of._type = self._type.__args__[0]
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
            for attr in dir()

    @field
    def fields(self, include_deprecated: Optional[bool] = False) -> Optional[List[Field]]:
        """
        OBJECT and INTERFACE only
        """
        pass

    @property
    def type(self):
        if is_union(self._type):
            return self._type.__args__[0]
        else:
            return self._type


@meta
class Schema(Object):
    types: List[Type]
    mutation_type: Optional[Type]
    subscription_type: Optional[Type]

    @field
    def directives(self) -> List[Directive]:
        return []

    @field
    def query_type(self) -> Type:
        schema = context.get().schema
        type = Type()
        type._type = schema.__fields__['query'].ftype
        return type


class Query(Object):

    @field
    def __type(self, name: str) -> Optional[Type]:
        return None

    @field
    def __schema(self) -> Schema:
        return Schema(types=[], mutation_type=[], subscription_type=None)


class WithMetaSchema(BaseSchema):
    query: Optional[Query]
