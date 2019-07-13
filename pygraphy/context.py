import typing
import dataclasses
from typing import Any, Optional, Mapping, List
from graphql.language.ast import OperationDefinitionNode


if typing.TYPE_CHECKING:
    from .types import Schema


@dataclasses.dataclass
class Context:
    schema: 'Schema'
    root_ast: List[OperationDefinitionNode]
    request: Optional[Any] = None
    variables: Optional[Mapping[str, Any]] = None
