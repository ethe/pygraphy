import json
from .utils import to_camel_case
from pygraphql import types


class GraphQLEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, types.Object):
            attrs = {}
            for field in obj.__fields__.values():
                camel_cases = to_camel_case(field.name)
                if isinstance(field, types.ResolverField):
                    if field.name in obj.resolver_results:
                        attrs[camel_cases] = obj.resolver_results[field.name]
                elif isinstance(field, types.Field):
                    if hasattr(obj, field.name):
                        attrs[camel_cases] = getattr(obj, field.name)
            return attrs
        elif issubclass(type(obj), types.Enum):
            return str(obj).split('.')[-1]
        elif isinstance(obj, Exception):
            return {
                'message': str(obj),
                'locations': [{'line': obj.location[0], 'column': obj.location[1]}],
                'path': obj.path
            }
        return super().default(obj)
