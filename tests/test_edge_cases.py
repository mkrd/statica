"""Edge-case coverage for 2.0 features: hashing, ordering, validators, unions, abc."""

import unittest
from collections import abc
from datetime import datetime
from decimal import Decimal
from enum import Enum, IntEnum

from statica import (
	ConstraintValidationError,
	Field,
	FrozenInstanceError,
	Statica,
	TypeValidationError,
)
from statica.validation import validate_or_raise


class TestHashingEdges(unittest.TestCase):
	def test_frozen_eq_false_uses_identity_hash(self) -> None:
		class Model(Statica, frozen=True, eq=False):
			x: int

		a = Model(x=1)
		self.assertEqual(hash(a), object.__hash__(a))
		self.assertNotEqual(Model(x=1), Model(x=1))

	def test_frozen_with_unhashable_field_raises_on_hash(self) -> None:
		class Model(Statica, frozen=True):
			items: list[int] = Field(default=[])

		with self.assertRaises(TypeError):
			hash(Model(items=[1, 2]))

	def test_eq_with_nested_models(self) -> None:
		class Inner(Statica):
			v: int

		class Outer(Statica):
			inner: Inner

		self.assertEqual(Outer(inner=Inner(v=1)), Outer(inner=Inner(v=1)))
		self.assertNotEqual(Outer(inner=Inner(v=1)), Outer(inner=Inner(v=2)))


class TestOrderingEdges(unittest.TestCase):
	def test_all_operators_tie_break(self) -> None:
		class M(Statica, order=True):
			a: int
			b: int

		self.assertTrue(M(a=1, b=1) <= M(a=1, b=1))
		self.assertTrue(M(a=1, b=1) >= M(a=1, b=1))
		self.assertTrue(M(a=1, b=2) > M(a=1, b=1))
		self.assertFalse(M(a=1, b=1) > M(a=1, b=1))

	def test_le_ge_gt_different_classes(self) -> None:
		class A(Statica, order=True):
			x: int

		class B(Statica, order=True):
			x: int

		for op in ("__le__", "__ge__", "__gt__", "__lt__"):
			self.assertIs(getattr(A(x=1), op)(B(x=1)), NotImplemented)


class TestValidatorErrorPropagation(unittest.TestCase):
	def test_validator_raises_constraint_error_without_loc(self) -> None:
		def reject(_: int) -> int:
			msg = "nope"
			raise ConstraintValidationError(msg)

		class M(Statica):
			n: int = Field(validator=reject)

		with self.assertRaises(ConstraintValidationError) as cm:
			M(n=1)
		self.assertEqual(str(cm.exception), "M.n: nope")

	def test_validator_raises_constraint_error_with_loc(self) -> None:
		def reject(_: int) -> int:
			msg = "nope"
			raise ConstraintValidationError(msg, loc=["explicit"])

		class M(Statica):
			n: int = Field(validator=reject)

		with self.assertRaises(ConstraintValidationError) as cm:
			M(n=1)
		# Explicit loc is preserved (not overwritten with the field name).
		self.assertEqual(str(cm.exception), "M.explicit: nope")

	def test_validator_raises_type_error(self) -> None:
		def reject(_: int) -> int:
			msg = "bad type"
			raise TypeValidationError(msg)

		class M(Statica):
			n: int = Field(validator=reject)

		with self.assertRaises(TypeValidationError) as cm:
			M(n=1)
		self.assertEqual(str(cm.exception), "M.n: bad type")


class TestFrozenPostInit(unittest.TestCase):
	def test_post_init_can_read_fields(self) -> None:
		class M(Statica, frozen=True):
			x: int

			def __post_init__(self) -> None:
				if self.x < 0:
					msg = "negative"
					raise ValueError(msg)

		self.assertEqual(M(x=5).x, 5)
		with self.assertRaises(ValueError):
			M(x=-1)

	def test_post_init_normal_assignment_blocked(self) -> None:
		class M(Statica, frozen=True):
			x: int
			doubled: int = Field(default=0)

			def __post_init__(self) -> None:
				# Normal assignment is blocked on a frozen instance.
				self.doubled = self.x * 2  # type: ignore[read-only]

		with self.assertRaises(FrozenInstanceError):
			M(x=2)

	def test_post_init_object_setattr_works(self) -> None:
		class M(Statica, frozen=True):
			x: int
			doubled: int = Field(default=0)

			def __post_init__(self) -> None:
				object.__setattr__(self, "doubled", self.x * 2)

		self.assertEqual(M(x=2).doubled, 4)


class TestUnionCoercion(unittest.TestCase):
	def test_union_coerces_via_codec_branch(self) -> None:
		class M(Statica):
			v: int | datetime

		self.assertIsInstance(M.from_map({"v": "2020-01-01T00:00:00"}).v, datetime)
		self.assertEqual(M(v=5).v, 5)

	def test_union_left_to_right_str_wins(self) -> None:
		# A str value matches `str` before `datetime`, so it is NOT coerced.
		class M(Statica):
			v: str | datetime

		self.assertIsInstance(M.from_map({"v": "2020-01-01T00:00:00"}).v, str)

	def test_optional_codec(self) -> None:
		class M(Statica):
			v: datetime | None

		self.assertIsNone(M(v=None).v)
		self.assertIsInstance(M.from_map({"v": "2020-01-01T00:00:00"}).v, datetime)


