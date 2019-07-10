import json
from pygraphy import types


class GraphQLEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, types.Object):
            return obj.resolve_results
        elif issubclass(type(obj), types.Enum):
            return str(obj).split('.')[-1]
        elif isinstance(obj, Exception):
            return {
                'message': str(obj),
                'locations': [{'line': obj.location[0], 'column': obj.location[1]}] if hasattr(obj, 'location') else None,
                'path': obj.path if hasattr(obj, 'path') else None
            }
        return super().default(obj)
