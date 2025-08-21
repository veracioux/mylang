"""Built-in objects for the MyLang programming language.

Importing this module makes the built-in objects available in the current context.
"""

from .core import *
from .core import op
from .core import Object, String
from .io import echo


def __initialize_context():
    """Makes the builtin objects available in the current context."""
    from .core._context import Context, current_context
    from .core._utils import is_exposed

    context = Context(
        {
            String(v._m_name_ if hasattr(v, "_m_name_") else k): v
            for k, v in globals().items()
            if (
                not k.startswith("_")
                and (
                    (isinstance(v, type) and issubclass(v, Object))
                    or isinstance(v, Object)
                )
                and is_exposed(v)
            )
        }
    )

    # TODO: Make operators first class citizens
    for operator in op.operators:
        context[operator] = op.operators[operator]

    current_context.set(context)


__initialize_context()
