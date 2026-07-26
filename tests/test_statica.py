import unittest

from statica.core import ConstraintValidationError, Field, Statica, TypeValidationError


class TestStatica(unittest.TestCase):
	def test_basic_syntax(self) -> None:
		class RequiredStr(Statica):
			name: str

		i1 = RequiredStr.from_map({"name": "Test"})
		self.assertEqual(i1.name, "Test")

		i1 = RequiredStr(name="Test")
		self.assertEqual(i1.name, "Test")

		with self.assertRaises(TypeValidationError):
			RequiredStr.from_map({})

		with self.assertRaises(TypeValidationError):
			RequiredStr.from_map({"name": 123})

		class OptionalStr(Statica):
			name: str | None

		i2 = OptionalStr.from_map({"name": "Test"})
		self.assertEqual(i2.name, "Test")
		i2 = OptionalStr.from_map({"name": None})
		self.assertIsNone(i2.name)
		i2 = OptionalStr.from_map({})
		self.assertIsNone(i2.name)
		with self.assertRaises(TypeValidationError):
			OptionalStr.from_map({"name": 123})

	def test_different_field_syntax_variations(self) -> None:
		class StringTestSyntax1(Statica):
			name: str

		class StringTestSyntax2(Statica):
			name: str

		class StringTestSyntax3(Statica):
			name: str = Field()

		for cls in (StringTestSyntax1, StringTestSyntax2, StringTestSyntax3):
			instance = cls.from_map({"name": "Test"})

			self.assertEqual(getattr(instance, "name", None), "Test")

			with self.assertRaises(TypeValidationError):
				cls.from_map({})

			with self.assertRaises(TypeValidationError):
				cls.from_map({"name": 123})

	def test_required_string_field(self) -> None:
		class StringTest(Statica):
			name: str

		instance = StringTest(name="Test")
		self.assertEqual(instance.name, "Test")

		instance = StringTest.from_map({"name": "Test"})
		self.assertEqual(instance.name, "Test")

		with self.assertRaises(TypeValidationError):
			StringTest.from_map({})

		with self.assertRaises(TypeValidationError):
			StringTest.from_map({"name": 123})

		with self.assertRaises(TypeValidationError):
			StringTest.from_map({"name": None})

	def test_optional_string_field(self) -> None:
		class StringTest(Statica):
			name: str | None

		instance = StringTest.from_map({"name": "Test"})
		self.assertEqual(instance.name, "Test")

		instance = StringTest.from_map({"name": None})
		self.assertIsNone(instance.name)

		instance = StringTest.from_map({})
		self.assertIsNone(instance.name)

		with self.assertRaises(TypeValidationError):
			StringTest.from_map({"name": 123})

	def test_string_field_with_length_constraints(self) -> None:
		class StringTest(Statica):
			name: str = Field(min_length=3, max_length=5)

		instance = StringTest.from_map({"name": "Test"})
		self.assertEqual(instance.name, "Test")

		with self.assertRaises(ConstraintValidationError) as cm:
			StringTest.from_map({"name": "Te"})
		self.assertIn("length must be at least 3", str(cm.exception))

		with self.assertRaises(ConstraintValidationError) as cm:
			StringTest.from_map({"name": "Testing"})
		self.assertIn("length must be at most 5", str(cm.exception))

	def test_string_field_with_whitespace_stripping(self) -> None:
		class StringTest(Statica):
			name: str = Field(strip_whitespace=True, max_length=4)

		instance = StringTest.from_map({"name": " Test "})
		self.assertEqual(instance.name, "Test")

		with self.assertRaises(ConstraintValidationError) as cm:
			StringTest.from_map({"name": " TestLong "})
		self.assertIn("length must be at most 4", str(cm.exception))

	def test_integer_field_with_value_constraints(self) -> None:
		class IntTest(Statica):
			num: int = Field(min_value=1, max_value=10)

		num = 5

		instance = IntTest.from_map({"num": num})
		self.assertEqual(instance.num, num)

		with self.assertRaises(ConstraintValidationError) as cm:
			IntTest.from_map({"num": 0})
		self.assertIn("must be at least 1", str(cm.exception))

		with self.assertRaises(ConstraintValidationError) as cm:
			IntTest.from_map({"num": 11})
		self.assertIn("must be at most 10", str(cm.exception))

	def test_custom_error_class(self) -> None:
		class CustomError(Exception):
			pass

		class IntTest(Statica):
			constraint_error_class = CustomError

			num: int = Field(min_value=1, max_value=10)

		with self.assertRaises(CustomError) as cm:
			IntTest.from_map({"num": 0})
		self.assertIn("must be at least 1", str(cm.exception))

		class FloatTest(Statica):
			num: float = Field(min_value=1, max_value=10)

		num_float = 5.5

		instance = FloatTest.from_map({"num": num_float})
		self.assertEqual(instance.num, num_float)

		with self.assertRaises(TypeValidationError):
			FloatTest.from_map({"num": "4"})

	def test_cast(self) -> None:
		class IntTest(Statica):
			num: int = Field(cast_to=int)

		num_int = 5
		num_str = str(num_int)

		instance = IntTest.from_map({"num": num_str})
		self.assertEqual(instance.num, num_int)

		with self.assertRaises(TypeValidationError):
			IntTest.from_map({"num": "5.5"})

	def test_nested_from_map(self) -> None:
		class Inner(Statica):
			value: str

		class Outer(Statica):
			inner: Inner
			other: str

		instance = Outer.from_map({"inner": {"value": "Test"}, "other": "Other"})
		self.assertEqual(instance.inner.value, "Test")

		with self.assertRaises(TypeValidationError):
			Outer.from_map({"inner": {"value": 123}})

	def test_nested_from_map_optional(self) -> None:
		class Inner(Statica):
			value: str | None

		class Outer(Statica):
			inner: Inner | None
			other: str

		instance = Outer.from_map({"inner": {"value": "Test"}, "other": "Other"})

		if instance.inner is not None:
			self.assertEqual(instance.inner.value, "Test")

		instance = Outer.from_map({"inner": None, "other": "Other"})
		self.assertIsNone(instance.inner)

		with self.assertRaises(TypeValidationError):
			Outer.from_map({"inner": {"value": 123}})

	def test_class_without_fields(self) -> None:
		class Empty(Statica):
			pass

		instance = Empty.from_map({})
		self.assertIsInstance(instance, Empty)
		self.assertEqual(instance.to_dict(), {})

		instance = Empty()
		self.assertEqual(instance.to_dict(), {})
