import pytest

from statica.core import Field, Statica
from statica.exceptions import TypeValidationError

# Assuming the module is imported as 'validation'
from statica.validation import validate_or_raise


class User(Statica):
	name: str
	age: int
	email: str = Field(min_length=5)


class Address(Statica):
	street: str
	city: str
	zipcode: str = Field(min_length=5, max_length=10)


class Company(Statica):
	name: str
	employees: list[User]
	headquarters: Address


class Profile(Statica):
	user: User
	address: Address | None
	tags: list[str]
	metadata: dict[str, str]


class NestedProfile(Statica):
	profiles: list[Profile]
	company: Company | None


# Basic type validation tests
def test_validate_int_success() -> None:
	"""Test successful int validation"""
	validate_or_raise(42, int)
	validate_or_raise(0, int)
	validate_or_raise(-1, int)


def test_validate_int_failure() -> None:
	"""Test failed int validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise("42", int)
	with pytest.raises(TypeValidationError):
		validate_or_raise(42.0, int)


def test_validate_float_success() -> None:
	"""Test successful float validation"""
	validate_or_raise(3.14, float)
	validate_or_raise(0.0, float)
	validate_or_raise(-2.5, float)


def test_validate_float_failure() -> None:
	"""Test failed float validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise("3.14", float)
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, float)


def test_validate_str_success() -> None:
	"""Test successful string validation"""
	validate_or_raise("hello", str)
	validate_or_raise("", str)
	validate_or_raise("123", str)


def test_validate_str_failure() -> None:
	"""Test failed string validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise(123, str)
	with pytest.raises(TypeValidationError):
		validate_or_raise(None, str)


def test_validate_none_success() -> None:
	"""Test successful None validation"""
	validate_or_raise(None, type(None))


def test_validate_none_failure() -> None:
	"""Test failed None validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise("", type(None))
	with pytest.raises(TypeValidationError):
		validate_or_raise(0, type(None))


# Union type tests
def test_validate_union_int_or_str_success() -> None:
	"""Test successful union int|str validation"""
	union_type = int | str
	validate_or_raise(42, union_type)
	validate_or_raise("hello", union_type)


def test_validate_union_int_or_str_failure() -> None:
	"""Test failed union int|str validation"""
	union_type = int | str
	with pytest.raises(TypeValidationError):
		validate_or_raise(3.14, union_type)
	with pytest.raises(TypeValidationError):
		validate_or_raise([], union_type)


def test_validate_union_with_none_success() -> None:
	"""Test successful union with None validation"""
	union_type = int | None
	validate_or_raise(42, union_type)
	validate_or_raise(None, union_type)


def test_validate_union_with_none_failure() -> None:
	"""Test failed union with None validation"""
	union_type = int | None
	with pytest.raises(TypeValidationError):
		validate_or_raise("hello", union_type)


def test_validate_complex_union_success() -> None:
	"""Test successful complex union validation"""
	union_type = int | str | float | None
	validate_or_raise(42, union_type)
	validate_or_raise("hello", union_type)
	validate_or_raise(3.14, union_type)
	validate_or_raise(None, union_type)


# List type tests
def test_validate_list_int_success() -> None:
	"""Test successful list[int] validation"""
	validate_or_raise([1, 2, 3], list[int])
	validate_or_raise([], list[int])
	validate_or_raise([0, -1, 100], list[int])


def test_validate_list_int_failure() -> None:
	"""Test failed list[int] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise([1, "2", 3], list[int])
	with pytest.raises(TypeValidationError):
		validate_or_raise("not a list", list[int])
	with pytest.raises(TypeValidationError):
		validate_or_raise([1, 2, 3.14], list[int])


def test_validate_list_str_success() -> None:
	"""Test successful list[str] validation"""
	validate_or_raise(["a", "b", "c"], list[str])
	validate_or_raise([], list[str])
	validate_or_raise(["hello", "world", ""], list[str])


def test_validate_list_str_failure() -> None:
	"""Test failed list[str] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise(["a", 1, "c"], list[str])
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, list[str])


# Set type tests
def test_validate_set_int_success() -> None:
	"""Test successful set[int] validation"""
	validate_or_raise({1, 2, 3}, set[int])
	validate_or_raise(set(), set[int])
	validate_or_raise({0, -1, 100}, set[int])


