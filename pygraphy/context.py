import typing
import dataclasses


if typing.TYPE_CHECKING:
    from .types import Schema


@dataclasses.dataclass
class Context:
    schema: 'Schema'
