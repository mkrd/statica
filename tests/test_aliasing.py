import unittest

from statica.core import Field, Statica, TypeValidationError
from statica.exceptions import ConstraintValidationError

INTEGER = 42
FLOAT = 19.99
STRING = "test string"


class TestAliasing(unittest.TestCase):
	def test_basic_alias(self) -> None:
		class AliasTest(Statica):
			full_name: str = Field(alias="fullName")
			age: int = Field(alias="userAge")

		# Test parsing with alias
		data = {"fullName": "John Doe", "userAge": INTEGER}
		instance = AliasTest.from_map(data)
		self.assertEqual(instance.full_name, "John Doe")
		self.assertEqual(instance.age, INTEGER)
		self.assertEqual(instance.to_dict(), data)

		# Test that original field names don't work when alias is used
		with self.assertRaises(TypeValidationError):
			AliasTest.from_map({"full_name": "John Doe", "age": INTEGER})

	def test_alias_with_optional_fields(self) -> None:
		"""Test aliases with optional fields."""

		class OptionalAliasTest(Statica):
			required_field: str = Field(alias="reqField")
			optional_field: str | None = Field(alias="optField")

		# Test with both fields provided
		instance = OptionalAliasTest.from_map({"reqField": "required", "optField": "optional"})
		self.assertEqual(instance.required_field, "required")
		self.assertEqual(instance.optional_field, "optional")

		# Test with only required field
		instance = OptionalAliasTest.from_map({"reqField": "required"})
		self.assertEqual(instance.required_field, "required")
		self.assertIsNone(instance.optional_field)

		# Test missing required field should still raise error
		with self.assertRaises(TypeValidationError):
			OptionalAliasTest.from_map({"optField": "optional"})

	def test_alias_with_constraints(self) -> None:
		"""Test that aliases work with field constraints."""

		class ConstraintAliasTest(Statica):
			name: str = Field(alias="userName", min_length=3, max_length=10, strip_whitespace=True)
			score: int = Field(alias="userScore", min_value=0, max_value=100)

		# Test valid values
		instance = ConstraintAliasTest.from_map({"userName": " Alice ", "userScore": INTEGER})
		self.assertEqual(instance.name, "Alice")  # Whitespace should be stripped
		self.assertEqual(instance.score, INTEGER)

		# Test constraint violations with aliases
		with self.assertRaises(ConstraintValidationError):  # Should be ConstraintValidationError
			ConstraintAliasTest.from_map({"userName": "Al", "userScore": INTEGER})  # Too short

		with self.assertRaises(ConstraintValidationError):  # Should be ConstraintValidationError
			ConstraintAliasTest.from_map({"userName": "Alice", "userScore": 150})  # Too high

	def test_alias_with_casting(self) -> None:
		"""Test that aliases work with type casting."""

		class CastAliasTest(Statica):
			number: int = Field(alias="numStr", cast_to=int)
			price: float = Field(alias="priceStr", cast_to=float)

		instance = CastAliasTest.from_map({"numStr": "42", "priceStr": "19.99"})
		self.assertEqual(instance.number, INTEGER)
		self.assertEqual(instance.price, FLOAT)

	def test_mixed_alias_and_no_alias(self) -> None:
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
		self.assertEqual(instance.normal_field, "normal")
		self.assertEqual(instance.aliased_field, "aliased")
		self.assertEqual(instance.another_normal, INTEGER)

	def test_alias_serialization(self) -> None:
		class SerializationTest(Statica):
			field_name: str = Field(alias="serialAlias")

		instance = SerializationTest(field_name=STRING)

		self.assertEqual(instance.to_dict(), {"serialAlias": STRING})
		self.assertEqual(instance.to_dict(with_aliases=False), {"field_name": STRING})

	def test_empty_alias_mapping(self) -> None:
		"""Test behavior when no matching aliases are found in the mapping."""

		class EmptyMappingTest(Statica):
			field_name: str = Field(alias="expectedAlias")

		# Should raise TypeValidationError when the aliased field is missing
		with self.assertRaises(TypeValidationError):
			EmptyMappingTest.from_map({"wrongAlias": "value"})

		# Should raise a TypeValidationError when the original field name is used
		with self.assertRaises(TypeValidationError):
			EmptyMappingTest.from_map({"field_name": "value"})

	def test_aliasing_with_nested_statica(self) -> None:
		"""Test aliasing with nested Statica objects."""

		class NestedStatica(Statica):
			nested_field: str = Field(alias="nestedField")

		class AliasNestedTest(Statica):
			nested: NestedStatica = Field(alias="nestedObject")

		data = {
			"nestedObject": {"nestedField": "nested value"},
		}

		instance = AliasNestedTest.from_map(data)
		self.assertEqual(instance.nested.nested_field, "nested value")
		self.assertEqual(instance.to_dict(), data)
		self.assertEqual(
			instance.to_dict(with_aliases=False),
			{"nested": {"nested_field": "nested value"}},
		)
