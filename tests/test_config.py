import pytest

from statica import ConstraintValidationError, Field, Statica, TypeValidationError
from statica.config import StaticaConfig


def test_default_config_error_messages() -> None:
	"""Test that default error messages are used when no custom config is provided."""

	class DefaultTest(Statica):
		name: str = Field(min_length=3)
		age: int = Field(min_value=18, max_value=65)

	# Test type error with default message
	with pytest.raises(TypeValidationError) as exc_info:
		DefaultTest.from_map({"name": "John", "age": "not_int"})
	assert "expected type 'int', got 'str'" in str(exc_info)

	# Test constraint error with default message
	with pytest.raises(ConstraintValidationError) as exc_info_type:
		DefaultTest(name="Jo", age=25)
	assert "name length must be at least 3" in str(exc_info_type)

	with pytest.raises(ConstraintValidationError) as exc_info_constraint:
		DefaultTest(name="John Doe", age=17)
	assert "age must be at least 18" in str(exc_info_constraint)


def test_custom_config_type_error_message() -> None:
	"""Test custom type error message configuration."""

	custom_config = StaticaConfig.create(
		type_error_message="{found_type} is not {expected_type}",
	)

	class CustomTypeErrorTest(Statica, config=custom_config):
		name: str
		age: int

	with pytest.raises(TypeValidationError) as exc_info:
		CustomTypeErrorTest.from_map({"name": "John", "age": "x"})
	assert "str is not int" in str(exc_info)

	with pytest.raises(TypeValidationError) as exc_info:
		CustomTypeErrorTest.from_map({"name": 123, "age": 30})
	assert "int is not str" in str(exc_info)


def test_custom_config_length_error_messages() -> None:
	"""Test custom length constraint error messages."""

	custom_config = StaticaConfig.create(
		min_length_error_message="{field_name} < {min_length}",
		max_length_error_message="{field_name} < {max_length}",
	)

	class CustomLengthErrorTest(Statica, config=custom_config):
		username: str = Field(min_length=3, max_length=10)
		description: str = Field(max_length=50)

	# Test min length error
	with pytest.raises(ConstraintValidationError) as exc_info:
		CustomLengthErrorTest(username="ab", description="Valid description")
	assert "username < 3" in str(exc_info.value)

	# Test max length error
	with pytest.raises(ConstraintValidationError) as exc_info:
		CustomLengthErrorTest(username="validuser", description="a" * 51)
	assert "description < 50" in str(exc_info.value)


def test_custom_config_value_error_messages() -> None:
	"""Test custom value constraint error messages."""

	custom_config = StaticaConfig.create(
		min_value_error_message="{field_name} < {min_value}",
		max_value_error_message="{field_name} > {max_value}",
	)

	class CustomValueErrorTest(Statica, config=custom_config):
		age: int = Field(min_value=0, max_value=120)
		price: float = Field(min_value=0.01, max_value=999.99)

	# Test min value error
	with pytest.raises(ConstraintValidationError) as exc_info:
		CustomValueErrorTest(age=-1, price=10.0)
	assert "age < 0" in str(exc_info.value)

	# Test max value error
	with pytest.raises(ConstraintValidationError) as exc_info:
		CustomValueErrorTest(age=25, price=1000.0)
	assert "price > 999.99" in str(exc_info.value)


def test_custom_config_with_from_map() -> None:
	"""Test that custom configuration works with from_map method."""

	custom_config = StaticaConfig.create(
		type_error_message="from_map error: expected {expected_type}, got {found_type}",
		min_length_error_message="from_map: {field_name} needs at least {min_length} chars",
	)

	class FromMapTest(Statica, config=custom_config):
		name: str = Field(min_length=5)
		age: int

	# Test type error via from_map
	with pytest.raises(TypeValidationError) as exc_info_type:
		FromMapTest.from_map({"name": "Valid Name", "age": "not_int"})
	assert "from_map error: expected int, got str" in str(exc_info_type.value)

	# Test constraint error via from_map
	with pytest.raises(ConstraintValidationError) as exc_info_cosnstraint:
		FromMapTest.from_map({"name": "Jon", "age": 25})
	assert "from_map: name needs at least 5 chars" in str(exc_info_cosnstraint.value)


