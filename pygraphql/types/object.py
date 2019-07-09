import inspect
from copy import copy
from graphql.language.ast import (
    FragmentSpreadNode,
    InlineFragmentNode
)
from pygraphql.utils import (
    patch_indents,
    to_snake_case,
    is_union,
    is_list,
    is_optional,
    shelling_type
)
from pygraphql.exceptions import RuntimeError, ValidationError
from pygraphql import types
from .interface import InterfaceType
from .field import Field, ResolverField
from .base import print_type, load_literal_value


class ObjectType(InterfaceType):

    def __str__(cls):
        return (
            f'{cls.print_description()}'
            + f'type {cls.__name__}{cls.print_interface_implement()} '
            + '{\n'
            + f'{patch_indents(cls.print_field(), indent=1)}'
            + '\n}'
        )

    def print_interface_implement(cls):
        literal = ''
        for base in cls.__bases__:
            if isinstance(base, ObjectType):
                continue
            if not literal:
                literal = f' implements {base.__name__}'
            else:
                literal += f' & {base.__name__}'
        return literal

    def validate(cls):
        if cls.__validated__:
            return
        cls.__validated__ = True
        for _, field in cls.__fields__.items():
            if not isinstance(field, (Field, ResolverField)):
                raise ValidationError(f'{field} is an invalid field type')
            print_type(field.ftype, except_types=(types.InputType))
            if isinstance(field, ResolverField):
                for gtype in field.params.values():
                    print_type(gtype)
            if isinstance(field.ftype, ObjectType):
                field.ftype.validate()
            if is_union(field.ftype):
                shelled = shelling_type(field.ftype)
                if isinstance(shelled, ObjectType):
                    shelled.validate()


class Object(metaclass=ObjectType):

    def __resolve__(self, root_node, nodes, error_collector, path=[]):
        self.resolve_results = {}
        for node in nodes:
            if hasattr(node, 'name'):
                path = copy(path)
                path.append(node.name.value)

            returned = self.__resolve_fragment__(root_node, node, error_collector, path)
            if returned:
                continue

            name = node.name.value
            snake_cases = to_snake_case(name)
            field = self.__fields__.get(snake_cases)

            resolver = self.__get_resover__(name, node, field, path)
            if not resolver:
                self.resolve_results[name] = getattr(self, snake_cases)
                continue

            kwargs = self.__package_args__(node, field, path)

            try:
                result = resolver(**kwargs)
            except Exception as e:
                # TODO: Use logger to print stack
                import traceback
                traceback.print_exc()
                e.location = node.loc.source.get_location(node.loc.start)
                e.path = path
                error_collector.append(e)
                result = None

            return_type = inspect.signature(resolver).return_annotation
            if not self.__check_return_type__(return_type, result):
                if result is None and error_collector:
                    return None
                raise RuntimeError(
                    f'{result} is not a valid return value to'
                    f' {resolver.__name__}, please check {resolver.__name__}\'s type annotation',
                    node,
                    path
                )

            if isinstance(result, Object):
                result.__resolve__(root_node, node.selection_set.selections, error_collector, path)
            elif hasattr(result, 'iter') and isinstance(return_type.__args__[0], ObjectType):
                for item in result:
                    item.__resolve__(root_node, node.selection_set.selections, error_collector, path)
            self.resolve_results[name] = result
        return self

    def __resolve_fragment__(self, root_node, node, error_collector, path):
        if isinstance(node, InlineFragmentNode):
            if node.type_condition.name.value == self.__class__.__name__:
                self.__resolve__(
                    root_node,
                    node.selection_set.selections,
                    error_collector
                )
            return True
        elif isinstance(node, FragmentSpreadNode):
            for subroot_node in root_node:
                if node.name.value == subroot_node.name.value:
                    current_path = copy(path)
                    current_path.append(subroot_node.name.value)
                    self.__resolve__(
                        root_node,
                        subroot_node.selection_set.selections,
                        error_collector,
                        current_path
                    )
            return True
        return False

    def __get_resover__(self, name, node, field, path):
        snake_cases = to_snake_case(name)
        if not field:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node,
                path
            )
        if not isinstance(field, ResolverField):
            return None
        if '__' in snake_cases:
            resolver = getattr(self, f'_{self.__class__.__name__}{snake_cases}', None)
        else:
            resolver = getattr(self, snake_cases, None)
        if not resolver:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node,
                path
            )
        return resolver

    def __package_args__(self, node, field, path):
        kwargs = {}
        for arg in node.arguments:
            slot = field.params.get(arg.name.value)
            if not slot:
                raise RuntimeError(
                    f'Can not find {arg.value.name}'
                    f' as param in {field.name}',
                    node,
                    path
                )
            kwargs[to_snake_case(arg.name.value)] = load_literal_value(
                arg, slot
            )
        return kwargs

    @classmethod
    def __check_return_type__(cls, return_type, result):
        if is_optional(return_type):
            if result is None:
                return True
            return cls.__check_return_type__(return_type.__args__[0], result)
        elif is_list(return_type):
            return cls.__check_return_type__(return_type.__args__[0], result)
        elif isinstance(return_type, types.UnionType):
            for member in return_type.members:
                if isinstance(result, member):
                    return True
        elif isinstance(result, return_type):
            return True

        return False
