from statica import Statica
from statica.core import Field, FieldDescriptor


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