def test_custom_config_with_nested_statica() -> None:
	"""Test that custom configuration works with nested Statica objects."""

	inner_config = StaticaConfig.create(
		type_error_message="Inner error: expected {expected_type}, got {found_type}",
	)

	outer_config = StaticaConfig.create(
		type_error_message="Outer error: expected {expected_type}, got {found_type}",
	)

	class InnerTest(Statica, config=inner_config):
		value: str

	class OuterTest(Statica, config=outer_config):
		inner: InnerTest
		name: str

	# Test inner object error uses inner config
	with pytest.raises(TypeValidationError) as exc_info:
		OuterTest.from_map({"inner": {"value": 123}, "name": "Outer"})
	assert "Inner error: expected str, got int" in str(exc_info.value)

	# Test outer object error uses outer config
	with pytest.raises(TypeValidationError) as exc_info:
		OuterTest.from_map({"inner": {"value": "inner"}, "name": 123})
	assert "Outer error: expected str, got int" in str(exc_info.value)


def test_config_with_union_types() -> None:
	"""Test custom configuration with union types."""

	custom_config = StaticaConfig.create(
		type_error_message="Union error: expected one of {expected_type}, got {found_type}",
	)

	class UnionTest(Statica, config=custom_config):
		value: str | int
		optional_value: str | None = Field(min_length=3)

	# Test union type error
	with pytest.raises(TypeValidationError) as exc_info:
		UnionTest.from_map({"value": 3.14, "optional_value": "test"})
	assert "Union error: expected one of" in str(exc_info.value)
	assert "got float" in str(exc_info.value)


def test_config_with_list_and_dict_constraints() -> None:
	"""Test custom configuration with list and dict length constraints."""

	custom_config = StaticaConfig.create(
		min_length_error_message="Collection {field_name} must have at least {min_length} items",
		max_length_error_message="Collection {field_name} can have at most {max_length} items",
	)

	class CollectionTest(Statica, config=custom_config):
		tags: list[str] = Field(min_length=1, max_length=5)
		metadata: dict[str, str] = Field(min_length=1, max_length=3)

	# Test list length errors
	with pytest.raises(ConstraintValidationError) as exc_info:
		CollectionTest(tags=[], metadata={"key": "value"})
	assert "Collection tags must have at least 1 items" in str(exc_info.value)

	with pytest.raises(ConstraintValidationError) as exc_info:
		CollectionTest(tags=["a"] * 6, metadata={"key": "value"})
	assert "Collection tags can have at most 5 items" in str(exc_info.value)

	# Test dict length errors
	with pytest.raises(ConstraintValidationError) as exc_info:
		CollectionTest(tags=["valid"], metadata={})
	assert "Collection metadata must have at least 1 items" in str(exc_info.value)

	with pytest.raises(ConstraintValidationError) as exc_info:
		CollectionTest(tags=["valid"], metadata={f"key{i}": f"value{i}" for i in range(4)})
	assert "Collection metadata can have at most 3 items" in str(exc_info.value)


def test_config_create_method_defaults() -> None:
	"""Test that StaticaConfig.create() method works with partial parameters."""

	# Test with only one custom message
	config1 = StaticaConfig.create(type_error_message="Custom type error")
	assert config1.type_error_message == "Custom type error"
	assert config1.min_length_error_message == "{field_name} length must be at least {min_length}"

	# Test with multiple custom messages
	config2 = StaticaConfig.create(
		min_length_error_message="Custom min length",
		max_value_error_message="Custom max value",
	)
	assert config2.min_length_error_message == "Custom min length"
	assert config2.max_value_error_message == "Custom max value"
	assert config2.type_error_message == "expected type '{expected_type}', got '{found_type}'"


def test_config_immutability() -> None:
	"""Test that StaticaConfig instances are immutable (frozen dataclass)."""

	config = StaticaConfig.create(type_error_message="Custom message")

	# Should not be able to modify frozen dataclass
	with pytest.raises(AttributeError):
		config.type_error_message = "Modified message"  # type: ignore[misc]