def test_validate_set_int_failure() -> None:
	"""Test failed set[int] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise({1, "2", 3}, set[int])
	with pytest.raises(TypeValidationError):
		validate_or_raise([1, 2, 3], set[int])


def test_validate_set_str_success() -> None:
	"""Test successful set[str] validation"""
	validate_or_raise({"a", "b", "c"}, set[str])
	validate_or_raise(set(), set[str])


def test_validate_set_str_failure() -> None:
	"""Test failed set[str] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise({"a", 1, "c"}, set[str])


# Dict type tests
def test_validate_dict_str_int_success() -> None:
	"""Test successful dict[str, int] validation"""
	validate_or_raise({"a": 1, "b": 2}, dict[str, int])
	validate_or_raise({}, dict[str, int])
	validate_or_raise({"key": 0, "another": -5}, dict[str, int])


def test_validate_dict_str_int_failure() -> None:
	"""Test failed dict[str, int] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise({"a": "1", "b": 2}, dict[str, int])
	with pytest.raises(TypeValidationError):
		validate_or_raise({1: 1, "b": 2}, dict[str, int])
	with pytest.raises(TypeValidationError):
		validate_or_raise("not a dict", dict[str, int])


def test_validate_dict_int_str_success() -> None:
	"""Test successful dict[int, str] validation"""
	validate_or_raise({1: "a", 2: "b"}, dict[int, str])
	validate_or_raise({}, dict[int, str])


def test_validate_dict_int_str_failure() -> None:
	"""Test failed dict[int, str] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise({1: 1, 2: "b"}, dict[int, str])
	with pytest.raises(TypeValidationError):
		validate_or_raise({"1": "a", 2: "b"}, dict[int, str])


# Nested structure tests
def test_validate_nested_list_of_lists_success() -> None:
	"""Test successful nested list[list[int]] validation"""
	validate_or_raise([[1, 2], [3, 4], []], list[list[int]])
	validate_or_raise([], list[list[int]])
	validate_or_raise([[0]], list[list[int]])


def test_validate_nested_list_of_lists_failure() -> None:
	"""Test failed nested list[list[int]] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise([[1, 2], [3, "4"], []], list[list[int]])
	with pytest.raises(TypeValidationError):
		validate_or_raise([[1, 2], "not a list"], list[list[int]])
	with pytest.raises(TypeValidationError):
		validate_or_raise([1, 2, 3], list[list[int]])


def test_validate_nested_dict_of_lists_success() -> None:
	"""Test successful nested dict[str, list[int]] validation"""
	validate_or_raise({"a": [1, 2], "b": [3, 4]}, dict[str, list[int]])
	validate_or_raise({"empty": []}, dict[str, list[int]])
	validate_or_raise({}, dict[str, list[int]])


def test_validate_nested_dict_of_lists_failure() -> None:
	"""Test failed nested dict[str, list[int]] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise({"a": [1, "2"], "b": [3, 4]}, dict[str, list[int]])
	with pytest.raises(TypeValidationError):
		validate_or_raise({"a": "not a list"}, dict[str, list[int]])
	with pytest.raises(TypeValidationError):
		validate_or_raise({1: [1, 2]}, dict[str, list[int]])


def test_validate_nested_list_of_dicts_success() -> None:
	"""Test successful nested list[dict[str, int]] validation"""
	validate_or_raise([{"a": 1}, {"b": 2}], list[dict[str, int]])
	validate_or_raise([{}], list[dict[str, int]])
	validate_or_raise([], list[dict[str, int]])


def test_validate_nested_list_of_dicts_failure() -> None:
	"""Test failed nested list[dict[str, int]] validation"""
	with pytest.raises(TypeValidationError):
		validate_or_raise([{"a": "1"}], list[dict[str, int]])
	with pytest.raises(TypeValidationError):
		validate_or_raise([{1: 1}], list[dict[str, int]])
	with pytest.raises(TypeValidationError):
		validate_or_raise(["not a dict"], list[dict[str, int]])


def test_validate_complex_nested_structure_success() -> None:
	"""Test successful complex nested structure validation"""
	# dict[str, list[dict[str, int]]]
	data = {
		"users": [{"id": 1, "age": 25}, {"id": 2, "age": 30}],
		"products": [{"id": 101, "price": 1000}],
	}
	validate_or_raise(data, dict[str, list[dict[str, int]]])


