import unittest

from statica import ConstraintValidationError, Field, Statica, TypeValidationError
from statica.config import StaticaConfig


class TestConfig(unittest.TestCase):
	def test_default_config_error_messages(self) -> None:
		"""Test that default error messages are used when no custom config is provided."""

		class DefaultTest(Statica):
			name: str = Field(min_length=3)
			age: int = Field(min_value=18, max_value=65)

		# Test type error with default message
		with self.assertRaises(TypeValidationError) as cm:
			DefaultTest.from_map({"name": "John", "age": "not_int"})
		self.assertIn("expected type 'int', got 'str'", str(cm.exception))

		# Test constraint error with default message (path-prefixed)
		with self.assertRaises(ConstraintValidationError) as cm:
			DefaultTest(name="Jo", age=25)
		self.assertIn("DefaultTest.name: length must be at least 3", str(cm.exception))

		with self.assertRaises(ConstraintValidationError) as cm:
			DefaultTest(name="John Doe", age=17)
		self.assertIn("DefaultTest.age: must be at least 18", str(cm.exception))

	def test_custom_config_type_error_message(self) -> None:
		"""Test custom type error message configuration."""

		custom_config = StaticaConfig.create(
			type_error_message="{found_type} is not {expected_type}",
		)

		class CustomTypeErrorTest(Statica, config=custom_config):
			name: str
			age: int

		with self.assertRaises(TypeValidationError) as cm:
			CustomTypeErrorTest.from_map({"name": "John", "age": "x"})
		self.assertIn("str is not int", str(cm.exception))

		with self.assertRaises(TypeValidationError) as cm:
			CustomTypeErrorTest.from_map({"name": 123, "age": 30})
		self.assertIn("int is not str", str(cm.exception))

	def test_custom_config_length_error_messages(self) -> None:
		"""Test custom length constraint error messages."""

		custom_config = StaticaConfig.create(
			min_length_error_message="{field_name} < {min_length}",
			max_length_error_message="{field_name} < {max_length}",
		)

		class CustomLengthErrorTest(Statica, config=custom_config):
			username: str = Field(min_length=3, max_length=10)
			description: str = Field(max_length=50)

		# Test min length error
		with self.assertRaises(ConstraintValidationError) as cm:
			CustomLengthErrorTest(username="ab", description="Valid description")
		self.assertIn("username < 3", str(cm.exception))

		# Test max length error
		with self.assertRaises(ConstraintValidationError) as cm:
			CustomLengthErrorTest(username="validuser", description="a" * 51)
		self.assertIn("description < 50", str(cm.exception))

	def test_custom_config_value_error_messages(self) -> None:
		"""Test custom value constraint error messages."""

		custom_config = StaticaConfig.create(
			min_value_error_message="{field_name} < {min_value}",
			max_value_error_message="{field_name} > {max_value}",
		)

		class CustomValueErrorTest(Statica, config=custom_config):
			age: int = Field(min_value=0, max_value=120)
			price: float = Field(min_value=0.01, max_value=999.99)

		# Test min value error
		with self.assertRaises(ConstraintValidationError) as cm:
			CustomValueErrorTest(age=-1, price=10.0)
		self.assertIn("age < 0", str(cm.exception))

		# Test max value error
		with self.assertRaises(ConstraintValidationError) as cm:
			CustomValueErrorTest(age=25, price=1000.0)
		self.assertIn("price > 999.99", str(cm.exception))

	def test_custom_config_with_from_map(self) -> None:
		"""Test that custom configuration works with from_map method."""

		custom_config = StaticaConfig.create(
			type_error_message="from_map error: expected {expected_type}, got {found_type}",
			min_length_error_message="from_map: {field_name} needs at least {min_length} chars",
		)

		class FromMapTest(Statica, config=custom_config):
			name: str = Field(min_length=5)
			age: int

		# Test type error via from_map
		with self.assertRaises(TypeValidationError) as cm:
			FromMapTest.from_map({"name": "Valid Name", "age": "not_int"})
		self.assertIn("from_map error: expected int, got str", str(cm.exception))

		# Test constraint error via from_map
		with self.assertRaises(ConstraintValidationError) as cm:
			FromMapTest.from_map({"name": "Jon", "age": 25})
		self.assertIn("from_map: name needs at least 5 chars", str(cm.exception))

	def test_custom_config_with_nested_statica(self) -> None:
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
		with self.assertRaises(TypeValidationError) as cm:
			OuterTest.from_map({"inner": {"value": 123}, "name": "Outer"})
		self.assertIn("Inner error: expected str, got int", str(cm.exception))

		# Test outer object error uses outer config
		with self.assertRaises(TypeValidationError) as cm:
			OuterTest.from_map({"inner": {"value": "inner"}, "name": 123})
		self.assertIn("Outer error: expected str, got int", str(cm.exception))

	def test_config_with_union_types(self) -> None:
		"""Test custom configuration with union types."""

		custom_config = StaticaConfig.create(
			type_error_message="Union error: expected one of {expected_type}, got {found_type}",
		)

		class UnionTest(Statica, config=custom_config):
			value: str | int
			optional_value: str | None = Field(min_length=3)

		# Test union type error
		with self.assertRaises(TypeValidationError) as cm:
			UnionTest.from_map({"value": 3.14, "optional_value": "test"})
		self.assertIn("Union error: expected one of", str(cm.exception))
		self.assertIn("got float", str(cm.exception))

	def test_config_with_list_and_dict_constraints(self) -> None:
		"""Test custom configuration with list and dict length constraints."""

		custom_config = StaticaConfig.create(
			min_length_error_message=(
				"Collection {field_name} must have at least {min_length} items"
			),
			max_length_error_message=(
				"Collection {field_name} can have at most {max_length} items"
			),
		)

		class CollectionTest(Statica, config=custom_config):
			tags: list[str] = Field(min_length=1, max_length=5)
			metadata: dict[str, str] = Field(min_length=1, max_length=3)

		# Test list length errors
		with self.assertRaises(ConstraintValidationError) as cm:
			CollectionTest(tags=[], metadata={"key": "value"})
		self.assertIn("Collection tags must have at least 1 items", str(cm.exception))

		with self.assertRaises(ConstraintValidationError) as cm:
			CollectionTest(tags=["a"] * 6, metadata={"key": "value"})
		self.assertIn("Collection tags can have at most 5 items", str(cm.exception))

		# Test dict length errors
		with self.assertRaises(ConstraintValidationError) as cm:
			CollectionTest(tags=["valid"], metadata={})
		self.assertIn("Collection metadata must have at least 1 items", str(cm.exception))

		with self.assertRaises(ConstraintValidationError) as cm:
			CollectionTest(tags=["valid"], metadata={f"key{i}": f"value{i}" for i in range(4)})
		self.assertIn("Collection metadata can have at most 3 items", str(cm.exception))

	def test_config_create_method_defaults(self) -> None:
		"""Test that StaticaConfig.create() method works with partial parameters."""

		# Test with only one custom message
		config1 = StaticaConfig.create(type_error_message="Custom type error")
		self.assertEqual(config1.type_error_message, "Custom type error")
		self.assertEqual(
			config1.min_length_error_message,
			"length must be at least {min_length}",
		)

		# Test with multiple custom messages
		config2 = StaticaConfig.create(
			min_length_error_message="Custom min length",
			max_value_error_message="Custom max value",
		)
		self.assertEqual(config2.min_length_error_message, "Custom min length")
		self.assertEqual(config2.max_value_error_message, "Custom max value")
		self.assertEqual(
			config2.type_error_message,
			"expected type '{expected_type}', got '{found_type}'",
		)

	def test_config_immutability(self) -> None:
		"""Test that StaticaConfig instances are immutable (frozen dataclass)."""

		config = StaticaConfig.create(type_error_message="Custom message")

		# Should not be able to modify frozen dataclass
		with self.assertRaises(AttributeError):
			config.type_error_message = "Modified message"  # type: ignore[misc]
