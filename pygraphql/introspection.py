from .types import Enum, Object, field, Schema as BaseSchema
from typing import List, Optional
from .utils import meta


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
    kind: TypeKind
    name: Optional[str]
    description: Optional[str]

    # OBJECT only
    interfaces: Optional[List['Type']]
    # INTERFACE and UNION only
    possible_types: Optional[List['Type']]
    # INPUT_OBJECT only
    input_fields: Optional[List[InputValue]]
    # NON_NULL and LIST only
    of_type: Optional['Type']

    # ENUM only
    @field
    def enum_values(self, include_deprecated: Optional[bool] = False) -> Optional[List[EnumValue]]:
        pass

    # OBJECT and INTERFACE only
    @field
    def fields(self, include_deprecated: Optional[bool] = False) -> Optional[List[Field]]:
        pass


@meta
class Schema(Object):
    types: List[Type]
    mutation_type: Optional[Type]
    subscription_type: Type

    @field
    def directives(self) -> List[Directive]:
        return []

    @field
    def query_type(self) -> Type:
        return []


class Query(Object):

    @field
    def __type(self, name: str) -> Optional[Type]:
        return None

    @field
    def __schema(self) -> Schema:
        pass


class WithMetaSchema(BaseSchema):
    query: Optional[Query]
