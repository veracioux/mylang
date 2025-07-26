from mylang.stdlib.core.primitive import Int

from .base import Args, Array, Dict, Object
from ._utils import python_obj_to_mylang


class fun(Dict):
    def __init__(self, name: Object, /, *args, **kwargs):
        self.name: Object
        self.parameters: Dict
        self.body: Array[Args]
        super().__init__(name, *args, **kwargs)

    def _m_init_(self, args: 'Args', /):
        last_positional_index = args.get_last_positional()
        if last_positional_index is not None and last_positional_index >= 1:
            self.body = args[last_positional_index]
            if last_positional_index >= 1:
                self.name = args[0]
            self.parameters = python_obj_to_mylang({
                k: v for k, v in args._m_dict_.items()
                if k != last_positional_index
            })
        else:
            raise ValueError("Function requires at least two positional arguments - name and body")

    def __call__(self, *args, **kwargs):
        pass

    def _m_call_(self, args: Args, /):
        pass


class call(Object):
    def __call__(self):
        pass

    def _m_call_(self, args: Args, /):
        pass


class get(Object):
    def __call__(self):
        pass
