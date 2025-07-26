from typing import Any, TypeVar
import contextvars

__all__ = ['mylang_is_exposed', 'mylang_expose', 'exposed_objects']


T = TypeVar('T')


exposed_objects: set[int]  # Contains the IDs of objects that are exposed in mylang


def mylang_is_exposed(obj: Any):
    return id(obj) in exposed_objects


def mylang_expose(obj: T) -> T:
    """Marks something as exposed in mylang. Can be used as a decorator or simply called."""
    exposed_objects.add(id(obj))
    return obj  # For when used as a decorator


current_context = contextvars.ContextVar('context')

def get_current_context():
    return current_context.get()
