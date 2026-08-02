"""Tests for full-path error context in validation errors."""

import unittest

from statica import ConstraintValidationError, Field, Statica, TypeValidationError


class TestErrorPaths(unittest.TestCase):
	def test_top_level_field_path(self) -> None:
		class User(Statica):
			age: int

		with self.assertRaises(TypeValidationError) as cm:
			User(age="old")  # type: ignore[arg-type]
		self.assertEqual(str(cm.exception), "User.age: expected type 'int', got 'str'")

	def test_nested_model_path(self) -> None:
		class Street(Statica):
			name: str

		class Address(Statica):
			street: Street

		class User(Statica):
			address: Address

		with self.assertRaises(TypeValidationError) as cm:
			User.from_map({"address": {"street": {"name": 123}}})
		self.assertEqual(
			str(cm.exception),
			"User.address.street.name: expected type 'str', got 'int'",
		)

	def test_list_index_path(self) -> None:
		class Model(Statica):
			items: list[int]

		with self.assertRaises(TypeValidationError) as cm:
			Model(items=[1, 2, "bad"])  # type: ignore[list-item]
		self.assertEqual(str(cm.exception), "Model.items[2]: expected type 'int', got 'str'")

	def test_tuple_index_path(self) -> None:
		class Model(Statica):
			pair: tuple[int, str]

		with self.assertRaises(TypeValidationError) as cm:
			Model(pair=(1, 2))  # type: ignore[arg-type]
		self.assertEqual(str(cm.exception), "Model.pair[1]: expected type 'str', got 'int'")

	def test_dict_value_path(self) -> None:
		class Model(Statica):
			meta: dict[str, int]

		with self.assertRaises(TypeValidationError) as cm:
			Model(meta={"count": "bad"})  # type: ignore[dict-item]
		self.assertEqual(str(cm.exception), "Model.meta['count']: expected type 'int', got 'str'")

	def test_dict_key_path(self) -> None:
		class Model(Statica):
			meta: dict[str, int]

		with self.assertRaises(TypeValidationError) as cm:
			Model(meta={5: 1})  # type: ignore[dict-item]
		self.assertIn("Model.meta.<key 5>", str(cm.exception))

	def test_set_element_path(self) -> None:
		class Model(Statica):
			tags: set[int]

		with self.assertRaises(TypeValidationError) as cm:
			Model(tags={"bad"})  # type: ignore[arg-type]
		self.assertIn("Model.tags{'bad'}", str(cm.exception))

	def test_union_summary(self) -> None:
		class Model(Statica):
			value: int | str

		with self.assertRaises(TypeValidationError) as cm:
			Model(value=3.14)  # type: ignore[arg-type]
		self.assertEqual(str(cm.exception), "Model.value: expected type 'int | str', got 'float'")

	def test_constraint_error_has_path(self) -> None:
		class Model(Statica):
			name: str = Field(min_length=3)

		with self.assertRaises(ConstraintValidationError) as cm:
			Model(name="ab")
		self.assertEqual(str(cm.exception), "Model.name: length must be at least 3")

	def test_nested_list_of_models_path(self) -> None:
		class Item(Statica):
			qty: int

		class Cart(Statica):
			items: list[Item]

		with self.assertRaises(TypeValidationError) as cm:
			Cart.from_map({"items": [{"qty": 1}, {"qty": "bad"}]})
		self.assertEqual(str(cm.exception), "Cart.items[1].qty: expected type 'int', got 'str'")


if __name__ == "__main__":
	unittest.main()