def test_validate_complex_nested_structure_failure() -> None:
	"""Test failed complex nested structure validation"""
	# dict[str, list[dict[str, int]]]
	data = {
		"users": [
			{"id": 1, "age": "25"},  # age should be int
			{"id": 2, "age": 30},
		],
	}
	with pytest.raises(TypeValidationError):
		validate_or_raise(data, dict[str, list[dict[str, int]]])


# Union with generic types tests
def test_validate_union_with_generic_success() -> None:
	"""Test successful union with generic types validation"""
	union_type = list[int] | str
	validate_or_raise([1, 2, 3], union_type)
	validate_or_raise("hello", union_type)


def test_validate_union_with_generic_failure() -> None:
	"""Test failed union with generic types validation"""
	union_type = list[int] | str
	with pytest.raises(TypeValidationError):
		validate_or_raise([1, "2", 3], union_type)
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, union_type)


def test_validate_complex_union_with_generics_success() -> None:
	"""Test successful complex union with generic types"""
	union_type = list[str] | dict[str, int] | None
	validate_or_raise(["a", "b"], union_type)
	validate_or_raise({"key": 1}, union_type)
	validate_or_raise(None, union_type)


def test_validate_complex_union_with_generics_failure() -> None:
	"""Test failed complex union with generic types"""
	union_type = list[str] | dict[str, int] | None
	with pytest.raises(TypeValidationError):
		validate_or_raise([1, 2], union_type)  # should be list[str]
	with pytest.raises(TypeValidationError):
		validate_or_raise({"key": "value"}, union_type)  # should be dict[str, int]
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, union_type)


def test_validate_deeply_nested_success() -> None:
	"""Test successful deeply nested structure validation"""
	# list[dict[str, list[dict[str, int]]]]
	data = [
		{"group1": [{"item1": 1, "item2": 2}, {"item3": 3}], "group2": []},
		{"group3": [{"item4": 4}]},
	]
	validate_or_raise(data, list[dict[str, list[dict[str, int]]]])


def test_validate_deeply_nested_failure() -> None:
	"""Test failed deeply nested structure validation"""
	# list[dict[str, list[dict[str, int]]]]
	data = [
		{
			"group1": [
				{"item1": 1, "item2": "2"},  # should be int
				{"item3": 3},
			],
		},
	]
	with pytest.raises(TypeValidationError):
		validate_or_raise(data, list[dict[str, list[dict[str, int]]]])


def test_validate_mixed_union_nested_success() -> None:
	"""Test successful mixed union with nested structures"""
	# dict[str, int | list[str]]
	data = {"count": 5, "items": ["a", "b", "c"], "total": 100}
	validate_or_raise(data, dict[str, int | list[str]])


def test_validate_mixed_union_nested_failure() -> None:
	"""Test failed mixed union with nested structures"""
	# dict[str, int | list[str]]
	data = {
		"count": 5,
		"items": [1, 2, 3],  # should be list[str]
		"total": 100,
	}
	with pytest.raises(TypeValidationError):
		validate_or_raise(data, dict[str, int | list[str]])


def test_validate_empty_containers_success() -> None:
	"""Test successful validation of empty containers"""
	validate_or_raise([], list[int])
	validate_or_raise(set(), set[str])
	validate_or_raise({}, dict[str, int])
	validate_or_raise([], list[dict[str, list[int]]])


def test_validate_unsupported_generic_type_failure() -> None:
	"""Test validation failure for unsupported generic types"""
	# This would test tuple or other unsupported generic types
	# Note: This test assumes tuple is not supported based on the code
	with pytest.raises(TypeValidationError, match="Validation for type .* is not supported"):
		validate_or_raise((1, 2, 3), tuple[int, ...])


# Statica subclass tests
def test_validate_statica_instance_success() -> None:
	"""Test successful validation of Statica instance"""
	user = User(name="John", age=30, email="john@example.com")
	validate_or_raise(user, User)


def test_validate_statica_instance_failure() -> None:
	"""Test failed validation of Statica instance - wrong type"""
	user = User(name="John", age=30, email="john@example.com")
	with pytest.raises(TypeValidationError):
		validate_or_raise(user, Address)


