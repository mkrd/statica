import pytest

from statica.core import Field, Statica, TypeValidationError
from statica.exceptions import ConstraintValidationError

INTEGER = 42
FLOAT = 19.99
STRING = "test string"


def test_basic_alias() -> None:
	class AliasTest(Statica):
		full_name: str = Field(alias="fullName")
		age: int = Field(alias="userAge")

	# Test parsing with alias
	data = {"fullName": "John Doe", "userAge": INTEGER}
	instance = AliasTest.from_map(data)
	assert instance.full_name == "John Doe"
	assert instance.age == INTEGER
	assert instance.to_dict() == data

	# Test that original field names don't work when alias is used
	with pytest.raises(KeyError):
		AliasTest.from_map({"full_name": "John Doe", "age": INTEGER})


def test_alias_for_parsing() -> None:
	"""Test alias_for_parsing specifically."""

	class ParseAliasTest(Statica):
		user_name: str = Field(alias_for_parsing="userName")
		user_id: int = Field(alias_for_parsing="userId")

	# Test parsing with parsing alias
	instance = ParseAliasTest.from_map({"userName": "alice", "userId": INTEGER})
	assert instance.user_name == "alice"
	assert instance.user_id == INTEGER


def test_alias_priority() -> None:
	"""Test that alias_for_parsing takes priority over general alias."""

	class PriorityTest(Statica):
		field_name: str = Field(alias="generalAlias", alias_for_parsing="parseAlias")

	# Should use alias_for_parsing
	instance = PriorityTest.from_map({"parseAlias": STRING})
	assert instance.field_name == STRING

	# General alias should not work when alias_for_parsing exists
	with pytest.raises(KeyError):
		PriorityTest.from_map({"generalAlias": STRING})


def test_alias_with_optional_fields() -> None:
	"""Test aliases with optional fields."""

	class OptionalAliasTest(Statica):
		required_field: str = Field(alias="reqField")
		optional_field: str | None = Field(alias="optField")

	# Test with both fields provided
	instance = OptionalAliasTest.from_map({"reqField": "required", "optField": "optional"})
	assert instance.required_field == "required"
	assert instance.optional_field == "optional"

	# Test with only required field
	instance = OptionalAliasTest.from_map({"reqField": "required"})
	assert instance.required_field == "required"
	assert instance.optional_field is None

	# Test missing required field should still raise error
	with pytest.raises(TypeValidationError):
		OptionalAliasTest.from_map({"optField": "optional"})


def test_alias_with_constraints() -> None:
	"""Test that aliases work with field constraints."""

	class ConstraintAliasTest(Statica):
		name: str = Field(alias="userName", min_length=3, max_length=10, strip_whitespace=True)
		score: int = Field(alias="userScore", min_value=0, max_value=100)

	# Test valid values
	instance = ConstraintAliasTest.from_map({"userName": " Alice ", "userScore": INTEGER})
	assert instance.name == "Alice"  # Whitespace should be stripped
	assert instance.score == INTEGER

	# Test constraint violations with aliases
	with pytest.raises(ConstraintValidationError):  # Should be ConstraintValidationError
		ConstraintAliasTest.from_map({"userName": "Al", "userScore": INTEGER})  # Too short

	with pytest.raises(ConstraintValidationError):  # Should be ConstraintValidationError
		ConstraintAliasTest.from_map({"userName": "Alice", "userScore": 150})  # Too high


def test_alias_with_casting() -> None:
	"""Test that aliases work with type casting."""

	class CastAliasTest(Statica):
		number: int = Field(alias="numStr", cast_to=int)
		price: float = Field(alias="priceStr", cast_to=float)

	instance = CastAliasTest.from_map({"numStr": "42", "priceStr": "19.99"})
	assert instance.number == INTEGER
	assert instance.price == FLOAT


def test_mixed_alias_and_no_alias() -> None:
	"""Test mixing fields with and without aliases."""

	class MixedTest(Statica):
		normal_field: str
		aliased_field: str = Field(alias="aliasedField")
		another_normal: int

	instance = MixedTest.from_map(
		{
			"normal_field": "normal",
			"aliasedField": "aliased",
			"another_normal": INTEGER,
		},
	)
	assert instance.normal_field == "normal"
	assert instance.aliased_field == "aliased"
	assert instance.another_normal == INTEGER


def test_alias_serialization() -> None:
	class SerializationTest(Statica):
		field_name: str = Field(alias_for_serialization="serialAlias")

	instance = SerializationTest(field_name=STRING)

	assert instance.to_dict() == {"serialAlias": STRING}


def test_all_alias_types_together() -> None:
	"""Test a field with all three alias types."""

	class AllAliasTest(Statica):
		field_name: str = Field(
			alias="generalAlias",
			alias_for_parsing="parseAlias",
			alias_for_serialization="serializeAlias",
		)

	# Should use alias_for_parsing for parsing
	instance = AllAliasTest.from_map({"parseAlias": STRING})
	assert instance.field_name == STRING
	assert instance.to_dict() == {"serializeAlias": STRING}


def test_empty_alias_mapping() -> None:
	"""Test behavior when no matching aliases are found in the mapping."""

	class EmptyMappingTest(Statica):
		field_name: str = Field(alias="expectedAlias")

	# Should raise KeyError when the aliased field is missing
	with pytest.raises(KeyError):
		EmptyMappingTest.from_map({"wrongAlias": "value"})
