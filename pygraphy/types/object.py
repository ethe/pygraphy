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
from pygraphy import types
from pygraphy.exceptions import RuntimeError, ValidationError
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
                    shelled = shelling_type(gtype)
                    if isinstance(shelled, types.InputType):
                        shelled.validate()
            if isinstance(field.ftype, ObjectType):
                field.ftype.validate()
            if is_union(field.ftype):
                shelled = shelling_type(field.ftype)
                if isinstance(shelled, ObjectType):
                    shelled.validate()


class Object(metaclass=ObjectType):

    def __iter__(self):
        for name, value in self.resolve_results.items():
            if isinstance(value, Object):
                value = dict(value)
            elif isinstance(value, list):
                serialized_value = []
                for i in value:
                    if isinstance(i, Object):
                        serialized_value.append(dict(i))
                    else:
                        serialized_value.append(i)
                value = serialized_value
            yield (name, value)

    async def _resolve(self, nodes, error_collector, path=[]):
        self.resolve_results = {}
        tasks = {}
        for node in nodes:
            if hasattr(node, 'name'):
                path = copy(path)
                path.append(node.name.value)

            returned = await self.__resolve_fragment(
                node, error_collector, path
            )
            if returned:
                continue

            name = node.name.value
            snake_cases = to_snake_case(name)
            field = self.__fields__.get(snake_cases)

            resolver = self.__get_resover(name, node, field, path)
            if not resolver:
                try:
                    tasks[name] = (getattr(self, snake_cases), node, field, path)
                except AttributeError:
                    raise RuntimeError(
                        f'{name} is not a valid node of {self}', node, path
                    )
            else:
                kwargs = self.__package_args(node, field, path)

                try:
                    returned = resolver(**kwargs)
                except Exception as e:
                    self.__handle_error(e, node, path, error_collector)
                    tasks[name] = (None, node, field, path)
                    continue

                if isawaitable(returned):
                    tasks[name] = (asyncio.ensure_future(returned), node, field, path)
                else:
                    tasks[name] = (returned, node, field, path)

        return self.__task_receiver(tasks, error_collector)

    @staticmethod
    def __get_field_name(name, node):
        if node.alias:
            return node.alias.value
        return name

    async def __task_receiver(self, tasks, error_collector):
        generators = []
        for name, task in tasks.items():
            task, node, field, path = task
            if hasattr(task, '__aiter__'):
                generators.append(task)
            else:
                if isawaitable(task):
                    try:
                        result = await task
                    except Exception as e:
                        self.__handle_error__(e, node, path, error_collector)
                        result = None
                else:
                    result = task
                self.resolve_results[self.__get_field_name(name, node)] = result

        for generator in generators:
            async for result in generator:
                self.resolve_results[self.__get_field_name(name, node)] = result
                yield await self.__check_and_circular_resolve(tasks, error_collector)

        if not generators:
            yield await self.__check_and_circular_resolve(tasks, error_collector)

    async def __check_and_circular_resolve(self, tasks, error_collector):
        for name, task in tasks.items():
            task, node, field, path = task
            result = self.resolve_results[self.__get_field_name(name, node)]
            if not self.__check_return_type(field.ftype, result):
                if result is None and error_collector:
                    return False
                raise RuntimeError(
                    f'{result} is not a valid return value to'
                    f' {name}, please check {name}\'s type annotation',
                    node,
                    path
                )
            await self.__circular_resolve(
                result, node, error_collector, path
            )
        return self

    @staticmethod
    def __handle_error(e, node, path, error_collector):
        logging.error(e, exc_info=True)
        e.location = node.loc.source.get_location(node.loc.start)
        e.path = path
        error_collector.append(e)

    async def __circular_resolve(self, result, node, error_collector, path):
        if isinstance(result, Object):
            async for obj in await result._resolve(
                node.selection_set.selections, error_collector, path
            ):
                pass
        elif hasattr(result, '__iter__'):
            for item in result:
                if isinstance(item, Object):
                    async for _ in await item._resolve(
                        node.selection_set.selections,
                        error_collector,
                        path
                    ):
                        pass

    async def __resolve_fragment(self, node, error_collector, path):
        if isinstance(node, InlineFragmentNode):
            if node.type_condition.name.value == self.__class__.__name__:
                async for _ in await self._resolve(
                    node.selection_set.selections,
                    error_collector
                ):
                    pass
            return True
        elif isinstance(node, FragmentSpreadNode):
            root_node = types.context.get().root_ast
            for subroot_node in root_node:
                if node.name.value == subroot_node.name.value:
                    current_path = copy(path)
                    current_path.append(subroot_node.name.value)
                    async for _ in await self._resolve(
                        subroot_node.selection_set.selections,
                        error_collector,
                        current_path
                    ):
                        pass
            return True
        return False

    def __get_resover(self, name, node, field, path):
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

    def __package_args(self, node, field, path):
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
    def __check_return_type(cls, return_type, result):
        if is_optional(return_type):
            if result is None:
                return True
            return cls.__check_return_type(return_type.__args__[0], result)
        elif is_list(return_type):
            if not isinstance(result, list):
                return False
            if len(result) == 0:
                return True
            for item in result:
                if not cls.__check_return_type(return_type.__args__[0], item):
                    return False
                return True
        elif isinstance(return_type, types.UnionType):
            for member in return_type.members:
                if cls.__check_return_type(member, result):
                    return True
        elif isinstance(result, return_type):
            return True

        return False