class TestUnionNestedModelPath(unittest.TestCase):
	def test_bad_field_in_optional_model_reports_union_summary(self) -> None:
		# Known limitation: a bad field inside `Model | None` surfaces the union
		# summary, not the precise nested path, because the union suppresses the
		# inner branch failure.
		class Addr(Statica):
			street: str

		class User(Statica):
			addr: Addr | None

		with self.assertRaises(TypeValidationError) as cm:
			User.from_map({"addr": {"street": 123}})
		self.assertIn("User.addr:", str(cm.exception))
		self.assertIn("Addr | NoneType", str(cm.exception))


class TestAbcBranches(unittest.TestCase):
	def test_mapping_rejects_non_mapping(self) -> None:
		class M(Statica):
			data: abc.Mapping[str, int]

		with self.assertRaises(TypeValidationError):
			M(data=[1, 2])  # type: ignore[arg-type]

	def test_container_isinstance_only(self) -> None:
		class M(Statica):
			c: abc.Container[int]

		self.assertEqual(M(c=[1, 2]).c, [1, 2])
		with self.assertRaises(TypeValidationError):
			M(c=5)  # type: ignore[arg-type]

	def test_sequence_rejects_non_sequence(self) -> None:
		class M(Statica):
			items: abc.Sequence[int]

		with self.assertRaises(TypeValidationError):
			M(items=5)  # type: ignore[arg-type]

	def test_unsupported_generic_origin(self) -> None:
		class M(Statica):
			a: abc.Awaitable[int]

		with self.assertRaisesRegex(TypeValidationError, r"unsupported type"):
			M(a=None)  # type: ignore[arg-type]

	def test_mutable_variants(self) -> None:
		class M(Statica):
			seq: abc.MutableSequence[int]
			mp: abc.MutableMapping[str, int]
			st: abc.MutableSet[int]

		m = M(seq=[1], mp={"a": 1}, st={1})
		self.assertEqual(list(m.seq), [1])
		self.assertEqual(dict(m.mp), {"a": 1})


class TestNestedGenerics(unittest.TestCase):
	def test_list_of_lists(self) -> None:
		class M(Statica):
			grid: list[list[int]]

		self.assertEqual(M(grid=[[1, 2], [3]]).grid, [[1, 2], [3]])
		with self.assertRaises(TypeValidationError) as cm:
			M(grid=[[1], [2, "x"]])  # type: ignore[list-item]
		self.assertEqual(str(cm.exception), "M.grid[1][1]: expected type 'int', got 'str'")

	def test_dict_of_lists(self) -> None:
		class M(Statica):
			data: dict[str, list[int]]

		self.assertEqual(M(data={"a": [1, 2]}).data, {"a": [1, 2]})
		with self.assertRaises(TypeValidationError) as cm:
			M(data={"a": [1, "x"]})  # type: ignore[list-item]
		self.assertEqual(str(cm.exception), "M.data['a'][1]: expected type 'int', got 'str'")


class TestEnumAndDecimalEdges(unittest.TestCase):
	def test_int_enum(self) -> None:
		class Level(IntEnum):
			LOW = 1
			HIGH = 2

		class M(Statica):
			lvl: Level

		self.assertEqual(M.from_map({"lvl": 1}).lvl, Level.LOW)
		self.assertEqual(M(lvl=Level.HIGH).to_dict(), {"lvl": 2})

	def test_list_of_enum_serialization(self) -> None:
		class Color(Enum):
			R = "r"
			G = "g"

		class M(Statica):
			colors: list[Color]

		m = M.from_map({"colors": ["r", "g"]})
		self.assertEqual(m.colors, [Color.R, Color.G])
		self.assertEqual(m.to_dict(), {"colors": ["r", "g"]})

	def test_decimal_from_int(self) -> None:
		class M(Statica):
			d: Decimal

		self.assertEqual(M.from_map({"d": 5}).d, Decimal(5))
		self.assertEqual(M(d=Decimal("1.5")).d, Decimal("1.5"))


class TestSerializationEdges(unittest.TestCase):
	def test_dict_of_models_coercion_and_to_dict(self) -> None:
		class Item(Statica):
			n: int

		class Box(Statica):
			items: dict[str, Item]

		box = Box.from_map({"items": {"a": {"n": 1}, "b": {"n": 2}}})
		self.assertIsInstance(box.items["a"], Item)
		self.assertEqual(box.to_dict(), {"items": {"a": {"n": 1}, "b": {"n": 2}}})

	def test_nested_to_dict_without_aliases(self) -> None:
		class Inner(Statica):
			full_name: str = Field(alias="fullName")

		class Outer(Statica):
			inner: Inner = Field(alias="innerObj")

		outer = Outer.from_map({"innerObj": {"fullName": "x"}})
		self.assertEqual(outer.to_dict(), {"innerObj": {"fullName": "x"}})
		self.assertEqual(
			outer.to_dict(with_aliases=False),
			{"inner": {"full_name": "x"}},
		)


