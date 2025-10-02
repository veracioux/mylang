"""Built-in objects for the MyLang programming language.

Importing this module makes the built-in objects available in the current context.
"""

# pylint: disable=unused-import

from .core._context import LocalsDict
from .core import *
from .core import op, Object, String
from .io import echo
from .doc import doc


def create_locals_dict():
    """Makes the builtin objects available in the current context."""
    from .core._utils import is_exposed

    dict_ = LocalsDict(
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
        dict_[operator] = op.operators[operator]

    return dict_
