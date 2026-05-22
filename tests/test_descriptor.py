from typing import Literal

from statica import Statica
from statica.core import Field, FieldDescriptor

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 50
AGE_MIN_VALUE = 0
AGE_MAX_VALUE = 120


def test_descriptor() -> None:
	class TestSubclass(Statica):
		x: int = Field()
		y: int = Field()

	class Test(Statica):
		data: str = Field()
		data_optional: int | None
		sub: TestSubclass = Field()

	d_data = Test.data

	assert isinstance(d_data, FieldDescriptor)
	assert d_data.name == "data"
	assert d_data.owner is Test
	assert d_data.expected_type is str
	assert set(d_data.sub_types) == {str}
	assert d_data.statica_sub_class is None

	d_data_optional = Test.data_optional
	assert isinstance(d_data_optional, FieldDescriptor)
	assert d_data_optional.owner is Test
	assert d_data_optional.expected_type == int | None
	assert set(d_data_optional.sub_types) == {int, type(None)}
	assert d_data_optional.statica_sub_class is None

	d_sub = Test.sub
	assert isinstance(d_sub, FieldDescriptor)
	assert d_sub.name == "sub"
	assert d_sub.owner is Test
	assert d_sub.expected_type is TestSubclass
	assert set(d_sub.sub_types) == {TestSubclass}
	assert d_sub.statica_sub_class is TestSubclass
	assert d_sub.statica_sub_class is not None


def test_descriptor_generic_list() -> None:
	"""Test descriptor metadata for list[int] field."""

	class Model(Statica):
		items: list[int] = Field()

	d = Model.items
	assert isinstance(d, FieldDescriptor)
	assert d.name == "items"
	assert d.expected_type == list[int]
	assert d.statica_sub_class is None


def test_descriptor_generic_dict() -> None:
	"""Test descriptor metadata for dict[str, int] field."""

	class Model(Statica):
		data: dict[str, int] = Field()

	d = Model.data
	assert isinstance(d, FieldDescriptor)
	assert d.name == "data"
	assert d.expected_type == dict[str, int]
	assert d.statica_sub_class is None


def test_descriptor_literal() -> None:
	"""Test descriptor metadata for Literal field."""

	class Model(Statica):
		status: Literal["active", "inactive"]

	d = Model.status
	assert isinstance(d, FieldDescriptor)
	assert d.name == "status"
	assert d.statica_sub_class is None


def test_descriptor_optional_statica_subclass() -> None:
	"""Test descriptor identifies Statica subclass in optional union."""

	class Inner(Statica):
		value: str

	class Outer(Statica):
		inner: Inner | None = Field()

	d = Outer.inner
	assert isinstance(d, FieldDescriptor)
	assert d.expected_type == Inner | None
	assert set(d.sub_types) == {Inner, type(None)}
	assert d.statica_sub_class is Inner


def test_descriptor_constraint_metadata() -> None:
	"""Test descriptor stores constraint metadata correctly."""

	class Model(Statica):
		name: str = Field(
			min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH, strip_whitespace=True,
		)
		age: int = Field(min_value=AGE_MIN_VALUE, max_value=AGE_MAX_VALUE)

	d_name = Model.name
	assert isinstance(d_name, FieldDescriptor)
	assert d_name.min_length == NAME_MIN_LENGTH
	assert d_name.max_length == NAME_MAX_LENGTH
	assert d_name.strip_whitespace is True
	assert d_name.min_value is None
	assert d_name.max_value is None

	d_age = Model.age
	assert isinstance(d_age, FieldDescriptor)
	assert d_age.min_value == AGE_MIN_VALUE
	assert d_age.max_value == AGE_MAX_VALUE
	assert d_age.min_length is None
	assert d_age.max_length is None


def test_descriptor_cast_to_metadata() -> None:
	"""Test descriptor stores cast_to callable."""

	class Model(Statica):
		num: int = Field(cast_to=int)

	d = Model.num
	assert isinstance(d, FieldDescriptor)
	assert d.cast_to is int


def test_descriptor_alias_metadata() -> None:
	"""Test descriptor stores alias."""

	class Model(Statica):
		full_name: str = Field(alias="fullName")

	d = Model.full_name
	assert isinstance(d, FieldDescriptor)
	assert d.alias == "fullName"


def test_descriptor_default_metadata() -> None:
	"""Test descriptor stores default values."""

	class Model(Statica):
		name: str = Field(default="unknown")
		count: int = Field(default=0)
		tags: list[str] = Field(default=[])

	d_name = Model.name
	d_count = Model.count
	d_tags = Model.tags
	assert isinstance(d_name, FieldDescriptor)
	assert isinstance(d_count, FieldDescriptor)
	assert isinstance(d_tags, FieldDescriptor)
	assert d_name.default == "unknown"
	assert d_count.default == 0
	assert d_tags.default == []


def test_descriptor_auto_created_without_field() -> None:
	"""Test that bare annotations get auto-wrapped in FieldDescriptor."""

	class Model(Statica):
		name: str

	d = Model.name
	assert isinstance(d, FieldDescriptor)
	assert d.name == "name"
	assert d.expected_type is str
	assert d.default is None
	assert d.min_length is None
	assert d.cast_to is None
	assert d.alias is None


def test_descriptor_complex_union() -> None:
	"""Test descriptor with multi-type union."""

	class Model(Statica):
		value: int | float | str | None

	d = Model.value
	assert isinstance(d, FieldDescriptor)
	assert set(d.sub_types) == {int, float, str, type(None)}
	assert d.statica_sub_class is None