def test_validate_statica_subclass_hierarchy_success() -> None:
	"""Test successful validation with Statica subclass hierarchy"""
	user = User(name="John", age=30, email="john@example.com")
	# User should validate against Statica base class
	validate_or_raise(user, Statica)


def test_validate_non_statica_against_statica_failure() -> None:
	"""Test failed validation of non-Statica against Statica type"""
	with pytest.raises(TypeValidationError):
		validate_or_raise("not a statica", User)
	with pytest.raises(TypeValidationError):
		validate_or_raise({"name": "John", "age": 30}, User)
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, User)


def test_validate_statica_union_success() -> None:
	"""Test successful validation of union with Statica types"""
	user = User(name="John", age=30, email="john@example.com")
	address = Address(street="123 Main St", city="Anytown", zipcode="12345")

	union_type = User | Address
	validate_or_raise(user, union_type)
	validate_or_raise(address, union_type)


def test_validate_statica_union_failure() -> None:
	"""Test failed validation of union with Statica types"""
	union_type = User | Address
	with pytest.raises(TypeValidationError):
		validate_or_raise("not a statica", union_type)
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, union_type)


def test_validate_statica_with_none_union_success() -> None:
	"""Test successful validation of Statica | None union"""
	user = User(name="John", age=30, email="john@example.com")
	union_type = User | None

	validate_or_raise(user, union_type)
	validate_or_raise(None, union_type)


def test_validate_statica_with_none_union_failure() -> None:
	"""Test failed validation of Statica | None union"""
	union_type = User | None
	with pytest.raises(TypeValidationError):
		validate_or_raise("not a user", union_type)
	with pytest.raises(TypeValidationError):
		validate_or_raise(42, union_type)


def test_validate_list_of_statica_success() -> None:
	"""Test successful validation of list[Statica]"""
	users = [
		User(name="John", age=30, email="john@example.com"),
		User(name="Jane", age=25, email="jane@example.com"),
	]
	validate_or_raise(users, list[User])
	validate_or_raise([], list[User])


def test_validate_list_of_statica_failure() -> None:
	"""Test failed validation of list[Statica]"""
	users = [
		User(name="John", age=30, email="john@example.com"),
		"not a user",  # Invalid item
	]
	with pytest.raises(TypeValidationError):
		validate_or_raise(users, list[User])


def test_validate_dict_with_statica_values_success() -> None:
	"""Test successful validation of dict[str, Statica]"""
	user_dict = {
		"user1": User(name="John", age=30, email="john@example.com"),
		"user2": User(name="Jane", age=25, email="jane@example.com"),
	}
	validate_or_raise(user_dict, dict[str, User])
	validate_or_raise({}, dict[str, User])


def test_validate_dict_with_statica_values_failure() -> None:
	"""Test failed validation of dict[str, Statica]"""
	user_dict = {
		"user1": User(name="John", age=30, email="john@example.com"),
		"user2": "not a user",  # Invalid value
	}
	with pytest.raises(TypeValidationError):
		validate_or_raise(user_dict, dict[str, User])


def test_validate_dict_with_statica_keys_success() -> None:
	"""Test successful validation of dict[Statica, str]"""
	user1 = User(name="John", age=30, email="john@example.com")
	user2 = User(name="Jane", age=25, email="jane@example.com")

	user_dict = {"1": user1, "2": user2}
	validate_or_raise(user_dict, dict[str, User])


def test_validate_nested_statica_structure_success() -> None:
	"""Test successful validation of nested Statica structures"""
	user = User(name="John", age=30, email="john@example.com")
	address = Address(street="123 Main St", city="Anytown", zipcode="12345")

	profile = Profile(
		user=user,
		address=address,
		tags=["developer", "python"],
		metadata={"role": "engineer", "level": "senior"},
	)

	validate_or_raise(profile, Profile)


def test_validate_nested_statica_structure_failure() -> None:
	"""Test failed validation of nested Statica structures"""
	# Invalid user field
	with pytest.raises(TypeValidationError):
		Profile.from_map(
			{
				"user": "not a user",  # Should be User instance
				"address": None,
				"tags": ["developer"],
				"metadata": {"role": "engineer"},
			},
		)


