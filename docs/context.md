Pygraphy uses [Context Variables](https://docs.python.org/3/library/contextvars.html#module-contextvars) to manage the context of a query, which has been included in Python 3.7 and later. With context variables, you do not need to pass a context everywhere any more like graphql-core.
```python
from pygraphy import context, Object, field


class Schema(Object):

    @field
    def query_type(self):
        """
        The type that query operations will be rooted at.
        """
        schema = context.get().schema
        query_type = schema.__fields__['query'].ftype
        # Do whatever you want
```

The definition of context is posted blow:
```python
@dataclasses.dataclass
class Context:
    schema: 'Schema'
    root_ast: List[OperationDefinitionNode]
    request: Optional[Any] = None
    variables: Optional[Mapping[str, Any]] = None
```

Attributes:

- schema: The Schema class which is processing now.
- root_ast: The ast tree parsed from query string.
- request: Request instance, passed into context from the argument of `Schema.execute`.
- variables: Query variables.
