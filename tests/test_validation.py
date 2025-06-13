import pytest

from statica import Field, Statica, TypeValidationError


def test_dict_as_field() -> None:
	class DictTest(Statica):
		data: dict

	test_dict = {"key1": 1, "key2": 2}

	i1 = DictTest.from_map({"data": test_dict})
	assert i1.data == test_dict

	with pytest.raises(TypeValidationError):
		DictTest.from_map({"data": "not a dict"})

	class TypedDictTest(Statica):
		data: dict[str, int]

	i2 = TypedDictTest.from_map({"data": test_dict})
	assert i2.data == test_dict

	with pytest.raises(TypeValidationError):
		TypedDictTest.from_map({"data": {"key1": "not an int"}})


def test_dict_as_field_typed() -> None:
	class TypedDictTest(Statica):
		data: dict[str, int]

	test_dict = {"key1": 1, "key2": 2}

	i2 = TypedDictTest.from_map({"data": test_dict})
	assert i2.data == test_dict

	class TypedDictTest2(Statica):
		data: dict[str, int | None]

	test_dict2 = {"key1": 1, "key2": None}

	i3 = TypedDictTest2.from_map({"data": test_dict2})
	print(i3.data)
	assert i3.data == test_dict2


def test_list_as_field() -> None:
	class ListTest(Statica):
		items: list[int]

	test_list = [1, 2, 3]

	i1 = ListTest.from_map({"items": test_list})
	assert i1.items == test_list

	with pytest.raises(TypeValidationError):
		ListTest.from_map({"items": "not a list"})

	with pytest.raises(TypeValidationError):
		ListTest.from_map({"items": [1, "not an int"]})


def test_list_as_field_optional() -> None:
	class ListTest(Statica):
		items: list[int | None]

	test_list = [1, 2, None]

	i1 = ListTest.from_map({"items": test_list})
	assert i1.items == test_list


def test_set_as_field() -> None:
	class SetTest(Statica):
		items: set[int]

	test_set = {1, 2, 3}

	assert SetTest.from_map({"items": test_set}).items == test_set

	with pytest.raises(TypeValidationError):
		SetTest.from_map({"items": "not a set"})

	class SetTestCast(Statica):
		items: set[int] = Field(cast_to=set)

	test_list = [4, 4, 5]

	assert SetTestCast.from_map({"items": test_list}).items == set(test_list)

	with pytest.raises(TypeValidationError):
		SetTest.from_map({"items": "not a set"})


def test_validate_unsupported_generic_alias() -> None:
	class UnsupportedGeneric(Statica):
		data: frozenset[int]

	with pytest.raises(TypeValidationError):
		UnsupportedGeneric(data=frozenset([1, 2, 3]))
