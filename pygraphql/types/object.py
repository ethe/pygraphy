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
    is_list
)
from pygraphql.exceptions import RuntimeError, ValidationError
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
            from .input import InputType
            print_type(field.ftype, except_types=(InputType))
            if isinstance(field, ResolverField):
                for gtype in field.params.values():
                    print_type(gtype)
            if isinstance(field.ftype, ObjectType):
                field.ftype.validate()


class Object(metaclass=ObjectType):

    def __resolve__(self, root_node, nodes, error_collector, path=[]):
        self.resolver_results = {}
        for node in nodes:
            name = node.name.value
            current_path = copy(path)
            current_path.append(name)

            self.__resolve_fragment__(root_node, node, error_collector, current_path)

            snake_cases = to_snake_case(name)
            field = self.__fields__.get(snake_cases)

            resolver = self.__get_resover__(name, node, field)
            if not resolver:
                continue

            kwargs = self.__package_args__(node, field)

            try:
                result = resolver(**kwargs)
            except Exception as e:
                e.location = node.loc.source.get_location(node.loc.start)
                e.path = current_path
                error_collector.append(e)
                result = None

            return_type = inspect.signature(resolver).return_annotation
            if not self.__check_return_type__(return_type, result):
                if result is None and error_collector:
                    return None
                raise RuntimeError(
                    f'{result} is not a valid return value to'
                    f' {resolver.__name__}',
                    node
                )

            if isinstance(result, Object):
                result.__resolve__(root_node, node.selection_set.selections, error_collector, path)
            self.resolver_results[snake_cases] = result
        return self

    def __resolve_fragment__(self, root_node, node, error_collector, path):
        if isinstance(node, InlineFragmentNode):
            if node.type_condition == self.__class__.__name__:
                self.__resolve__(
                    root_node,
                    node.selection_set.selections,
                    error_collector,
                    path
                )
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
                    break

    def __get_resover__(self, name, node, field):
        snake_cases = to_snake_case(name)
        if not field:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node
            )
        if not isinstance(field, ResolverField):
            return None
        resolver = getattr(self, snake_cases, None)
        if not resolver:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node
            )
        return resolver

    def __package_args__(self, node, field):
        kwargs = {}
        for arg in node.arguments:
            slot = field.params.get(arg.name.value)
            if not slot:
                raise RuntimeError(
                    f'Can not find {arg.value.name}'
                    f' as param in {field.name}',
                    node
                )
            kwargs[to_snake_case(arg.name.value)] = load_literal_value(
                arg, slot
            )
        return kwargs

    @classmethod
    def __check_return_type__(cls, return_type, result):
        if is_union(return_type) or is_list(return_type):
            for type_arg in return_type.__args__:
                return cls.__check_return_type__(type_arg, result)
        elif isinstance(result, return_type):
            return True

        return False
