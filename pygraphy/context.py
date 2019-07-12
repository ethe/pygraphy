import typing
import dataclasses
from typing import Any, Optional


if typing.TYPE_CHECKING:
    from .types import Schema


@dataclasses.dataclass
class Context:
    schema: 'Schema'
    request: Optional[Any] = None
