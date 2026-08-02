"""Tests for frozen models and the init/frozen/eq/order class arguments."""

import unittest

from statica import (
	ConstraintValidationError,
	Field,
	FrozenInstanceError,
	Statica,
	StaticaConfig,
	TypeValidationError,
)


class TestFrozen(unittest.TestCase):
	def test_frozen_blocks_assignment(self) -> None:
		class Point(Statica, frozen=True):
			x: int
			y: int

		p = Point(x=1, y=2)
		self.assertEqual((p.x, p.y), (1, 2))

		with self.assertRaises(FrozenInstanceError):
			p.x = 5  # type: ignore[read-only]

		with self.assertRaises(FrozenInstanceError):
			del p.x  # type: ignore[read-only]

	def test_frozen_is_attribute_error(self) -> None:
		class Point(Statica, frozen=True):
			x: int

		# FrozenInstanceError must behave like an AttributeError.
		self.assertTrue(issubclass(FrozenInstanceError, AttributeError))
		with self.assertRaises(AttributeError):
			Point(x=1).x = 2  # type: ignore[read-only]

	def test_non_frozen_allows_assignment(self) -> None:
		class Point(Statica):
			x: int

		p = Point(x=1)
		p.x = 9
		self.assertEqual(p.x, 9)

	def test_frozen_validates_on_init(self) -> None:

		class Point(Statica, frozen=True):
			x: int

		with self.assertRaises(TypeValidationError):
			Point(x="nope")  # type: ignore[arg-type]


class TestEquality(unittest.TestCase):
	def test_default_value_equality(self) -> None:
		class Model(Statica):
			x: int
			y: str

		self.assertEqual(Model(x=1, y="a"), Model(x=1, y="a"))
		self.assertNotEqual(Model(x=1, y="a"), Model(x=2, y="a"))

	def test_eq_false_uses_identity(self) -> None:
		class Model(Statica, eq=False):
			x: int

		a = Model(x=1)
		self.assertEqual(a, a)
		self.assertNotEqual(Model(x=1), Model(x=1))

	def test_eq_different_classes(self) -> None:
		class A(Statica):
			x: int

		class B(Statica):
			x: int

		self.assertNotEqual(A(x=1), B(x=1))

	def test_default_model_unhashable(self) -> None:
		class Model(Statica):
			x: int

		with self.assertRaises(TypeError):
			hash(Model(x=1))

	def test_frozen_model_hashable(self) -> None:
		class Model(Statica, frozen=True):
			x: int
			y: int

		self.assertEqual(hash(Model(x=1, y=2)), hash(Model(x=1, y=2)))
		self.assertEqual(len({Model(x=1, y=2), Model(x=1, y=2)}), 1)

	def test_eq_false_keeps_identity_hash(self) -> None:
		class Model(Statica, eq=False):
			x: int

		# Not eq -> identity hash remains available.
		self.assertIsInstance(hash(Model(x=1)), int)


class TestOrder(unittest.TestCase):
	def test_order_operators(self) -> None:
		class Model(Statica, order=True):
			a: int
			b: int

		self.assertLess(Model(a=1, b=1), Model(a=1, b=2))
		self.assertLessEqual(Model(a=1, b=1), Model(a=1, b=1))
		self.assertGreater(Model(a=2, b=0), Model(a=1, b=9))
		self.assertGreaterEqual(Model(a=1, b=1), Model(a=1, b=1))

	def test_order_default_off(self) -> None:
		class Model(Statica):
			a: int

		with self.assertRaises(TypeError):
			_ = Model(a=1) < Model(a=2)  # type: ignore[unsupported-operation]

	def test_order_different_classes(self) -> None:
		class A(Statica, order=True):
			x: int

		class B(Statica, order=True):
			x: int

		with self.assertRaises(TypeError):
			_ = A(x=1) < B(x=2)  # type: ignore[unsupported-operation]


class TestInitArgument(unittest.TestCase):
	def test_init_false_skips_generated_init(self) -> None:
		class Model(Statica, init=False):
			x: int

			def __init__(self, value: int) -> None:
				self.x = value

		m = Model(5)
		self.assertEqual(m.x, 5)

	def test_init_false_still_validates_on_assignment(self) -> None:

		class Model(Statica, init=False):
			x: int

			def __init__(self, value: object) -> None:
				self.x = value  # type: ignore[assignment]

		with self.assertRaises(TypeValidationError):
			Model("bad")


class TestOptionInheritance(unittest.TestCase):
	def test_frozen_inherited(self) -> None:
		class Base(Statica, frozen=True):
			x: int

		# frozen is inherited at runtime; the type checker can't model that.
		class Child(Base):  # type: ignore[invalid-inheritance]
			y: int

		child = Child(x=1, y=2)
		with self.assertRaises(FrozenInstanceError):
			child.y = 3  # type: ignore[read-only]

	def test_child_can_override_option(self) -> None:
		class Base(Statica, frozen=True):
			x: int

		class Child(Base, frozen=False):  # type: ignore[invalid-inheritance]
			y: int

		child = Child(x=1, y=2)
		child.y = 3
		self.assertEqual(child.y, 3)

	def test_config_inherited(self) -> None:

		config = StaticaConfig.create(type_error_message="CUSTOM {expected_type}")

		class Base(Statica, config=config):
			x: int

		class Child(Base):
			y: int

		with self.assertRaises(TypeValidationError) as cm:
			Child(x="bad", y=1)  # type: ignore[arg-type]
		self.assertIn("CUSTOM", str(cm.exception))


class TestPostInit(unittest.TestCase):
	def test_cross_field_validation(self) -> None:
		class Range(Statica):
			lo: int
			hi: int

			def __post_init__(self) -> None:
				if self.lo > self.hi:
					msg = "lo must be <= hi"
					raise ValueError(msg)

		self.assertEqual(Range(lo=1, hi=2).hi, 2)
		with self.assertRaises(ValueError):
			Range(lo=5, hi=1)

	def test_post_init_runs_via_from_map(self) -> None:
		calls: list[str] = []

		class Model(Statica):
			x: int

			def __post_init__(self) -> None:
				calls.append("called")

		Model.from_map({"x": 1})
		self.assertEqual(calls, ["called"])

	def test_field_validator_transform_and_reject(self) -> None:

		def clamp_positive(value: int) -> int:
			if value < 0:
				msg = "must be positive"
				raise ValueError(msg)
			return value * 2

		class Model(Statica):
			n: int = Field(validator=clamp_positive)

		self.assertEqual(Model(n=3).n, 6)
		with self.assertRaises(ConstraintValidationError):
			Model(n=-1)


if __name__ == "__main__":
	unittest.main()
