import unittest

from statica import Field, Statica, TypeValidationError
from statica.config import StaticaConfig


class TestMissingField(unittest.TestCase):
	def test_missing_required_field_message(self) -> None:
		class User(Statica):
			age: int

		with self.assertRaises(TypeValidationError) as cm:
			User.from_map({})
		self.assertEqual(str(cm.exception), "age is required")

	def test_missing_required_field_custom_message(self) -> None:
		config = StaticaConfig.create(missing_field_error_message="Please provide {field_name}")

		class User(Statica, config=config):
			age: int

		with self.assertRaises(TypeValidationError) as cm:
			User.from_map({})
		self.assertEqual(str(cm.exception), "Please provide age")

	def test_missing_required_field_custom_error_class(self) -> None:
		class MyError(Exception):
			pass

		class User(Statica):
			type_error_class = MyError

			age: int

		with self.assertRaises(MyError):
			User.from_map({})

	def test_explicit_none_on_required_field_is_type_error(self) -> None:
		class User(Statica):
			age: int

		with self.assertRaises(TypeValidationError) as cm:
			User.from_map({"age": None})
		self.assertIn("expected type 'int', got 'NoneType'", str(cm.exception))

	def test_missing_nullable_field_is_none(self) -> None:
		class User(Statica):
			age: int | None

		self.assertIsNone(User.from_map({}).age)

	def test_missing_nullable_field_skips_cast(self) -> None:
		class User(Statica):
			age: int | None = Field(cast_to=int)

		self.assertIsNone(User.from_map({}).age)

	def test_missing_required_field_skips_cast(self) -> None:
		class User(Statica):
			age: int = Field(cast_to=int)

		with self.assertRaises(TypeValidationError) as cm:
			User.from_map({})
		self.assertEqual(str(cm.exception), "age is required")

	def test_default_none_is_a_default(self) -> None:
		class User(Statica):
			age: int | None = Field(default=None)
			name: str | None = None

		user = User()
		self.assertIsNone(user.age)
		self.assertIsNone(user.name)
