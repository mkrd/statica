import unittest

from statica.core import ConstraintValidationError, Field, Statica, TypeValidationError


class TestStatica(unittest.TestCase):
	def test_different_field_syntax_variations(self) -> None:
		class StringTestSyntax1(Statica):
			name: str

		class StringTestSyntax3(Statica):
			name: str = Field()

		for cls in (StringTestSyntax1, StringTestSyntax3):
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
		if instance.inner is None:
			self.fail("inner was not built from the dict")
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

	def test_reused_field_object(self) -> None:
		non_empty = Field(min_length=1)

		class First(Statica):
			title: str = non_empty
			label: str = non_empty

		class Second(Statica):
			count: list[int] = non_empty

		self.assertEqual(First(title="a", label="b").to_dict(), {"title": "a", "label": "b"})
		self.assertEqual(Second(count=[1]).to_dict(), {"count": [1]})

		# Each field keeps its own type and the shared constraint
		with self.assertRaises(TypeValidationError):
			First(title=1, label="b")  # type: ignore[arg-type]
		with self.assertRaises(ConstraintValidationError):
			Second(count=[])
