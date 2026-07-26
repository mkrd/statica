import unittest
from typing import Literal

from statica import Statica
from statica.core import Field, FieldDescriptor

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 50
AGE_MIN_VALUE = 0
AGE_MAX_VALUE = 120


class TestDescriptor(unittest.TestCase):
	def test_descriptor(self) -> None:
		class TestSubclass(Statica):
			x: int = Field()
			y: int = Field()

		class Test(Statica):
			data: str = Field()
			data_optional: int | None
			sub: TestSubclass = Field()

		d_data = Test.data

		self.assertIsInstance(d_data, FieldDescriptor)
		self.assertEqual(d_data.name, "data")
		self.assertIs(d_data.owner, Test)
		self.assertIs(d_data.expected_type, str)
		self.assertEqual(set(d_data.sub_types), {str})
		self.assertIsNone(d_data.statica_sub_class)

		d_data_optional = Test.data_optional
		self.assertIsInstance(d_data_optional, FieldDescriptor)
		self.assertIs(d_data_optional.owner, Test)
		self.assertEqual(d_data_optional.expected_type, int | None)
		self.assertEqual(set(d_data_optional.sub_types), {int, type(None)})
		self.assertIsNone(d_data_optional.statica_sub_class)

		d_sub = Test.sub
		self.assertIsInstance(d_sub, FieldDescriptor)
		self.assertEqual(d_sub.name, "sub")
		self.assertIs(d_sub.owner, Test)
		self.assertIs(d_sub.expected_type, TestSubclass)
		self.assertEqual(set(d_sub.sub_types), {TestSubclass})
		self.assertIs(d_sub.statica_sub_class, TestSubclass)
		self.assertIsNotNone(d_sub.statica_sub_class)

	def test_descriptor_generic_list(self) -> None:
		"""Test descriptor metadata for list[int] field."""

		class Model(Statica):
			items: list[int] = Field()

		d = Model.items
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(d.name, "items")
		self.assertEqual(d.expected_type, list[int])
		self.assertIsNone(d.statica_sub_class)

	def test_descriptor_generic_dict(self) -> None:
		"""Test descriptor metadata for dict[str, int] field."""

		class Model(Statica):
			data: dict[str, int] = Field()

		d = Model.data
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(d.name, "data")
		self.assertEqual(d.expected_type, dict[str, int])
		self.assertIsNone(d.statica_sub_class)

	def test_descriptor_literal(self) -> None:
		"""Test descriptor metadata for Literal field."""

		class Model(Statica):
			status: Literal["active", "inactive"]

		d = Model.status
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(d.name, "status")
		self.assertIsNone(d.statica_sub_class)

	def test_descriptor_optional_statica_subclass(self) -> None:
		"""Test descriptor identifies Statica subclass in optional union."""

		class Inner(Statica):
			value: str

		class Outer(Statica):
			inner: Inner | None = Field()

		d = Outer.inner
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(d.expected_type, Inner | None)
		self.assertEqual(set(d.sub_types), {Inner, type(None)})
		self.assertIs(d.statica_sub_class, Inner)

	def test_descriptor_constraint_metadata(self) -> None:
		"""Test descriptor stores constraint metadata correctly."""

		class Model(Statica):
			name: str = Field(
				min_length=NAME_MIN_LENGTH,
				max_length=NAME_MAX_LENGTH,
				strip_whitespace=True,
			)
			age: int = Field(min_value=AGE_MIN_VALUE, max_value=AGE_MAX_VALUE)

		d_name = Model.name
		self.assertIsInstance(d_name, FieldDescriptor)
		self.assertEqual(d_name.min_length, NAME_MIN_LENGTH)
		self.assertEqual(d_name.max_length, NAME_MAX_LENGTH)
		self.assertTrue(d_name.strip_whitespace)
		self.assertIsNone(d_name.min_value)
		self.assertIsNone(d_name.max_value)

		d_age = Model.age
		self.assertIsInstance(d_age, FieldDescriptor)
		self.assertEqual(d_age.min_value, AGE_MIN_VALUE)
		self.assertEqual(d_age.max_value, AGE_MAX_VALUE)
		self.assertIsNone(d_age.min_length)
		self.assertIsNone(d_age.max_length)

	def test_descriptor_cast_to_metadata(self) -> None:
		"""Test descriptor stores cast_to callable."""

		class Model(Statica):
			num: int = Field(cast_to=int)

		d = Model.num
		self.assertIsInstance(d, FieldDescriptor)
		self.assertIs(d.cast_to, int)

	def test_descriptor_alias_metadata(self) -> None:
		"""Test descriptor stores alias."""

		class Model(Statica):
			full_name: str = Field(alias="fullName")

		d = Model.full_name
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(d.alias, "fullName")

	def test_descriptor_default_metadata(self) -> None:
		"""Test descriptor stores default values."""

		class Model(Statica):
			name: str = Field(default="unknown")
			count: int = Field(default=0)
			tags: list[str] = Field(default=[])

		d_name = Model.name
		d_count = Model.count
		d_tags = Model.tags
		self.assertIsInstance(d_name, FieldDescriptor)
		self.assertIsInstance(d_count, FieldDescriptor)
		self.assertIsInstance(d_tags, FieldDescriptor)
		self.assertEqual(d_name.default, "unknown")
		self.assertEqual(d_count.default, 0)
		self.assertEqual(d_tags.default, [])

	def test_descriptor_auto_created_without_field(self) -> None:
		"""Test that bare annotations get auto-wrapped in FieldDescriptor."""

		class Model(Statica):
			name: str

		d = Model.name
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(d.name, "name")
		self.assertIs(d.expected_type, str)
		self.assertIsNone(d.default)
		self.assertIsNone(d.min_length)
		self.assertIsNone(d.cast_to)
		self.assertIsNone(d.alias)

	def test_descriptor_complex_union(self) -> None:
		"""Test descriptor with multi-type union."""

		class Model(Statica):
			value: int | float | str | None

		d = Model.value
		self.assertIsInstance(d, FieldDescriptor)
		self.assertEqual(set(d.sub_types), {int, float, str, type(None)})
		self.assertIsNone(d.statica_sub_class)
