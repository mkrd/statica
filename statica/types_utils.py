from __future__ import annotations

from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints


def type_allows_none(expected_type: Any) -> bool:
	"""
	Check if the expected type allows None.

	Examples:
	.. code-block:: python
		_allows_none(int | None)  # True
		_allows_none(int)  # False
	"""
	if isinstance(expected_type, UnionType):
		return type(None) in get_args(expected_type)
	return expected_type is type(None) or expected_type is Any


def value_matches_type(value: Any | None, expected_type: Any) -> bool:
	"""
	Check if the value matches the expected type.
	Handles basic types, Union types, and generic types.

	Examples:
	.. code-block:: python
		_value_matches_type(1, int)  # True
		_value_matches_type(None, int | None)  # True
		_value_matches_type(None, int)  # False
	"""
	# If expected_type is e.g. int | None, pass if value is None
	if type_allows_none(expected_type) and value is None:
		return True

	# Basic types like int, str, etc.
	if (origin := get_origin(expected_type)) is None:
		return isinstance(value, expected_type)

	# Handle Union types
	if origin is UnionType or origin is type(None) or origin is Any:
		types = get_args(expected_type)
		return any(value_matches_type(value, t) for t in types if t is not type(None))

	# Handle generic types
	return isinstance(value, origin)


def get_expected_type(cls: type, attr_name: str) -> Any:
	"""
	Get the expected type for a class attribute.
	Handles type hints and Field descriptors.

	Examples:
	.. code-block:: python
		class MyClass(Statica):
			age: int | None
			name: str = Field()

		_get_expected_type(MyClass, "age")  # int | None
		_get_expected_type(MyClass, "name")  # str
	"""

	return get_type_hints(cls).get(attr_name, Any)
