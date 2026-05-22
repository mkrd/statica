"""Tests for Statica class inheritance behavior."""

import pytest

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


@pytest.mark.xfail(reason="Metaclass does not propagate parent fields through __init__")
def test_basic_inheritance() -> None:
	"""Test that a subclass inherits parent fields."""

	class Base(Statica):
		name: str

	class Child(Base):
		age: int

	child = Child(name="Alice", age=AGE_30)
	assert child.name == "Alice"
	assert child.age == AGE_30


@pytest.mark.xfail(reason="Metaclass does not propagate parent fields through from_map")
def test_inheritance_from_map() -> None:
	"""Test that from_map works with inherited fields."""

	class Base(Statica):
		name: str

	class Child(Base):
		age: int

	child = Child.from_map({"name": "Bob", "age": AGE_25})
	assert child.name == "Bob"
	assert child.age == AGE_25


@pytest.mark.xfail(reason="Metaclass does not propagate parent fields through to_dict")
def test_inheritance_to_dict() -> None:
	"""Test that to_dict includes inherited fields."""

	class Base(Statica):
		name: str

	class Child(Base):
		age: int

	child = Child(name="Charlie", age=AGE_40)
	result = child.to_dict()
	assert result == {"name": "Charlie", "age": AGE_40}


@pytest.mark.xfail(reason="Metaclass does not propagate parent fields through __init__")
def test_inheritance_with_defaults() -> None:
	"""Test that inherited fields with defaults work in subclass."""

	class Base(Statica):
		name: str
		active: bool = Field(default=True)

	class Child(Base):
		age: int

	child = Child(name="Dana", age=AGE_20)
	assert child.active is True
	assert child.age == AGE_20


def test_inheritance_child_adds_constraints() -> None:
	"""Test that a child class can add its own constrained fields."""

	class Base(Statica):
		name: str

	class Child(Base):
		score: int = Field(min_value=0, max_value=100)

	child = Child(name="Eve", score=SCORE_85)
	assert child.score == SCORE_85

	with pytest.raises(ConstraintValidationError):
		Child(name="Eve", score=150)


@pytest.mark.xfail(reason="Parent fields not validated in subclass")
def test_inheritance_parent_validation_preserved() -> None:
	"""Test that parent field validation is preserved in subclass."""

	class Base(Statica):
		name: str

	class Child(Base):
		age: int

	with pytest.raises(TypeValidationError):
		Child(name=123, age=AGE_30)  # type: ignore[arg-type]

	with pytest.raises(TypeValidationError):
		Child(name="Alice", age="thirty")  # type: ignore[arg-type]


@pytest.mark.xfail(reason="Missing parent field not detected in subclass")
def test_inheritance_missing_required_parent_field() -> None:
	"""Test that missing required parent fields raise errors."""

	class Base(Statica):
		name: str

	class Child(Base):
		age: int

	with pytest.raises(TypeValidationError):
		Child(age=AGE_30)  # type: ignore[call-arg]


@pytest.mark.xfail(reason="Parent fields not propagated in multi-level inheritance")
def test_multi_level_inheritance() -> None:
	"""Test three levels of inheritance: A -> B -> C."""

	class A(Statica):
		x: int

	class B(A):
		y: int

	class C(B):
		z: int

	x_val, y_val, z_val = 1, 2, 3
	instance = C(x=x_val, y=y_val, z=z_val)
	assert instance.x == x_val
	assert instance.y == y_val
	assert instance.z == z_val

	result = instance.to_dict()
	assert result == {"x": x_val, "y": y_val, "z": z_val}


@pytest.mark.xfail(reason="Metaclass does not propagate parent fields through multi-level from_map")
def test_multi_level_inheritance_from_map() -> None:
	"""Test from_map with three levels of inheritance."""

	class A(Statica):
		x: int

	class B(A):
		y: int

	class C(B):
		z: int

	x_val, y_val, z_val = 10, 20, 30
	instance = C.from_map({"x": x_val, "y": y_val, "z": z_val})
	assert instance.x == x_val
	assert instance.y == y_val
	assert instance.z == z_val


@pytest.mark.xfail(reason="Parent fields not propagated via from_map with aliases")
def test_inheritance_with_aliases() -> None:
	"""Test that aliases work with inherited fields."""

	class Base(Statica):
		name: str = Field(alias="userName")

	class Child(Base):
		age: int = Field(alias="userAge")

	child = Child.from_map({"userName": "Frank", "userAge": AGE_35})
	assert child.name == "Frank"
	assert child.age == AGE_35

	result = child.to_dict()
	assert result == {"userName": "Frank", "userAge": AGE_35}


def test_inheritance_with_custom_config() -> None:
	"""Test that subclass can use a different config."""

	custom_config = StaticaConfig.create(
		type_error_message="Custom: expected {expected_type}, got {found_type}",
	)

	class Base(Statica):
		name: str

	class Child(Base, config=custom_config):
		age: int

	with pytest.raises(TypeValidationError, match="Custom:"):
		Child(name="Alice", age="thirty")  # type: ignore[arg-type]


def test_inheritance_with_custom_error_class() -> None:
	"""Test that subclass can override error classes."""

	class CustomError(Exception):
		pass

	class Base(Statica):
		name: str

	class Child(Base):
		type_error_class = CustomError
		age: int

	with pytest.raises(CustomError):
		Child(name="Alice", age="thirty")  # type: ignore[arg-type]


@pytest.mark.xfail(reason="Metaclass does not propagate parent fields with nested Statica")
def test_inheritance_with_nested_statica() -> None:
	"""Test inheritance where child has a nested Statica field."""

	class Address(Statica):
		city: str

	class Base(Statica):
		name: str

	class Child(Base):
		address: Address

	child = Child.from_map({"name": "Grace", "address": {"city": "Berlin"}})
	assert child.name == "Grace"
	assert child.address.city == "Berlin"

	result = child.to_dict()
	assert result == {"name": "Grace", "address": {"city": "Berlin"}}


@pytest.mark.xfail(reason="Metaclass does not propagate parent optional fields")
def test_inheritance_with_optional_parent_fields() -> None:
	"""Test inheritance where parent has optional fields."""

	class Base(Statica):
		name: str
		nickname: str | None

	class Child(Base):
		age: int

	child = Child(name="Hank", nickname=None, age=AGE_28)
	assert child.nickname is None

	child2 = Child(name="Hank", nickname="Hanky", age=AGE_28)
	assert child2.nickname == "Hanky"


def test_inheritance_child_override_with_constraints() -> None:
	"""Test child class with same-name field with added constraints."""

	class Base(Statica):
		name: str

	class StrictChild(Base):
		name: str = Field(min_length=3, max_length=20)
		age: int

	child = StrictChild(name="Alice", age=AGE_30)
	assert child.name == "Alice"

	with pytest.raises(ConstraintValidationError):
		StrictChild(name="Al", age=AGE_30)
