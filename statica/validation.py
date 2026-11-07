"""
The backus naur grammar for types is as follows:
T ::= Statica
	| int
	| float
	| str
	| None
	| (T1 | T2)
	| list[T]
	| set[T]
	| dict[T1, T2]
	| Literal[V1, ...]


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
from typing import Any, Literal, TypeGuard, Union

from statica.config import StaticaConfig, default_config
from statica.exceptions import ConstraintValidationError, TypeValidationError

########################################################################################
#### MARK: Types


class LiteralGenericAlias:
	"""A type used in place of typing._LiteralGenericAlias to avoid private imports."""

	__origin__ = Literal
	__args__: tuple[Any, ...]


def is_literal_generic_alias(expected_type: Any) -> TypeGuard[LiteralGenericAlias]:
	return hasattr(expected_type, "__origin__") and expected_type.__origin__ is Literal


def is_union(expected_type: Any) -> bool:
	"""
	True for both union spellings, `X | Y` and `typing.Union[X, Y]` / `Optional[X]`.
	They are distinct types before Python 3.14 and the same type from 3.14 on.

	Runs on every validation, so it avoids `typing.get_origin`, which made
	instance creation about 45% slower in `benchmark_creation.py`.
	"""

	return (
		isinstance(expected_type, UnionType) or getattr(expected_type, "__origin__", None) is Union
	)


def type_name(expected_type: Any) -> str:
	"""Readable name for error messages, e.g. `int`, `list[str]`, `dict[str, int | None]`."""

	if expected_type is type(None):
		return "None"
	if isinstance(expected_type, type):
		return expected_type.__name__
	return str(expected_type)


########################################################################################
#### MARK: Type Validation


def validate_or_raise(
	value: Any,
	expected_type: Any,
	config: StaticaConfig = default_config,
) -> None:
	"""
	`expected_type` is any type expression the grammar above allows, typed as `Any`
	like the result of `typing.get_type_hints`.

	Value can be a nested structure, where all dicts with a Statica type hint
	are already initialized Statica objects.
	"""

	# Handle typing.Any, which accepts any value

	if expected_type is Any:
		return

	# Handle generic aliases of native python types, e.g. list[int], dict[str, int]

	if isinstance(expected_type, GenericAlias):
		validate_type_generic_alias(value, expected_type, config)
		return

	# Handle union types

	if is_union(expected_type):
		validate_union(value, expected_type.__args__, config)
		return

	# Handle Literal (e.g. Literal["a", "b"], with any number and type of values)

	if is_literal_generic_alias(expected_type):
		validate_literal(value, expected_type)
		return

	# Handle all other types

	if isinstance(value, expected_type):
		return

	msg = config.type_error_message.format(
		expected_type=type_name(expected_type),
		found_type=type(value).__name__,
	)
	raise TypeValidationError(msg)


def validate_literal(
	value: Any,
	expected_type: LiteralGenericAlias,
) -> None:
	"""
	Validate that the value matches one of the literals in the expected_type.
	Throws TypeValidationError if the value is not one of the literals.
	"""
	if value not in expected_type.__args__:
		msg = f"expected one of {expected_type.__args__}, got '{value}'"
		raise TypeValidationError(msg)


def validate_union(
	value: Any,
	members: tuple[Any, ...],
	config: StaticaConfig,
) -> None:
	"""
	Validate that the value matches one of the union members.
	Throws TypeValidationError if the value does not match any of them.
	"""
	for member in members:
		try:
			validate_or_raise(value, member, config)
		except TypeValidationError:
			continue  # Try the next member
		else:
			return  # Exit if one of the members matches

	msg = config.type_error_message.format(
		expected_type=" | ".join(type_name(member) for member in members),
		found_type=type(value).__name__,
	)
	raise TypeValidationError(msg)


def validate_type_generic_alias(
	value: Any,
	expected_type: GenericAlias,
	config: StaticaConfig,
) -> None:
	origin = expected_type.__origin__

	if origin is dict:
		key_type, value_type = expected_type.__args__

		if not isinstance(value, dict):
			msg = config.type_error_message.format(
				expected_type=type_name(expected_type),
				found_type=type(value).__name__,
			)
			raise TypeValidationError(msg)
		for key, val in value.items():
			validate_or_raise(key, key_type, config)
			validate_or_raise(val, value_type, config)

	elif origin is list:
		item_type = expected_type.__args__[0]

		if not isinstance(value, list):
			msg = config.type_error_message.format(
				expected_type=type_name(expected_type),
				found_type=type(value).__name__,
			)
			raise TypeValidationError(msg)
		for item in value:
			validate_or_raise(item, item_type, config)

	elif origin is set:
		item_type = expected_type.__args__[0]

		if not isinstance(value, set):
			msg = config.type_error_message.format(
				expected_type=type_name(expected_type),
				found_type=type(value).__name__,
			)
			raise TypeValidationError(msg)
		for item in value:
			validate_or_raise(item, item_type, config)

	else:
		msg = config.type_error_message.format(
			expected_type=type_name(expected_type),
			found_type=type(value).__name__ + " (not supported)",
		)
		raise TypeValidationError(msg)


########################################################################################
#### MARK: Constraint Validation


def validate_constraints(
	field_name: str,
	value: Any,
	*,
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
	config: StaticaConfig = default_config,
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

	if isinstance(value, (str, list, tuple, dict)):
		if min_length is not None and len(value) < min_length:
			msg = config.min_length_error_message.format(
				field_name=field_name,
				min_length=min_length,
			)
			raise ConstraintValidationError(msg)
		if max_length is not None and len(value) > max_length:
			msg = config.max_length_error_message.format(
				field_name=field_name,
				max_length=max_length,
			)
			raise ConstraintValidationError(msg)

	if isinstance(value, int | float):
		if min_value is not None and value < min_value:
			msg = config.min_value_error_message.format(
				field_name=field_name,
				min_value=min_value,
			)
			raise ConstraintValidationError(msg)
		if max_value is not None and value > max_value:
			msg = config.max_value_error_message.format(
				field_name=field_name,
				max_value=max_value,
			)
			raise ConstraintValidationError(msg)

	return value
