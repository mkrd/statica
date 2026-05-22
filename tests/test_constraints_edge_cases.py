"""Tests for constraint edge cases and boundary conditions."""

import pytest

from statica import Field, Statica
from statica.exceptions import ConstraintValidationError

SCORE_MAX = 100
FIXED_VALUE = 42
RATIO_HALF = 0.5
LONG_STRING_LEN = 1000
LARGE_COUNT = 999999
NEGATIVE_COUNT = -999
TEMP_MIN = -40
SCORE_85 = 85


def test_min_length_at_exact_boundary() -> None:
	"""Test value at exact min_length boundary passes."""

	class Model(Statica):
		name: str = Field(min_length=3)

	instance = Model(name="abc")
	assert instance.name == "abc"


def test_max_length_at_exact_boundary() -> None:
	"""Test value at exact max_length boundary passes."""

	class Model(Statica):
		name: str = Field(max_length=5)

	instance = Model(name="abcde")
	assert instance.name == "abcde"


def test_min_value_at_exact_boundary() -> None:
	"""Test value at exact min_value boundary passes."""

	class Model(Statica):
		age: int = Field(min_value=0)

	instance = Model(age=0)
	assert instance.age == 0


def test_max_value_at_exact_boundary() -> None:
	"""Test value at exact max_value boundary passes."""

	class Model(Statica):
		score: int = Field(max_value=SCORE_MAX)

	instance = Model(score=SCORE_MAX)
	assert instance.score == SCORE_MAX


def test_min_and_max_length_equal() -> None:
	"""Test that min_length == max_length enforces exact length."""

	class Model(Statica):
		code: str = Field(min_length=5, max_length=5)

	instance = Model(code="abcde")
	assert instance.code == "abcde"

	with pytest.raises(ConstraintValidationError):
		Model(code="abcd")

	with pytest.raises(ConstraintValidationError):
		Model(code="abcdef")


def test_min_and_max_value_equal() -> None:
	"""Test that min_value == max_value enforces exact value."""

	class Model(Statica):
		fixed: int = Field(min_value=FIXED_VALUE, max_value=FIXED_VALUE)

	instance = Model(fixed=FIXED_VALUE)
	assert instance.fixed == FIXED_VALUE

	with pytest.raises(ConstraintValidationError):
		Model(fixed=FIXED_VALUE - 1)

	with pytest.raises(ConstraintValidationError):
		Model(fixed=FIXED_VALUE + 1)


def test_float_value_constraints() -> None:
	"""Test float min_value/max_value constraints."""

	class Model(Statica):
		ratio: float = Field(min_value=0.0, max_value=1.0)

	instance = Model(ratio=RATIO_HALF)
	assert instance.ratio == RATIO_HALF

	instance = Model(ratio=0.0)
	assert instance.ratio == 0.0

	instance = Model(ratio=1.0)
	assert instance.ratio == 1.0

	with pytest.raises(ConstraintValidationError):
		Model(ratio=-0.1)

	with pytest.raises(ConstraintValidationError):
		Model(ratio=1.1)


def test_list_length_constraints() -> None:
	"""Test min_length/max_length applied to lists."""

	class Model(Statica):
		items: list[int] = Field(min_length=1, max_length=3)

	instance = Model(items=[1])
	assert instance.items == [1]

	instance = Model(items=[1, 2, 3])
	assert instance.items == [1, 2, 3]

	with pytest.raises(ConstraintValidationError):
		Model(items=[])

	with pytest.raises(ConstraintValidationError):
		Model(items=[1, 2, 3, 4])


def test_dict_length_constraints() -> None:
	"""Test min_length/max_length applied to dicts."""

	class Model(Statica):
		data: dict[str, int] = Field(min_length=1, max_length=2)

	instance = Model(data={"a": 1})
	assert instance.data == {"a": 1}

	with pytest.raises(ConstraintValidationError):
		Model(data={})

	with pytest.raises(ConstraintValidationError):
		Model(data={"a": 1, "b": 2, "c": 3})


