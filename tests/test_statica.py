import pytest

from statica.core import (
	ConstraintValidationError,
	Field,
	Statica,
	TypeValidationError,
	_get_expected_type,
	_type_allows_none,
	_validate_type,
	_value_matches_type,
)


def test_allows_none() -> None:
	assert _type_allows_none(type(None))
	assert _type_allows_none(int | None)
	assert not _type_allows_none(int)


def test_value_matches_type() -> None:
	assert _value_matches_type(1, int)
	assert _value_matches_type("abc", str)
	assert not _value_matches_type(1, str)
	assert _value_matches_type(None, int | None)
	assert _value_matches_type(1, int | None)
	assert not _value_matches_type(None, int)
	assert _value_matches_type(1, int | None)
	assert not _value_matches_type("abc", int | None)


def test_validate_type() -> None:
	# No exceptions should be raised for valid types
	_validate_type(1, int)
	_validate_type("abc", str)
	_validate_type(None, int | None)
	_validate_type(1, int | None)

	# Exceptions should be raised for invalid types
	with pytest.raises(TypeValidationError):
		_validate_type(1, str)
	with pytest.raises(TypeValidationError):
		_validate_type("abc", int)
	with pytest.raises(TypeValidationError):
		_validate_type(None, int)
	with pytest.raises(TypeValidationError):
		_validate_type("abc", int | None)


def test_get_expected_type() -> None:
	class TestClass(Statica):
		required_field: str
		optional_field: str | None
		required_with_field: str = Field()
		optional_with_field: str | None = Field()

	assert _get_expected_type(TestClass, "required_field") is str
	assert _get_expected_type(TestClass, "optional_field") == str | None
	assert _get_expected_type(TestClass, "required_with_field") is str
	assert _get_expected_type(TestClass, "optional_with_field") == str | None


def test_basic_syntax() -> None:
	class RequiredStr(Statica):
		name: str

	i1 = RequiredStr.from_map({"name": "Test"})
	assert i1.name == "Test"

	i1 = RequiredStr(name="Test")
	assert i1.name == "Test"

	with pytest.raises(TypeValidationError):
		RequiredStr.from_map({})

	with pytest.raises(TypeValidationError):
		RequiredStr.from_map({"name": 123})

	class OptionalStr(Statica):
		name: str | None

	i2 = OptionalStr.from_map({"name": "Test"})
	assert i2.name == "Test"
	i2 = OptionalStr.from_map({"name": None})
	assert i2.name is None
	i2 = OptionalStr.from_map({})
	assert i2.name is None
	with pytest.raises(TypeValidationError):
		OptionalStr.from_map({"name": 123})


def test_different_field_syntax_variations() -> None:
	class StringTestSyntax1(Statica):
		name: str

	class StringTestSyntax2(Statica):
		name: str

	class StringTestSyntax3(Statica):
		name: str = Field()

	for cls in (StringTestSyntax1, StringTestSyntax2, StringTestSyntax3):
		instance = cls.from_map({"name": "Test"})

		assert getattr(instance, "name", None) == "Test"

		with pytest.raises(TypeValidationError):
			cls.from_map({})

		with pytest.raises(TypeValidationError):
			cls.from_map({"name": 123})


def test_required_string_field() -> None:
	class StringTest(Statica):
		name: str

	instance = StringTest(name="Test")
	assert instance.name == "Test"

	instance = StringTest.from_map({"name": "Test"})
	assert instance.name == "Test"

	with pytest.raises(TypeValidationError):
		StringTest.from_map({})

	with pytest.raises(TypeValidationError):
		StringTest.from_map({"name": 123})

	with pytest.raises(TypeValidationError):
		StringTest.from_map({"name": None})


def test_optional_string_field() -> None:
	class StringTest(Statica):
		name: str | None

	instance = StringTest.from_map({"name": "Test"})
	assert instance.name == "Test"

	instance = StringTest.from_map({"name": None})
	assert instance.name is None

	instance = StringTest.from_map({})
	assert instance.name is None

	with pytest.raises(TypeValidationError):
		StringTest.from_map({"name": 123})


def test_string_field_with_length_constraints() -> None:
	class StringTest(Statica):
		name: str = Field(min_length=3, max_length=5)

	instance = StringTest.from_map({"name": "Test"})
	assert instance.name == "Test"

	with pytest.raises(ConstraintValidationError) as exc_info:
		StringTest.from_map({"name": "Te"})
	assert "length must be at least 3" in str(exc_info.value)

	with pytest.raises(ConstraintValidationError) as exc_info:
		StringTest.from_map({"name": "Testing"})
	assert "length must be at most 5" in str(exc_info.value)


def test_string_field_with_whitespace_stripping() -> None:
	class StringTest(Statica):
		name: str = Field(strip_whitespace=True, max_length=4)

	instance = StringTest.from_map({"name": " Test "})
	assert instance.name == "Test"

	with pytest.raises(ConstraintValidationError) as exc_info:
		StringTest.from_map({"name": " TestLong "})
	assert "length must be at most 4" in str(exc_info.value)


def test_integer_field_with_value_constraints() -> None:
	class IntTest(Statica):
		num: int = Field(min_value=1, max_value=10)

	num = 5

	instance = IntTest.from_map({"num": num})
	assert instance.num == num

	with pytest.raises(ConstraintValidationError) as exc_info:
		IntTest.from_map({"num": 0})
	assert "must be at least 1" in str(exc_info.value)

	with pytest.raises(ConstraintValidationError) as exc_info:
		IntTest.from_map({"num": 11})
	assert "must be at most 10" in str(exc_info.value)


def test_custom_error_class() -> None:
	class CustomError(Exception):
		pass

	class IntTest(Statica):
		constraint_error_class = CustomError

		num: int = Field(min_value=1, max_value=10)

	with pytest.raises(CustomError) as exc_info:
		IntTest.from_map({"num": 0})
	assert "must be at least 1" in str(exc_info.value)

	class FloatTest(Statica):
		num: float = Field(min_value=1, max_value=10)

	num_float = 5.5

	instance = FloatTest.from_map({"num": num_float})
	assert instance.num == num_float

	with pytest.raises(TypeValidationError):
		FloatTest.from_map({"num": "4"})


def test_cast() -> None:
	class IntTest(Statica):
		num: int = Field(cast_to=int)

	num_int = 5
	num_str = str(num_int)

	instance = IntTest.from_map({"num": num_str})
	assert instance.num == num_int

	with pytest.raises(TypeValidationError):
		IntTest.from_map({"num": "5.5"})


if __name__ == "__main__":
	pytest.main([__file__])
