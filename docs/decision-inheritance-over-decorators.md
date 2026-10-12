
Why inheritance instead of decorators?
----------------------------------------------------------------------------------------

Statica uses inheritance to define models:

```python
class MyModel(Statica):
	name: str = Field(min_length=3, max_length=50)
```

Under the hood, typing.dataclass_transform is used to tell the type checker that this is a dataclass-like class,
allowing for type checking and IDE support for the generated init mehod.

Additionally, typing.dataclass_transform also works with decorators,
theoretically allowing a syntax that is more similar to the built-in dataclasses:

```python
@Statica
class MyModel:
	name: str = Field(min_length=3, max_length=50)
```

However, this comes with drawbacks.
Consider the following example:

```python
from collections.abc import Callable
from typing import dataclass_transform, overload


class CustomError(Exception):
	def __init__(self, message: str) -> None:
		super().__init__(message)


class InjectionError(Exception):
	def __init__(self, message: str) -> None:
		super().__init__(message)


def to_dict_func(self) -> None:
	print("Test")


@overload
def validated_dataclass(
	*,
	custom_error: type[Exception],
) -> Callable[[Callable], Callable]: ...


@overload
def validated_dataclass(
	_cls: type | None = None,
	*,
	custom_error: type[Exception] = CustomError,
) -> Callable[[Callable], Callable]: ...


@dataclass_transform(kw_only_default=True, order_default=True)
def validated_dataclass(
	_cls: type | None = None,
	*,
	custom_error: type[Exception] = CustomError,
) -> Callable[[Callable], Callable]:
	def decorator_validated_dataclass(cls: type):
		def init(self, **kwargs):
			for name in cls.__annotations__:
				if name not in kwargs:
					msg = f"missing field {name}"
					raise custom_error(msg)
				setattr(self, name, kwargs[name])

		cls.__init__ = init
		cls.to_dict = to_dict_func

		return cls

	if _cls is None:
		return decorator_validated_dataclass

	return decorator_validated_dataclass(_cls)


@validated_dataclass
class MyClass:
	id: int


MyClass(id=1).to_dict()
```


As of October 2026, type checkers will not be able to understand that objects of type `MyClass` have a method `to_dict`.
Checked with pyrefly 1.3.2, mypy 2.4.0, ty 0.0.86 and pyright 1.1.414, all report that `MyClass` has no attribute `to_dict`.
This could be reconsidered in the future, but for now, Statica uses inheritance to ensure that type checkers can properly infer types and methods.
