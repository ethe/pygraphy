import re
import typing


def patch_indents(string, indent=0):
    spaces = '  ' * indent
    return spaces + string.replace('\n', '\n' + spaces)


def is_union(annotation):
    """Returns True if annotation is a typing.Union"""

    annotation_origin = getattr(annotation, "__origin__", None)

    return annotation_origin == typing.Union


def is_optional(annotation):
    annotation_origin = getattr(annotation, "__origin__", None)
    return annotation_origin == typing.Union \
        and len(annotation.__args__) == 2 \
        and annotation.__args__[1] == type(None)  # noqa


def is_list(annotation):
    return getattr(annotation, "__origin__", None) == list


def to_camel_case(snake_str):
    components = snake_str.split("_")
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])  # noqa


def to_snake_case(name):
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
