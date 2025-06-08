from __future__ import annotations

from types import UnionType
from typing import Any

from statica.exceptions import ConstraintValidationError, TypeValidationError
from statica.types_utils import value_matches_type


def validate_type(value: Any, expected_type: type | UnionType) -> None:
	"""
	Validate that the value matches the expected type.
	Throws TypeValidationError if the type does not match.

	Examples:
	.. code-block:: python
		_validate_type(1, int)  # No exception
		_validate_type("abc", str)  # No exception
		_validate_type(1, str)  # Raises TypeValidationError
		_validate_type(None, int | None)  # No exception
		_validate_type(None, int)  # Raises TypeValidationError
	"""
	if not value_matches_type(value, expected_type):
		expected_type_str = str(expected_type) if type(expected_type) is UnionType else expected_type.__name__

		msg = f"expected type '{expected_type_str}', got '{type(value).__name__}'"
		raise TypeValidationError(msg)


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
