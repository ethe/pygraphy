import asyncio
import logging
from inspect import isawaitable
from copy import copy
from graphql.language.ast import (
    FragmentSpreadNode,
    InlineFragmentNode
)
from pygraphy.utils import (
    patch_indents,
    to_snake_case,
    is_union,
    is_list,
    is_optional,
    shelling_type
)
from pygraphy.exceptions import RuntimeError, ValidationError
from pygraphy import types
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

    async def __resolve__(self, nodes, error_collector, path=[]):
        self.resolve_results = {}
        tasks = {}
        for node in nodes:
            if hasattr(node, 'name'):
                path = copy(path)
                path.append(node.name.value)

            returned = await self.__resolve_fragment__(
                node, error_collector, path
            )
            if returned:
                continue

            name = node.name.value
            snake_cases = to_snake_case(name)
            field = self.__fields__.get(snake_cases)

            resolver = self.__get_resover__(name, node, field, path)
            if not resolver:
                try:
                    tasks[name] = (getattr(self, snake_cases), node, field, path)
                except AttributeError:
                    raise RuntimeError(
                        f'{name} is not a valid node of {self}', node, path
                    )
            else:
                kwargs = self.__package_args__(node, field, path)

                try:
                    returned = resolver(**kwargs)
                except Exception as e:
                    self.__handle_error__(e, node, path, error_collector)
                    tasks[name] = (None, node, field, path)
                    continue

                if isawaitable(returned):
                    tasks[name] = (asyncio.ensure_future(returned), node, field, path)
                else:
                    tasks[name] = (returned, node, field, path)

        return await self.__task_receiver__(tasks, error_collector)

    async def __task_receiver__(self, tasks, error_collector):
        for name, task in tasks.items():
            task, node, field, path = task
            if isawaitable(task):
                try:
                    result = await task
                except Exception as e:
                    self.__handle_error__(e, node, path, error_collector)
                    result = None
            else:
                result = task

            if not self.__check_return_type__(field.ftype, result):
                if result is None and error_collector:
                    return None
                raise RuntimeError(
                    f'{result} is not a valid return value to'
                    f' {name}, please check {name}\'s type annotation',
                    node,
                    path
                )

            await self.__circular_resolve__(
                result, node, error_collector, path
            )

            self.resolve_results[name] = result
        return self

    @staticmethod
    def __handle_error__(e, node, path, error_collector):
        logging.error(e, exc_info=True)
        e.location = node.loc.source.get_location(node.loc.start)
        e.path = path
        error_collector.append(e)

    async def __circular_resolve__(self, result, node, error_collector, path):
        if isinstance(result, Object):
            await result.__resolve__(
                node.selection_set.selections, error_collector, path
            )
        elif hasattr(result, '__iter__'):
            for item in result:
                if isinstance(item, Object):
                    await item.__resolve__(
                        node.selection_set.selections,
                        error_collector,
                        path
                    )

    async def __resolve_fragment__(self, node, error_collector, path):
        if isinstance(node, InlineFragmentNode):
            if node.type_condition.name.value == self.__class__.__name__:
                await self.__resolve__(
                    node.selection_set.selections,
                    error_collector
                )
            return True
        elif isinstance(node, FragmentSpreadNode):
            root_node = types.context.get().root_ast
            for subroot_node in root_node:
                if node.name.value == subroot_node.name.value:
                    current_path = copy(path)
                    current_path.append(subroot_node.name.value)
                    await self.__resolve__(
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
            resolver = getattr(
                self, f'_{self.__class__.__name__}{snake_cases}', None
            )
        else:
            resolver = getattr(self, snake_cases, None)
        if not resolver or not resolver.__is_field__:
            raise RuntimeError(
                f"Cannot query field '{name}' on type '{type(self)}'.",
                node,
                path
            )
        return resolver

    def __package_args__(self, node, field, path):
        kwargs = {}
        for arg in node.arguments:
            slot = field.params.get(to_snake_case(arg.name.value))
            if not slot:
                raise RuntimeError(
                    f'Can not find {arg.name.value}'
                    f' as param in {field.name}',
                    node,
                    path
                )
            kwargs[to_snake_case(arg.name.value)] = load_literal_value(
                arg.value, slot
            )
        return kwargs

    @classmethod
    def __check_return_type__(cls, return_type, result):
        if is_optional(return_type):
            if result is None:
                return True
            return cls.__check_return_type__(return_type.__args__[0], result)
        elif is_list(return_type):
            if len(result) == 0:
                return True
            for item in result:
                if not cls.__check_return_type__(return_type.__args__[0], item):
                    return False
                return True
        elif isinstance(return_type, types.UnionType):
            for member in return_type.members:
                if cls.__check_return_type__(member, result):
                    return True
        elif isinstance(result, return_type):
            return True

        return False
