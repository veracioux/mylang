"""Utilities for exposing Python objects and attributes to MyLang."""

from typing import Any, TypeVar

T = TypeVar("T")

_exposed_objects = set[int]()
"""Holds all objects that are exposed outside of Python, in the context of MyLang."""


_exposed_class_attrs = set[tuple[type, str]]()
"""Holds all (class, attr_name) pairs that are exposed to MyLang."""


_exposed_instance_attrs = set[tuple[type, str]]()
"""Holds (class, attr_name) pairs. Each pair means that the attribute named
`attr_name` should be exposed to MyLang for instances of `class` and its subclasses."""


_exposed_obj_attrs = set[tuple[Any, str]]()
"""Holds (obj, attr_name) pairs. Each pair means that the attribute named
`attr_name` on object `obj` should be exposed to MyLang."""


def expose(obj: Any):
    """Expose the object outside of Python under all circumstances."""
    _exposed_objects.add(id(obj))
    # TODO: Make sure that callables are decorated by only_callable_by_call_decorator
    # (need to determine how to recognize something as a callable)
    return obj


def expose_class_attr(*attr_names: str):
    """Decorator to expose a class attribute in the context of MyLang."""

    def decorator(cls: T) -> T:
        for attr_name in attr_names:
            _exposed_class_attrs.add((cls, attr_name))
        return cls

    return decorator


def expose_instance_attr(*attr_names: str):
    """Decorator to expose attributes on all instances of class `cls` in the context of MyLang."""

    def decorator(cls: T) -> T:
        for attr_name in attr_names:
            _exposed_instance_attrs.add((cls, attr_name))
        return cls

    return decorator


def expose_obj_attr(obj: T, *attr_names: str) -> T:
    """Expose an attribute on an object in the context of MyLang."""
    for attr_name in attr_names:
        _exposed_obj_attrs.add((obj, attr_name))

    return obj


def is_exposed(obj: Any):
    """Check if the object is exposed outside of Python."""
    return id(obj) in _exposed_objects


def is_attr_exposed(obj: Any, attr_name: str):
    """Check if the given attribute on obj is exposed outside of Python."""
    if (obj, attr_name) in _exposed_obj_attrs or (
        type(obj),
        attr_name,
    ) in _exposed_instance_attrs:
        return True

    type_ = obj if isinstance(obj, type) else type(obj)

    for type_ in type_.mro()[:-1]:  # exclude `object`
        if (type_, attr_name) in _exposed_class_attrs:
            return True

    return False
