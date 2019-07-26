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


def to_camel_case(name):
    has_prefix = False
    if '__' in name:
        has_prefix = True
        without_prifix_name = ''.join(name.split('__')[1:])
    else:
        without_prifix_name = name
    components = without_prifix_name.split("_")
    res = components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])  # noqa
    return '__' + res if has_prefix else res


seprate_upper_case = re.compile("(.)([A-Z][a-z]+)")
seprate_upper_case_behind_lower_case = re.compile("([a-z0-9])([A-Z])")


def to_snake_case(name):
    has_prefix = False
    if '__' in name:
        has_prefix = True
        without_prifix_name = ''.join(name.split('__')[1:])
    else:
        without_prifix_name = name
    s1 = seprate_upper_case.sub(r"\1_\2", without_prifix_name)
    res = seprate_upper_case_behind_lower_case.sub(r"\1_\2", s1).lower()
    return '__' + res if has_prefix else res


def meta(obj):
    obj.__name__ = '__' + obj.__name__
    return obj


def shelling_type(type):
    while is_optional(type) or is_list(type):
        type = type.__args__[0]
    return type
