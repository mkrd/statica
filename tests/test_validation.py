import unittest
from typing import Any, Literal

from statica import Field, Statica, TypeValidationError


class TestValidation(unittest.TestCase):
	def test_dict_as_field(self) -> None:
		class DictTest(Statica):
			data: dict[str, Any]

		test_dict = {"key1": 1, "key2": 2}

		i1 = DictTest.from_map({"data": test_dict})
		self.assertEqual(i1.data, test_dict)

		with self.assertRaises(TypeValidationError):
			DictTest.from_map({"data": "not a dict"})

		class TypedDictTest(Statica):
			data: dict[str, int]

		i2 = TypedDictTest.from_map({"data": test_dict})
		self.assertEqual(i2.data, test_dict)

		with self.assertRaises(TypeValidationError):
			TypedDictTest.from_map({"data": {"key1": "not an int"}})

	def test_dict_as_field_typed(self) -> None:
		class TypedDictTest(Statica):
			data: dict[str, int]

		test_dict = {"key1": 1, "key2": 2}

		i2 = TypedDictTest.from_map({"data": test_dict})
		self.assertEqual(i2.data, test_dict)

		class TypedDictTest2(Statica):
			data: dict[str, int | None]

		test_dict2 = {"key1": 1, "key2": None}

		i3 = TypedDictTest2.from_map({"data": test_dict2})
		self.assertEqual(i3.data, test_dict2)

	def test_list_as_field(self) -> None:
		class ListTest(Statica):
			items: list[int]

		test_list = [1, 2, 3]

		i1 = ListTest.from_map({"items": test_list})
		self.assertEqual(i1.items, test_list)

		with self.assertRaises(TypeValidationError):
			ListTest.from_map({"items": "not a list"})

		with self.assertRaises(TypeValidationError):
			ListTest.from_map({"items": [1, "not an int"]})

	def test_list_as_field_optional(self) -> None:
		class ListTest(Statica):
			items: list[int | None]

		test_list = [1, 2, None]

		i1 = ListTest.from_map({"items": test_list})
		self.assertEqual(i1.items, test_list)

	def test_set_as_field(self) -> None:
		class SetTest(Statica):
			items: set[int]

		test_set = {1, 2, 3}

		self.assertEqual(SetTest.from_map({"items": test_set}).items, test_set)

		with self.assertRaises(TypeValidationError):
			SetTest.from_map({"items": "not a set"})

		class SetTestCast(Statica):
			items: set[int] = Field(cast_to=set)

		test_list = [4, 4, 5]

		self.assertEqual(SetTestCast.from_map({"items": test_list}).items, set(test_list))

		with self.assertRaises(TypeValidationError):
			SetTest.from_map({"items": "not a set"})

	def test_validate_frozenset(self) -> None:
		class FrozensetModel(Statica):
			data: frozenset[int]

		instance = FrozensetModel(data=frozenset([1, 2, 3]))
		self.assertEqual(instance.data, frozenset([1, 2, 3]))

		with self.assertRaises(TypeValidationError):
			FrozensetModel(data=frozenset(["a", "b"]))  # type: ignore[arg-type]

		with self.assertRaises(TypeValidationError):
			FrozensetModel(data=[1, 2, 3])  # type: ignore[arg-type]

	def test_validate_literal(self) -> None:
		class LiteralTest(Statica):
			data: Literal["a", "b", "c"]
			number: Literal[1, 2, 3]

		i1 = LiteralTest.from_map({"data": "a", "number": 1})
		self.assertEqual(i1.data, "a")
		self.assertEqual(i1.number, 1)

		with self.assertRaises(TypeValidationError):
			LiteralTest.from_map({"data": "d", "number": 1})

		with self.assertRaises(TypeValidationError):
			LiteralTest.from_map({"data": "a", "number": 4})

	def test_validate_literal_optional(self) -> None:
		class LiteralTest(Statica):
			data: Literal["a", "b", "c"] | None
			number: Literal[1, 2, 3] | None

		i1 = LiteralTest.from_map({"data": "a", "number": 1})
		self.assertEqual(i1.data, "a")
		self.assertEqual(i1.number, 1)

		i2 = LiteralTest.from_map({"data": None, "number": None})
		self.assertIsNone(i2.data)
		self.assertIsNone(i2.number)

		with self.assertRaises(TypeValidationError):
			LiteralTest.from_map({"data": "d", "number": 1})

		with self.assertRaises(TypeValidationError):
			LiteralTest.from_map({"data": "a", "number": 4})
