from mylang.stdlib.core._utils import python_obj_to_mylang
from mylang.stdlib.core.base import Args, Array
from mylang.stdlib.core.complex import String
from mylang.stdlib.core.func import fun, set
from mylang.stdlib.core.primitive import Int, undefined
from mylang.stdlib.core._context import Context, current_context


class TestArgs:
    def test_construct_empty(self):
        args = Args()
        assert args._m_dict_ == {}

    def test_construct_from_dict(self):
        args = Args.from_dict({"a": 1, "b": 2})
        assert args._m_dict_ == {String("a"): Int(1), String("b"): Int(2)}

    def test_construct_from_args(self):
        args = Args(10, 11, a="A", b="B")
        assert args._m_dict_ == {
            Int(0): Int(10),
            Int(1): Int(11),
            String("a"): String("A"),
            String("b"): String("B"),
        }


class TestArray:
    def test_construct_empty(self):
        args = Array()
        assert args._m_array_ == []

    def test_construct_from_list(self):
        array = Array.from_list([1, 2, 3])
        assert array._m_array_ == [1, 2, 3]


class Test_fun:
    def test_construct(self):
        f = fun(Args("test", "x", Array(Args("call", "something")), a="A", b="B"))
        assert f.name == String("test")
        assert f.parameters == python_obj_to_mylang(
            {0: "test", 1: "x", "a": "A", "b": "B"}
        )
        assert f.body == Array(Args("call", "something"))


class Test_set:
    def test_call(self):
        set(Args(a=1, b=2))
        context = current_context.get()
        assert context[String('a')] == Int(1)
        assert context[String('b')] == Int(2)

    def test_call_python_args_kwargs(self):
        set(a=1)
        context = current_context.get()
        assert context[String('a')] == Int(1)

    def test_empty_call(self):
        set()
        context = current_context.get()
        assert context.dict_ == {}
