"""Tests for Statica class inheritance behavior."""

import unittest

from statica import Field, Statica, TypeValidationError
from statica.config import StaticaConfig
from statica.exceptions import ConstraintValidationError

AGE_30 = 30
AGE_25 = 25
AGE_40 = 40
AGE_20 = 20
AGE_35 = 35
AGE_28 = 28
SCORE_85 = 85


class TestInheritance(unittest.TestCase):
	def test_basic_inheritance(self) -> None:
		"""Test that a subclass inherits parent fields."""

		class Base(Statica):
			name: str

		class Child(Base):
			age: int

		child = Child(name="Alice", age=AGE_30)
		self.assertEqual(child.name, "Alice")
		self.assertEqual(child.age, AGE_30)

	def test_inheritance_from_map(self) -> None:
		"""Test that from_map works with inherited fields."""

		class Base(Statica):
			name: str

		class Child(Base):
			age: int

		child = Child.from_map({"name": "Bob", "age": AGE_25})
		self.assertEqual(child.name, "Bob")
		self.assertEqual(child.age, AGE_25)

	def test_inheritance_to_dict(self) -> None:
		"""Test that to_dict includes inherited fields."""

		class Base(Statica):
			name: str

		class Child(Base):
			age: int

		child = Child(name="Charlie", age=AGE_40)
		result = child.to_dict()
		self.assertEqual(result, {"name": "Charlie", "age": AGE_40})

	def test_inheritance_with_defaults(self) -> None:
		"""Test that inherited fields with defaults work in subclass."""

		class Base(Statica):
			name: str
			active: bool = Field(default=True)

		class Child(Base):
			age: int

		child = Child(name="Dana", age=AGE_20)
		self.assertTrue(child.active)
		self.assertEqual(child.age, AGE_20)

	def test_inheritance_child_adds_constraints(self) -> None:
		"""Test that a child class can add its own constrained fields."""

		class Base(Statica):
			name: str

		class Child(Base):
			score: int = Field(min_value=0, max_value=100)

		child = Child(name="Eve", score=SCORE_85)
		self.assertEqual(child.score, SCORE_85)

		with self.assertRaises(ConstraintValidationError):
			Child(name="Eve", score=150)

	def test_inheritance_parent_validation_preserved(self) -> None:
		"""Test that parent field validation is preserved in subclass."""

		class Base(Statica):
			name: str

		class Child(Base):
			age: int

		with self.assertRaises(TypeValidationError):
			Child(name=123, age=AGE_30)  # type: ignore[arg-type]

		with self.assertRaises(TypeValidationError):
			Child(name="Alice", age="thirty")  # type: ignore[arg-type]

	def test_inheritance_missing_required_parent_field(self) -> None:
		"""Test that missing required parent fields raise errors."""

		class Base(Statica):
			name: str

		class Child(Base):
			age: int

		with self.assertRaises(TypeValidationError):
			Child(age=AGE_30)  # type: ignore[call-arg]

	def test_multi_level_inheritance(self) -> None:
		"""Test three levels of inheritance: A -> B -> C."""

		class A(Statica):
			x: int

		class B(A):
			y: int

		class C(B):
			z: int

		x_val, y_val, z_val = 1, 2, 3
		instance = C(x=x_val, y=y_val, z=z_val)
		self.assertEqual(instance.x, x_val)
		self.assertEqual(instance.y, y_val)
		self.assertEqual(instance.z, z_val)

		result = instance.to_dict()
		self.assertEqual(result, {"x": x_val, "y": y_val, "z": z_val})

	def test_multi_level_inheritance_from_map(self) -> None:
		"""Test from_map with three levels of inheritance."""

		class A(Statica):
			x: int

		class B(A):
			y: int

		class C(B):
			z: int

		x_val, y_val, z_val = 10, 20, 30
		instance = C.from_map({"x": x_val, "y": y_val, "z": z_val})
		self.assertEqual(instance.x, x_val)
		self.assertEqual(instance.y, y_val)
		self.assertEqual(instance.z, z_val)

	def test_inheritance_with_aliases(self) -> None:
		"""Test that aliases work with inherited fields."""

		class Base(Statica):
			name: str = Field(alias="userName")

		class Child(Base):
			age: int = Field(alias="userAge")

		child = Child.from_map({"userName": "Frank", "userAge": AGE_35})
		self.assertEqual(child.name, "Frank")
		self.assertEqual(child.age, AGE_35)

		result = child.to_dict()
		self.assertEqual(result, {"userName": "Frank", "userAge": AGE_35})

	def test_inheritance_with_custom_config(self) -> None:
		"""Test that subclass can use a different config."""

		custom_config = StaticaConfig.create(
			type_error_message="Custom: expected {expected_type}, got {found_type}",
		)

		class Base(Statica):
			name: str

		class Child(Base, config=custom_config):
			age: int

		with self.assertRaises(TypeValidationError) as cm:
			Child(name="Alice", age="thirty")  # type: ignore[arg-type]
		self.assertIn("Custom:", str(cm.exception))

	def test_inheritance_with_custom_error_class(self) -> None:
		"""Test that subclass can override error classes."""

		class CustomError(Exception):
			pass

		class Base(Statica):
			name: str

		class Child(Base):
			type_error_class = CustomError
			age: int

		with self.assertRaises(CustomError):
			Child(name="Alice", age="thirty")  # type: ignore[arg-type]

	def test_inheritance_with_nested_statica(self) -> None:
		"""Test inheritance where child has a nested Statica field."""

		class Address(Statica):
			city: str

		class Base(Statica):
			name: str

		class Child(Base):
			address: Address

		child = Child.from_map({"name": "Grace", "address": {"city": "Berlin"}})
		self.assertEqual(child.name, "Grace")
		self.assertEqual(child.address.city, "Berlin")

		result = child.to_dict()
		self.assertEqual(result, {"name": "Grace", "address": {"city": "Berlin"}})

	def test_inheritance_with_optional_parent_fields(self) -> None:
		"""Test inheritance where parent has optional fields."""

		class Base(Statica):
			name: str
			nickname: str | None

		class Child(Base):
			age: int

		child = Child(name="Hank", nickname=None, age=AGE_28)
		self.assertIsNone(child.nickname)

		child2 = Child(name="Hank", nickname="Hanky", age=AGE_28)
		self.assertEqual(child2.nickname, "Hanky")

	def test_inheritance_child_override_with_constraints(self) -> None:
		"""Test child class with same-name field with added constraints."""

		class Base(Statica):
			name: str

		class StrictChild(Base):
			name: str = Field(min_length=3, max_length=20)
			age: int

		child = StrictChild(name="Alice", age=AGE_30)
		self.assertEqual(child.name, "Alice")

		with self.assertRaises(ConstraintValidationError):
			StrictChild(name="Al", age=AGE_30)
