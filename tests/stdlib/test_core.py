# pylint: disable=missing-function-docstring,missing-module-docstring,invalid-name

import pytest

from mylang.stdlib.core import ref, return_
from mylang.stdlib.core._context import LocalsDict, StackFrame, current_stack_frame
from mylang.stdlib.core._utils import (
    function_defined_as_class,
    currently_called_func,
    FunctionAsClass,
    populate_locals_for_callable,
)
from mylang.stdlib.core.base import Args, Array, Dict, Object
from mylang.stdlib.core.complex import Path, String
from mylang.stdlib.core.func import StatementList, call, fun, set_, get
from mylang.stdlib.core.primitive import Int, undefined


@pytest.fixture(autouse=True)
def isolate_stack_frame():
    reset_token_1 = current_stack_frame.set(StackFrame())
    reset_token_2 = currently_called_func.set(None)
    yield
    current_stack_frame.reset(reset_token_1)
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
        array = Array.from_iterable([1, 2, 3])
        assert array._m_array_ == [1, 2, 3]


class Test_fun:
    def test_construct(self):
        f = fun("test", Args("x", StatementList(Args("call", "something")), a="A", b="B"))
        assert f.name == String("test")
        assert f.parameters == Args.from_dict({0: "x", "a": "A", "b": "B"})
        assert f.body == StatementList(Args("call", "something"))
        assert current_stack_frame.get()["test"] is f

    def test_call(self):
        """
        ```
        fun return_constant {
            return 42
        }
        ```
        """
        current_stack_frame.get().locals["return"] = return_
        f = fun(Args("return_constant", StatementList.from_iterable([Args("return", 42)])))
        result = f()
        assert result == Int(42)

    # TODO: Test arg to parameter binding


class Test_set:
    def test_call(self):
        result = set_(Args(a=1, b=2))
        stack_frame = current_stack_frame.get()
        assert stack_frame[String("a")] == Int(1)
        assert stack_frame[String("b")] == Int(2)
        assert result is undefined

    def test_call_python_args_kwargs(self):
        result = set_(a=1)
        stack_frame = current_stack_frame.get()
        assert stack_frame[String("a")] == Int(1)
        assert result is undefined

    def test_empty_call(self):
        result = set_()
        stack_frame = current_stack_frame.get()
        assert stack_frame.locals == {}
        assert result is undefined

    def test_set_path(self):
        obj = Dict()
        current_stack_frame.get().locals["obj"] = obj
        set_(Args.from_dict({Path("obj", "a"): Dict(b=1)}))
        set_(Args.from_dict({Path("obj", "a", "c"): 2}))

        assert obj == Dict(a=Dict(b=1, c=2))


class Test_call:
    @function_defined_as_class
    class func(Object, FunctionAsClass):
        _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

        @classmethod
        def _m_classcall_(cls, args: Args, /):
            return Array.from_iterable(["func_called", args[0], args[1], args["kwarg1"], args["kwarg2"]])

    def assert_result_correct(self, result):
        assert isinstance(result, Array)
        assert result._m_array_ == Array.from_iterable(
            [
                String("func_called"),
                String("arg0"),
                String("arg1"),
                String("KWARG1"),
                String("KWARG2"),
            ]
        )

    def test_call_args_kwargs(self):
        stack_frame = current_stack_frame.get()
        stack_frame.locals["func"] = self.func
        result = call("func", Args("arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"))
        self.assert_result_correct(result)

    def test_call_mylang_args(self):
        stack_frame = current_stack_frame.get()
        stack_frame.locals["func"] = self.func
        result = call(Args("func", "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"))
        self.assert_result_correct(result)

    def test_call_ref_of_func(self):
        result = call(ref.of(self.func), Args("arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"))
        self.assert_result_correct(result)

    def test_call_call(self):
        stack_frame = current_stack_frame.get()
        stack_frame.locals["call"] = call
        stack_frame.locals["func"] = self.func
        result = call("call", "func", "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2")
        self.assert_result_correct(result)

    def test_call_ref_of_call(self):
        result = call(
            ref.of(call),
            Args(ref.of(self.func), "arg0", "arg1", kwarg1="KWARG1", kwarg2="KWARG2"),
        )
        self.assert_result_correct(result)

    def test_call_ref_of_call_ref_of_call(self):
        result = call(
            Args(
                ref.of(call),
                ref.of(call),
                ref.of(self.func),
                "arg0",
                "arg1",
                kwarg1="KWARG1",
                kwarg2="KWARG2",
            )
        )
        self.assert_result_correct(result)


class Test_utils:
    def test_populate_locals_for_callable_positional_args(self):
        locals_ = LocalsDict({})

        # Call the method
        populate_locals_for_callable(
            locals_,
            Args("x", "y"),
            Args("X", "Y"),
        )

        # Check that positional arguments are mapped correctly
        assert locals_ == {String("x"): String("X"), String("y"): String("Y")}

    def test_populate_locals_for_callable_keyword_args(self):
        locals_ = LocalsDict({})

        # Call the method with keyword arguments
        populate_locals_for_callable(locals_, Args(first="default_1st", second="default_2nd"), Args(first="foo"))

        # Check that keyword arguments are mapped correctly
        assert locals_ == {String("first"): String("foo"), String("second"): String("default_2nd")}

    def test_populate_locals_for_callable_mixed_args(self):
        locals_ = LocalsDict({})

        # Call the method with mixed arguments
        locals_ = populate_locals_for_callable(
            locals_, Args("x", "y", third="default_3rd", fourth="default_4th"), Args("X", "Y", fourth="foo")
        )

        # Check that mixed arguments are mapped correctly
        assert locals_ == {
            String("x"): String("X"),
            String("y"): String("Y"),
            String("third"): String("default_3rd"),
            String("fourth"): String("foo"),
        }

    def test_populate_locals_for_callable_no_parameters(self):
        locals_ = LocalsDict({})

        # Call the method without parameters
        populate_locals_for_callable(locals_, Args(), Args())

        # Check that an empty context dict is returned
        assert locals_ == {}

    # TODO: Test invalid calls, e.g. too many positional arguments, etc.


class Test_get:
    def test_get_with_mylang_args(self):
        current_stack_frame.get().locals["key"] = Int(42)
        result = get(Args("key"))
        assert result == Int(42)

    def test_get_with_args_kwargs(self):
        current_stack_frame.get().locals["key"] = Int(42)
        result = get("key")
        assert result == Int(42)

    def test_get_ref(self):
        obj = Object()
        result = get(ref.of(obj))
        assert result is obj

    def test_get_non_existing_key(self):
        # TODO: Use custom exception
        with pytest.raises(KeyError):
            get("non_existing_key")

    def test_get_path(self):
        obj = Dict(a=1, b=Dict(c=2))
        current_stack_frame.get().locals["obj"] = obj
        b = get(Path("obj", "b"))
        c = get(Path("obj", "b", "c"))

        assert b == Dict(c=2)
        assert c == Int(2)


class Test_set_get:
    def test_set_then_get(self):
        set_(a=1, b=2)
        result_a = get("a")
        result_b = get("b")
        assert result_a == Int(1)
        assert result_b == Int(2)

    def test_set_key_obtained_using_get(self):
        set_(key="actual_key", actual_key="value")
        key = get("key")
        result = get(key)
        assert result == String("value")


class Test_ref:
    def test_ref_ref(self):
        obj = Object()
        ref_obj = ref.of(obj)
        ref_ref_obj = ref.of(ref_obj)
        assert ref_ref_obj.obj is obj


# TODO: Test function `ref`
# TODO: This file is incomplete