class TestStructuralEdges(unittest.TestCase):
	def test_empty_model(self) -> None:
		class Empty(Statica):
			pass

		self.assertEqual(Empty(), Empty())
		self.assertEqual(Empty().to_dict(), {})
		self.assertEqual(Empty.from_map({}).to_dict(), {})

	def test_multiple_inheritance_collects_all_fields(self) -> None:
		class A(Statica):
			a: int

		class B(Statica):
			b: int

		class C(A, B):
			c: int

		names = [d.name for d in C.__field_descriptors__]
		# Fields from all bases plus own, following reverse-bases order.
		self.assertEqual(set(names), {"a", "b", "c"})
		instance = C(a=1, b=2, c=3)
		self.assertEqual((instance.a, instance.b, instance.c), (1, 2, 3))
		self.assertEqual(instance.to_dict(), {"a": 1, "b": 2, "c": 3})

	def test_init_false_from_map_incompatible_raises(self) -> None:
		class M(Statica, init=False):
			x: int

			def __init__(self) -> None:  # incompatible with from_map kwargs
				object.__setattr__(self, "x", 0)

		with self.assertRaises(TypeError):
			M.from_map({"x": 1})


class TestDirectValidation(unittest.TestCase):
	def test_direct_validate_no_root_dict_key(self) -> None:
		with self.assertRaises(TypeValidationError) as cm:
			validate_or_raise({"k": "bad"}, dict[str, int])
		self.assertEqual(str(cm.exception), "['k']: expected type 'int', got 'str'")

	def test_direct_validate_no_root_key_segment(self) -> None:
		# Root-less error whose first segment is a mapping key (not a bracket).
		with self.assertRaises(TypeValidationError) as cm:
			validate_or_raise({5: 1}, dict[str, int])
		self.assertEqual(str(cm.exception), "<key 5>: expected type 'str', got 'int'")

	def test_direct_validate_returns_coerced(self) -> None:
		result = validate_or_raise("2020-01-02T03:04:05", datetime)
		self.assertIsInstance(result, datetime)


class _Category(Statica):
	"""Module-level recursive model (forward refs resolve at validation time)."""

	name: str = Field(min_length=1)
	children: list["_Category"] = Field(default=[])


class TestRecursiveModels(unittest.TestCase):
	def test_recursive_parse_and_round_trip(self) -> None:
		data = {
			"name": "root",
			"children": [
				{"name": "a", "children": [{"name": "a1"}]},
				{"name": "b"},
			],
		}
		root = _Category.from_map(data)
		self.assertEqual(root.name, "root")
		self.assertEqual(root.children[0].children[0].name, "a1")
		# Recursive to_dict round-trips (defaults included).
		self.assertEqual(_Category.from_map(root.to_dict()), root)

	def test_recursive_deep_error_path(self) -> None:
		data = {"name": "root", "children": [{"name": "a", "children": [{"name": ""}]}]}
		with self.assertRaises(ConstraintValidationError) as cm:
			_Category.from_map(data)
		self.assertEqual(
			str(cm.exception),
			"_Category.children[0].children[0].name: length must be at least 1",
		)


class TestCustomErrorClassPaths(unittest.TestCase):
	def test_nested_custom_error_class_single_path(self) -> None:
		class DomainTypeError(TypeValidationError):
			pass

		class Base(Statica):
			type_error_class = DomainTypeError

		class Inner(Base):
			code: str

		class Outer(Base):
			inner: Inner

		with self.assertRaises(DomainTypeError) as cm:
			Outer.from_map({"inner": {"code": 123}})
		# A single, non-doubled path even though a custom error class is used.
		self.assertEqual(str(cm.exception), "Outer.inner.code: expected type 'str', got 'int'")

	def test_non_validation_custom_error_class(self) -> None:
		class Model(Statica):
			type_error_class = ValueError
			x: int

		with self.assertRaises(ValueError) as cm:
			Model(x="bad")  # type: ignore[arg-type]
		self.assertIn("Model.x", str(cm.exception))


class TestDecimalConstraints(unittest.TestCase):
	def test_min_max_value_on_decimal(self) -> None:
		class Model(Statica):
			amount: Decimal = Field(min_value=0, max_value=100)

		self.assertEqual(Model(amount=Decimal(50)).amount, Decimal(50))
		with self.assertRaises(ConstraintValidationError):
			Model(amount=Decimal(-1))
		with self.assertRaises(ConstraintValidationError):
			Model(amount=Decimal(101))


if __name__ == "__main__":
	unittest.main()
