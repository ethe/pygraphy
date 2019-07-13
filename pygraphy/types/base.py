from graphql.language import parse_value
from graphql.language.ast import (
    IntValueNode,
    FloatValueNode,
    BooleanValueNode,
    StringValueNode,
    NullValueNode,
    EnumValueNode,
    ListValueNode,
    ObjectValueNode,
    VariableNode,
)
from pygraphy.utils import (
    patch_indents,
    is_union,
    is_optional,
    is_list
)
from pygraphy.exceptions import ValidationError
from pygraphy import types


class GraphQLType(type):

    def print_description(cls, indent=0):
        return patch_indents(
            f'"""\n{cls.__description__}\n"""\n' if cls.__description__ else '',  # noqa
            indent=indent
        )


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
    elif isinstance(gtype, types.ObjectType):
        literal = f'{gtype.__name__}'
    elif gtype in VALID_BASIC_TYPES:
        literal = VALID_BASIC_TYPES[gtype]
    elif gtype is None or gtype == type(None):  # noqa
        return 'null'
    elif isinstance(gtype, types.UnionType):
        literal = f'{gtype.__name__}'
    elif isinstance(gtype, types.EnumType):
        literal = f'{gtype.__name__}'
    elif isinstance(gtype, types.InputType):
        literal = f'{gtype.__name__}'
    elif isinstance(gtype, types.InterfaceType):
        literal = f'{gtype.__name__}'
    else:
        raise ValidationError(f'Can not convert type {gtype} to GraphQL type')

    if nonnull:
        literal += '!'
    return literal


def load_literal_value(node, ptype):
    if isinstance(node, IntValueNode):
        return int(node.value)
    elif isinstance(node, FloatValueNode):
        return float(node.value)
    elif isinstance(node, BooleanValueNode):
        return bool(node.value)
    elif isinstance(node, StringValueNode):
        return node.value
    elif isinstance(node, NullValueNode):
        return None
    elif isinstance(node, ListValueNode):
        return [load_literal_value(v.value) for v in node.values]
    elif isinstance(node, EnumValueNode):
        value = getattr(ptype, node.value)
        if not value:
            raise RuntimeError(
                f'{node.value} is not a valid member of {type}',
                node
            )
        return value
    elif isinstance(node, ObjectValueNode):
        return ptype.__resolve__(node)
    elif isinstance(node, VariableNode):
        name = node.name.value
        variables = types.context.get().variables
        if name not in variables:
            raise RuntimeError(f'Can not find variable {name}')
        node = parse_value(variables[name])
        return load_literal_value(node, ptype)
    raise RuntimeError(f'Can not convert {node.value}', node)
