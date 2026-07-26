"""Tests for cast_to edge cases and failure scenarios."""

import unittest

from statica import Field, Statica, TypeValidationError
from statica.exceptions import ConstraintValidationError

CAST_INT_VALUE = 42
CAST_FLOAT_VALUE = 19.99
CAST_COUNT_50 = 50
CAST_PRICE = 29.99
CAST_DEFAULT = 10


class TestCastEdgeCases(unittest.TestCase):
	def test_cast_to_int_from_string(self) -> None:
		"""Test basic cast_to int from string."""

		class Model(Statica):
			count: int = Field(cast_to=int)

		instance = Model(count="42")  # type: ignore[arg-type]
		self.assertEqual(instance.count, CAST_INT_VALUE)

	def test_cast_to_float_from_string(self) -> None:
		"""Test basic cast_to float from string."""

		class Model(Statica):
			price: float = Field(cast_to=float)

		instance = Model(price="19.99")  # type: ignore[arg-type]
		self.assertEqual(instance.price, CAST_FLOAT_VALUE)

	def test_cast_to_str_from_int(self) -> None:
		"""Test cast_to str from int."""

		class Model(Statica):
			label: str = Field(cast_to=str)

		instance = Model(label=42)  # type: ignore[arg-type]
		self.assertEqual(instance.label, "42")

	def test_cast_to_set_from_list(self) -> None:
		"""Test cast_to set from list."""

		class Model(Statica):
			items: set[int] = Field(cast_to=set)

		instance = Model(items=[1, 2, 3, 2])  # type: ignore[arg-type]
		self.assertEqual(instance.items, {1, 2, 3})

	def test_cast_to_raises_on_unconvertible_value(self) -> None:
		"""Test that cast_to raises when conversion fails (e.g. int('abc'))."""

		class Model(Statica):
			count: int = Field(cast_to=int)

		with self.assertRaises(TypeValidationError):
			Model(count="not_a_number")  # type: ignore[arg-type]

	def test_cast_to_raises_on_float_string_to_int(self) -> None:
		"""Test that int('3.14') raises."""

		class Model(Statica):
			count: int = Field(cast_to=int)

		with self.assertRaises(TypeValidationError):
			Model(count="3.14")  # type: ignore[arg-type]

	def test_cast_to_with_none_on_required_field(self) -> None:
		"""Test cast_to with None when field is required (not optional)."""

		class Model(Statica):
			count: int = Field(cast_to=int)

		with self.assertRaises((TypeValidationError, TypeError)):
			Model(count=None)  # type: ignore[arg-type]

	def test_cast_to_with_none_on_optional_field(self) -> None:
		"""Test cast_to with None on optional field (None should be passed through)."""

		class Model(Statica):
			count: int | None = Field(cast_to=int)

		# Casting None to int raises TypeError, which gets caught
		with self.assertRaises((TypeValidationError, TypeError)):
			Model(count=None)

	def test_cast_to_with_constraints(self) -> None:
		"""Test that cast_to is applied before constraint validation."""

		class Model(Statica):
			count: int = Field(cast_to=int, min_value=0, max_value=100)

		instance = Model(count="50")  # type: ignore[arg-type]
		self.assertEqual(instance.count, CAST_COUNT_50)

		# Cast succeeds but constraint fails
		with self.assertRaises(ConstraintValidationError):
			Model(count="150")  # type: ignore[arg-type]

	def test_cast_to_with_custom_callable(self) -> None:
		"""Test cast_to with a custom function."""

		def parse_bool(value: str) -> bool:
			return value.lower() in ("true", "1", "yes")

		class Model(Statica):
			enabled: bool = Field(cast_to=parse_bool)

		instance = Model(enabled="true")  # type: ignore[arg-type]
		self.assertTrue(instance.enabled)

		instance2 = Model(enabled="yes")  # type: ignore[arg-type]
		self.assertTrue(instance2.enabled)

		instance3 = Model(enabled="no")  # type: ignore[arg-type]
		self.assertFalse(instance3.enabled)

	def test_cast_to_from_map(self) -> None:
		"""Test that cast_to works with from_map."""

		class Model(Statica):
			price: float = Field(cast_to=float)

		instance = Model.from_map({"price": "29.99"})
		self.assertEqual(instance.price, CAST_PRICE)

	def test_cast_to_with_alias(self) -> None:
		"""Test cast_to combined with alias."""

		class Model(Statica):
			count: int = Field(cast_to=int, alias="itemCount")

		instance = Model.from_map({"itemCount": "42"})
		self.assertEqual(instance.count, CAST_INT_VALUE)

	def test_cast_to_with_default(self) -> None:
		"""Test cast_to with default value (default should still be validated)."""

		class Model(Statica):
			count: int = Field(default=CAST_DEFAULT, cast_to=int)

		instance = Model()
		self.assertEqual(instance.count, CAST_DEFAULT)

		instance2 = Model(count="42")  # type: ignore[arg-type]
		self.assertEqual(instance2.count, CAST_INT_VALUE)

	def test_cast_to_already_correct_type(self) -> None:
		"""Test cast_to when value already has the target type."""

		class Model(Statica):
			count: int = Field(cast_to=int)

		instance = Model(count=CAST_INT_VALUE)
		self.assertEqual(instance.count, CAST_INT_VALUE)

	def test_cast_to_list_from_tuple(self) -> None:
		"""Test cast_to list from tuple."""

		class Model(Statica):
			items: list[int] = Field(cast_to=list)

		instance = Model(items=(1, 2, 3))  # type: ignore[arg-type]
		self.assertEqual(instance.items, [1, 2, 3])

	def test_cast_to_bool_from_int(self) -> None:
		"""Test cast_to bool from int."""

		class Model(Statica):
			active: bool = Field(cast_to=bool)

		instance = Model(active=1)  # type: ignore[arg-type]
		self.assertTrue(instance.active)

		instance2 = Model(active=0)  # type: ignore[arg-type]
		self.assertFalse(instance2.active)
