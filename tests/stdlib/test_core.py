from mylang.stdlib.core._utils import (
    function_defined_as_class,
    python_obj_to_mylang,
    currently_called_func,
)
from mylang.stdlib.core.base import Args, Array, Object, Ref
from mylang.stdlib.core.complex import String
from mylang.stdlib.core.func import call, fun, set, get
from mylang.stdlib.core.primitive import Int, undefined
from mylang.stdlib.core._context import Context, current_context
import pytest


@pytest.fixture(autouse=True)
def isolate_context():
    reset_token_1 = current_context.set(Context())
    reset_token_2 = currently_called_func.set(None)
    yield
    current_context.reset(reset_token_1)
    currently_called_func.reset(reset_token_2)


class TestArgs:
    def test_construct_empty(self):
        args = Args()
        assert args._m_dict_ == {}

    def test_construct_from_dict(self):
        args = Args.from_dict({"a": 1, "b": 2})
        assert args._m_dict_ == {String("a"): Int(1), String("b"): Int(2)}

    def test_construct_from_args_kwargs(self):
        args = Args(10, 11, a="A", b="B")
        assert args._m_dict_ == {
            Int(0): Int(10),
            Int(1): Int(11),
            String("a"): String("A"),
            String("b"): String("B"),
        }

    def test_add_other_args(self):
        args = Args(10, 11, a="A", b="B")
        new_args = args + Args(12, 13, c="C")
        assert new_args._m_dict_ == {
            Int(0): Int(10),
            Int(1): Int(11),
            Int(2): Int(12),
            Int(3): Int(13),
            String("a"): String("A"),
            String("b"): String("B"),
            String("c"): String("C"),
        }

    def test_add_iterable(self):
        args = Args(10, 11, a="A", b="B")
        new_args = args + {12, 13}
        assert new_args._m_dict_ == {
            Int(0): Int(10),
            Int(1): Int(11),
            Int(2): Int(12),
            Int(3): Int(13),
            String("a"): String("A"),
            String("b"): String("B"),
        }

    def test_radd_iterable(self):
        args = Args(12, 13, a="A", b="B")
        new_args = {10, 11} + args
        assert new_args._m_dict_ == {
            Int(0): Int(10),
            Int(1): Int(11),
            Int(2): Int(12),
            Int(3): Int(13),
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
        result = set(Args(a=1, b=2))
        context = current_context.get()
        assert context[String("a")] == Int(1)
        assert context[String("b")] == Int(2)
        assert result is undefined

    def test_call_python_args_kwargs(self):
        result = set(a=1)
        context = current_context.get()
        assert context[String("a")] == Int(1)
        assert result is undefined

    def test_empty_call(self):
        result = set()
        context = current_context.get()
        assert context.dict_ == {}
        assert result is undefined


class Test_call:
    @function_defined_as_class
    class func(Object):
        @classmethod
        def _m_call_(self, args: Args, /):
            return ["func_called", args[0], args[1], args["kwarg1"], args["kwarg2"]]

    def assert_result_correct(self, result):
        assert isinstance(result, Array)
        assert result._m_array_ == Array.from_list(
            [
                String("func_called"),
                String("arg0"),
                String("arg1"),
                String("KWARG1"),
                String("KWARG2"),
            ]
        )

    def test_call_args_kwargs(self):
        context = current_context.get()
        context["func"] = self.func
        result = call("func", Args("arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"))
        self.assert_result_correct(result)

    def test_call_mylang_args(self):
        context = current_context.get()
        context["func"] = self.func
        result = call(Args("func", "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"))
        self.assert_result_correct(result)

    def test_call_ref_of_func(self):
        result = call(
            Ref.of(self.func), Args("arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2")
        )
        self.assert_result_correct(result)

    def test_call_call(self):
        current_context.get()["call"] = call
        current_context.get()["func"] = self.func
        result = call(
            "call", "func", "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"
        )
        self.assert_result_correct(result)

    def test_call_ref_of_call(self):
        result = call(
            Ref.of(call),
            Args(Ref.of(self.func), "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"),
        )
        self.assert_result_correct(result)

    def test_call_ref_of_call_ref_of_call(self):
        result = call(
            Args(Ref.of(call), Ref.of(call), Ref.of(self.func), "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2")
        )
        self.assert_result_correct(result)


class Test_get:
    def test_get_with_mylang_args(self):
        current_context.get()['key'] = Int(42)
        result = get(Args('key'))
        assert result == Int(42)

    def test_get_with_args_kwargs(self):
        current_context.get()['key'] = Int(42)
        result = get("key")
        assert result == Int(42)

    def test_get_ref(self):
        obj = Object()
        result = get(Ref.of(obj))
        assert result is obj

    def test_get_non_existing_key(self):
        # TODO: Use custom exception
        with pytest.raises(KeyError):
            get("non_existing_key")


class Test_set_get:
    def test_set_then_get(self):
        set(a=1, b=2)
        result_a = get("a")
        result_b = get("b")
        assert result_a == Int(1)
        assert result_b == Int(2)

    def test_set_key_obtained_using_get(self):
        set(key='actual_key', actual_key='value')
        key = get("key")
        result = get(key)
        assert result == String('value')
