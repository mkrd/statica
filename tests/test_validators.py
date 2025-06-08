import pytest

from statica.core import TypeValidationError
from statica.validators import validate_type


def test_validate_type() -> None:
	# No exceptions should be raised for valid types

	validate_type(1, int)
	validate_type("abc", str)
	validate_type(None, int | None)
	validate_type(1, int | None)

	# Exceptions should be raised for invalid types

	with pytest.raises(TypeValidationError):
		validate_type(1, str)
	with pytest.raises(TypeValidationError):
		validate_type("abc", int)
	with pytest.raises(TypeValidationError):
		validate_type(None, int)
	with pytest.raises(TypeValidationError):
		validate_type("abc", int | None)
