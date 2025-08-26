from ._utils import python_obj_to_mylang
from .base import Object, Args
from .primitive import Bool


__all__ = ("operators",)


# TODO: Object should be function type instead
# NOTE: The items are populated below
operators: dict[str, Object] = {}


def _op(name: str, *, convert_func_to_mylang=True):
    def decorator(func) -> staticmethod:
        f = python_obj_to_mylang(func) if convert_func_to_mylang else func
        f.__name__ = func.__name__
        operators[name] = f
        return func

    return decorator


@_op("==")
def equals(a, b):
    return Bool(a == b)


@_op("-")
def subtract(a, b):
    return a - b


@_op("+")
def add(a, b):
    return a + b


@_op("*")
def multiply(a, b):
    return a * b

# TODO: Add missing tests

@_op(">")
def gt(a, b):
    return a > b


@_op(">=")
def ge(a, b):
    return a >= b


@_op("<")
def lt(a, b):
    return a < b


@_op("<=")
def le(a, b):
    return a <= b


@_op("$", convert_func_to_mylang=False)
def dollar(a):
    from .func import call, ref, get

    return call._m_classcall_(Args(ref.of(get), a))


@_op("&", convert_func_to_mylang=False)
def ampersand(a):
    from .func import call, ref

    return call._m_classcall_(Args(ref.of(ref), a))


@_op("!")
def logical_not(a):
    return Bool(not a)
