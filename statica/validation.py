"""
The backus naur grammar for types is as follows:
T ::= Statica | int | float | str | None | (T1 | T2) | list[T] | set[T] | dict[T1, T2]

Where:
- Statica: A class that inherits from Statica
- Built-in types: int, float, str, None
- Union types: (T1 | T2)
- Generic alias types: list[T], set[T], dict[T1, T2]

Note:
If a union type contains a generic alias, it cannot be checked using the `isinstance`
function, because `isinstance` does not support generic aliases directly.
"""

from __future__ import annotations

from types import GenericAlias, UnionType
from typing import Any

from statica.exceptions import ConstraintValidationError, TypeValidationError

########################################################################################
#### MARK: Type Validation


def validate_or_raise(
	value: Any,
	expected_type: type | UnionType | GenericAlias,
) -> None:
	"""
	Value can be a nested structure, where all dicts with have a Statica type hint
	are already initialized Statica objects.
	"""

	# Handle union types

	if isinstance(expected_type, UnionType):
		validate_type_union(value, expected_type)
		return

	# Handle generic aliases

	if isinstance(expected_type, GenericAlias):
		validate_type_generic_alias(value, expected_type)
		return

	# Handle all other types

	if isinstance(value, expected_type):
		return

	msg = f"expected type '{expected_type.__name__}', got '{type(value).__name__}'"
	raise TypeValidationError(msg)


def validate_type_union(value: Any, expected_type: UnionType) -> None:
	"""
	Validate that the value matches one of the types in the UnionType.
	Throws TypeValidationError if the type does not match any of the union types.
	"""
	for sub_type in expected_type.__args__:
		try:
			validate_or_raise(value, sub_type)
		except TypeValidationError:
			continue  # Try the next sub-type
		else:
			return  # Exit if one of the sub-types matches

	msg = f"expected one of types {expected_type.__args__}, got '{type(value).__name__}'"
	raise TypeValidationError(msg)


def validate_type_generic_alias(value: Any, expected_type: GenericAlias) -> None:
	origin = expected_type.__origin__

	if origin is dict:
		key_type, value_type = expected_type.__args__

		if not isinstance(value, dict):
			msg = (
				f"expected type 'dict[{key_type.__name__}, {value_type.__name__}]'"
				f", got '{type(value).__name__}'"
			)
			raise TypeValidationError(msg)
		for key, val in value.items():
			validate_or_raise(key, key_type)
			validate_or_raise(val, value_type)

	elif origin is list:
		item_type = expected_type.__args__[0]

		if not isinstance(value, list):
			msg = f"expected type 'list[{item_type.__name__}]', got '{type(value).__name__}'"
			raise TypeValidationError(msg)
		for item in value:
			validate_or_raise(item, item_type)

	elif origin is set:
		item_type = expected_type.__args__[0]

		if not isinstance(value, set):
			msg = f"expected type 'set[{item_type.__name__}]', got '{type(value).__name__}'"
			raise TypeValidationError(msg)
		for item in value:
			validate_or_raise(item, item_type)

	else:
		msg = f"Validation for type '{expected_type}' is not supported"
		raise TypeValidationError(msg)


########################################################################################
#### MARK: Constraint Validation


def validate_constraints(
	value: Any,
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
) -> Any:
	"""
	If the value is a string, strip the whitespace if `strip_whitespace` is True.

	If the value is a string, list, tuple, or dict, check its length against
	the `min_length` and `max_length` constraints.

	If the value is an int or float, check its value against the `min_value`
	and `max_value` constraints.

	Throws ConstraintValidationError if any constraints are violated.
	"""

	# For performance, exit early if no constraints are provided
	if (
		min_length is None
		and max_length is None
		and min_value is None
		and max_value is None
		and strip_whitespace is None
	):
		return value

	if strip_whitespace and isinstance(value, str):
		value = value.strip()

	if isinstance(value, str | list | tuple | dict):
		if min_length is not None and len(value) < min_length:
			msg = f"length must be at least {min_length}"
			raise ConstraintValidationError(msg)
		if max_length is not None and len(value) > max_length:
			msg = f"length must be at most {max_length}"
			raise ConstraintValidationError(msg)

	if isinstance(value, int | float):
		if min_value is not None and value < min_value:
			msg = f"must be at least {min_value}"
			raise ConstraintValidationError(msg)
		if max_value is not None and value > max_value:
			msg = f"must be at most {max_value}"
			raise ConstraintValidationError(msg)

	return value