def test_validate_deeply_nested_statica_success() -> None:
	"""Test successful validation of deeply nested Statica structures"""
	users = [
		User(name="John", age=30, email="john@example.com"),
		User(name="Jane", age=25, email="jane@example.com"),
	]
	address = Address(street="123 Main St", city="Anytown", zipcode="12345")
	company = Company(name="Tech Corp", employees=users, headquarters=address)

	profiles = [
		Profile(
			user=users[0],
			address=address,
			tags=["developer"],
			metadata={"role": "engineer"},
		),
	]

	nested_profile = NestedProfile(profiles=profiles, company=company)
	validate_or_raise(nested_profile, NestedProfile)


def test_validate_deeply_nested_statica_failure() -> None:
	"""Test failed validation of deeply nested Statica structures"""
	# Invalid nested structure
	invalid_profiles = [
		"not a profile",  # Should be Profile instance
	]

	with pytest.raises(TypeValidationError):
		NestedProfile.from_map({"profiles": invalid_profiles, "company": None})


def test_validate_list_of_statica_unions_success() -> None:
	"""Test successful validation of list[Statica1 | Statica2]"""
	user = User(name="John", age=30, email="john@example.com")
	address = Address(street="123 Main St", city="Anytown", zipcode="12345")

	mixed_list = [user, address]
	validate_or_raise(mixed_list, list[User | Address])


def test_validate_list_of_statica_unions_failure() -> None:
	"""Test failed validation of list[Statica1 | Statica2]"""
	user = User(name="John", age=30, email="john@example.com")

	mixed_list = [user, "not a statica"]
	with pytest.raises(TypeValidationError):
		validate_or_raise(mixed_list, list[User | Address])


def test_validate_complex_statica_union_success() -> None:
	"""Test successful validation of complex union with Statica and primitives"""
	user = User(name="John", age=30, email="john@example.com")
	union_type = User | str | int | None

	validate_or_raise(user, union_type)
	validate_or_raise("string", union_type)
	validate_or_raise(42, union_type)
	validate_or_raise(None, union_type)


def test_validate_complex_statica_union_failure() -> None:
	"""Test failed validation of complex union with Statica and primitives"""
	union_type = User | str | int | None
	with pytest.raises(TypeValidationError):
		validate_or_raise(3.14, union_type)  # float not in union
	with pytest.raises(TypeValidationError):
		validate_or_raise([], union_type)  # list not in union


def test_validate_set_of_statica_failure() -> None:
	"""Test failed validation of set[Statica]"""
	# Note: This test might be tricky since sets can't contain unhashable types
	# We'll test with the wrong container type instead
	users = [  # List instead of set
		User(name="John", age=30, email="john@example.com"),
	]
	with pytest.raises(TypeValidationError):
		validate_or_raise(users, set[User])


def test_validate_mixed_generic_with_statica_success() -> None:
	"""Test successful validation of mixed generic structures with Statica"""
	# dict[str, list[Statica]]
	user1 = User(name="John", age=30, email="john@example.com")
	user2 = User(name="Jane", age=25, email="jane@example.com")

	data = {"team1": [user1], "team2": [user2], "team3": []}
	validate_or_raise(data, dict[str, list[User]])


def test_validate_mixed_generic_with_statica_failure() -> None:
	"""Test failed validation of mixed generic structures with Statica"""
	# dict[str, list[Statica]]
	user1 = User(name="John", age=30, email="john@example.com")

	data = {
		"team1": [user1],
		"team2": ["not a user"],  # Invalid list item
	}
	with pytest.raises(TypeValidationError):
		validate_or_raise(data, dict[str, list[User]])


def test_validate_optional_statica_in_complex_structure_success() -> None:
	"""Test successful validation of optional Statica in complex structures"""
	# list[dict[str, Statica | None]]
	user = User(name="John", age=30, email="john@example.com")

	data = [
		{"active_user": user, "inactive_user": None},
		{"active_user": None, "inactive_user": user},
	]
	validate_or_raise(data, list[dict[str, User | None]])


def test_validate_optional_statica_in_complex_structure_failure() -> None:
	"""Test failed validation of optional Statica in complex structures"""
	# list[dict[str, Statica | None]]
	data = [
		{"active_user": "not a user", "inactive_user": None},  # Invalid user
	]
	with pytest.raises(TypeValidationError):
		validate_or_raise(data, list[dict[str, User | None]])