def test_strip_whitespace_then_length_check() -> None:
	"""Test that strip_whitespace is applied before length checks."""

	class Model(Statica):
		name: str = Field(strip_whitespace=True, min_length=3)

	# "  ab  " stripped to "ab" which is length 2 -> should fail
	with pytest.raises(ConstraintValidationError):
		Model(name="  ab  ")

	# "  abc  " stripped to "abc" which is length 3 -> should pass
	instance = Model(name="  abc  ")
	assert instance.name == "abc"


def test_only_min_length_constraint() -> None:
	"""Test having only min_length without max_length."""

	class Model(Statica):
		name: str = Field(min_length=1)

	instance = Model(name="a")
	assert instance.name == "a"

	instance = Model(name="a" * LONG_STRING_LEN)
	assert len(instance.name) == LONG_STRING_LEN

	with pytest.raises(ConstraintValidationError):
		Model(name="")


def test_only_max_length_constraint() -> None:
	"""Test having only max_length without min_length."""

	class Model(Statica):
		name: str = Field(max_length=5)

	instance = Model(name="")
	assert instance.name == ""

	instance = Model(name="abcde")
	assert instance.name == "abcde"

	with pytest.raises(ConstraintValidationError):
		Model(name="abcdef")


def test_only_min_value_constraint() -> None:
	"""Test having only min_value without max_value."""

	class Model(Statica):
		count: int = Field(min_value=0)

	instance = Model(count=0)
	assert instance.count == 0

	instance = Model(count=LARGE_COUNT)
	assert instance.count == LARGE_COUNT

	with pytest.raises(ConstraintValidationError):
		Model(count=-1)


def test_only_max_value_constraint() -> None:
	"""Test having only max_value without min_value."""

	class Model(Statica):
		count: int = Field(max_value=SCORE_MAX)

	instance = Model(count=NEGATIVE_COUNT)
	assert instance.count == NEGATIVE_COUNT

	instance = Model(count=SCORE_MAX)
	assert instance.count == SCORE_MAX

	with pytest.raises(ConstraintValidationError):
		Model(count=SCORE_MAX + 1)


def test_negative_min_value() -> None:
	"""Test negative min_value boundary."""

	class Model(Statica):
		temp: int = Field(min_value=TEMP_MIN, max_value=50)

	instance = Model(temp=TEMP_MIN)
	assert instance.temp == TEMP_MIN

	instance = Model(temp=0)
	assert instance.temp == 0

	with pytest.raises(ConstraintValidationError):
		Model(temp=TEMP_MIN - 1)


def test_constraint_error_includes_field_name() -> None:
	"""Test that constraint error messages include the field name."""

	class Model(Statica):
		username: str = Field(min_length=3)

	with pytest.raises(ConstraintValidationError, match="username"):
		Model(username="ab")


def test_custom_constraint_error_class() -> None:
	"""Test that custom constraint_error_class is raised."""

	class MyError(Exception):
		pass

	class Model(Statica):
		constraint_error_class = MyError
		age: int = Field(min_value=0)

	with pytest.raises(MyError):
		Model(age=-1)


def test_custom_type_error_class() -> None:
	"""Test that custom type_error_class is raised on type mismatch."""

	class MyTypeError(Exception):
		pass

	class Model(Statica):
		type_error_class = MyTypeError
		name: str

	with pytest.raises(MyTypeError):
		Model(name=123)  # type: ignore[arg-type]


def test_constraints_with_from_map() -> None:
	"""Test that constraints work when using from_map."""

	class Model(Statica):
		name: str = Field(min_length=2, max_length=10)
		score: int = Field(min_value=0, max_value=SCORE_MAX)

	instance = Model.from_map({"name": "Alice", "score": SCORE_85})
	assert instance.name == "Alice"
	assert instance.score == SCORE_85

	with pytest.raises(ConstraintValidationError):
		Model.from_map({"name": "A", "score": 50})

	with pytest.raises(ConstraintValidationError):
		Model.from_map({"name": "Alice", "score": 150})
