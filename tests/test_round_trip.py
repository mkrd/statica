"""Tests for serialization round-trip: from_map -> to_dict -> from_map."""

import unittest

from statica import Field, Statica

AGE_30 = 30
AGE_25 = 25
SCORE_95 = 95


class TestRoundTrip(unittest.TestCase):
	def test_basic_round_trip(self) -> None:
		"""Test from_map -> to_dict produces the same data."""

		class Model(Statica):
			name: str
			age: int

		data = {"name": "Alice", "age": AGE_30}
		instance = Model.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

	def test_round_trip_with_optional_fields(self) -> None:
		"""Test round-trip with optional fields present."""

		class Model(Statica):
			name: str
			bio: str | None

		data_with = {"name": "Bob", "bio": "Hello"}
		instance = Model.from_map(data_with)
		self.assertEqual(instance.to_dict(), data_with)

		data_without = {"name": "Charlie"}
		instance2 = Model.from_map(data_without)
		result = instance2.to_dict()
		self.assertEqual(result, {"name": "Charlie", "bio": None})

	def test_round_trip_with_defaults(self) -> None:
		"""Test round-trip with default values."""

		class Model(Statica):
			name: str
			status: str = Field(default="active")

		data = {"name": "Dana"}
		instance = Model.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, {"name": "Dana", "status": "active"})

		# And back again
		instance2 = Model.from_map(result)
		self.assertEqual(instance2.name, "Dana")
		self.assertEqual(instance2.status, "active")

	def test_round_trip_with_aliases(self) -> None:
		"""Test full round-trip with aliases: from_map -> to_dict -> from_map."""

		class Model(Statica):
			full_name: str = Field(alias="fullName")
			user_age: int = Field(alias="userAge")

		data = {"fullName": "Eve Smith", "userAge": AGE_25}
		instance = Model.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

		# Round-trip back
		instance2 = Model.from_map(result)
		self.assertEqual(instance2.full_name, "Eve Smith")
		self.assertEqual(instance2.user_age, AGE_25)

	def test_round_trip_nested_statica(self) -> None:
		"""Test round-trip with nested Statica objects."""

		class Address(Statica):
			city: str
			zip_code: str

		class User(Statica):
			name: str
			address: Address

		data = {"name": "Frank", "address": {"city": "Berlin", "zip_code": "10115"}}
		instance = User.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

		# Round-trip back
		instance2 = User.from_map(result)
		self.assertEqual(instance2.name, "Frank")
		self.assertEqual(instance2.address.city, "Berlin")
		self.assertEqual(instance2.address.zip_code, "10115")

	def test_round_trip_nested_with_aliases(self) -> None:
		"""Test round-trip with nested Statica objects that have aliases."""

		class Inner(Statica):
			inner_value: str = Field(alias="innerValue")

		class Outer(Statica):
			outer_name: str = Field(alias="outerName")
			nested: Inner = Field(alias="nestedObj")

		data = {"outerName": "test", "nestedObj": {"innerValue": "hello"}}
		instance = Outer.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

		# Round-trip back
		instance2 = Outer.from_map(result)
		self.assertEqual(instance2.outer_name, "test")
		self.assertEqual(instance2.nested.inner_value, "hello")

	def test_round_trip_with_constraints(self) -> None:
		"""Test round-trip with constrained values."""

		class Model(Statica):
			name: str = Field(min_length=2, max_length=50)
			score: int = Field(min_value=0, max_value=100)

		data = {"name": "Grace", "score": SCORE_95}
		instance = Model.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

		instance2 = Model.from_map(result)
		self.assertEqual(instance2.name, "Grace")
		self.assertEqual(instance2.score, SCORE_95)

	def test_round_trip_with_strip_whitespace(self) -> None:
		"""Test that strip_whitespace alters the round-trip (expected behavior)."""

		class Model(Statica):
			name: str = Field(strip_whitespace=True)

		data = {"name": "  padded  "}
		instance = Model.from_map(data)
		self.assertEqual(instance.name, "padded")

		result = instance.to_dict()
		self.assertEqual(result, {"name": "padded"})  # Stripped, not original

		# Second round-trip is stable
		instance2 = Model.from_map(result)
		self.assertEqual(instance2.name, "padded")

	def test_round_trip_collection_fields(self) -> None:
		"""Test round-trip with list and dict fields."""

		class Model(Statica):
			tags: list[str]
			metadata: dict[str, int]

		data = {"tags": ["a", "b", "c"], "metadata": {"x": 1, "y": 2}}
		instance = Model.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

	def test_round_trip_optional_nested_none(self) -> None:
		"""Test round-trip when optional nested field is None."""

		class Inner(Statica):
			value: str

		class Outer(Statica):
			name: str
			inner: Inner | None

		data = {"name": "Hank"}
		instance = Outer.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, {"name": "Hank", "inner": None})

		# Round-trip back
		instance2 = Outer.from_map(result)
		self.assertEqual(instance2.name, "Hank")
		self.assertIsNone(instance2.inner)

	def test_round_trip_to_dict_without_aliases_then_back(self) -> None:
		"""Test from_map with aliased data, to_dict without aliases, verify field names."""

		class Model(Statica):
			user_name: str = Field(alias="userName")

		data = {"userName": "Ivy"}
		instance = Model.from_map(data)

		# Serialize without aliases (use Python field names)
		result_no_alias = instance.to_dict(with_aliases=False)
		self.assertEqual(result_no_alias, {"user_name": "Ivy"})

	def test_round_trip_deeply_nested(self) -> None:
		"""Test round-trip with multiple levels of nesting."""

		class Level3(Statica):
			value: str

		class Level2(Statica):
			child: Level3

		class Level1(Statica):
			child: Level2

		data = {"child": {"child": {"value": "deep"}}}
		instance = Level1.from_map(data)
		result = instance.to_dict()
		self.assertEqual(result, data)

		instance2 = Level1.from_map(result)
		self.assertEqual(instance2.child.child.value, "deep")

	def test_round_trip_extra_keys_ignored(self) -> None:
		"""Test that from_map ignores extra keys not in the model."""

		class Model(Statica):
			name: str

		data = {"name": "Jack", "extra_field": "ignored", "another": 42}
		instance = Model.from_map(data)
		self.assertEqual(instance.name, "Jack")

		result = instance.to_dict()
		self.assertEqual(result, {"name": "Jack"})  # Extra keys not in output
