"""Tests for extended type-validation coverage."""

import unittest
from collections import abc
from typing import Any, Dict, List, Literal, Optional  # noqa: UP035

from statica import Statica, TypeValidationError


class TestTuple(unittest.TestCase):
	def test_fixed_length_tuple(self) -> None:
		class Model(Statica):
			pair: tuple[int, str]

		self.assertEqual(Model(pair=(1, "a")).pair, (1, "a"))

		with self.assertRaises(TypeValidationError):
			Model(pair=(1, 2))  # type: ignore[arg-type]

		with self.assertRaises(TypeValidationError):
			Model(pair=(1,))  # wrong length  # type: ignore[arg-type]

		with self.assertRaises(TypeValidationError):
			Model(pair=(1, "a", "b"))  # wrong length  # type: ignore[arg-type]

	def test_variadic_tuple(self) -> None:
		class Model(Statica):
			nums: tuple[int, ...]

		self.assertEqual(Model(nums=(1, 2, 3)).nums, (1, 2, 3))
		self.assertEqual(Model(nums=()).nums, ())

		with self.assertRaises(TypeValidationError):
			Model(nums=(1, "x"))  # type: ignore[arg-type]

	def test_empty_tuple(self) -> None:
		class Model(Statica):
			empty: tuple[()]

		self.assertEqual(Model(empty=()).empty, ())

		with self.assertRaises(TypeValidationError):
			Model(empty=(1,))  # type: ignore[arg-type]

	def test_non_tuple_rejected(self) -> None:
		class Model(Statica):
			nums: tuple[int, ...]

		with self.assertRaises(TypeValidationError):
			Model(nums=[1, 2, 3])  # type: ignore[arg-type]


class TestFrozenset(unittest.TestCase):
	def test_frozenset(self) -> None:
		class Model(Statica):
			data: frozenset[int]

		result = Model(data=frozenset([1, 2, 3]))
		self.assertEqual(result.data, frozenset([1, 2, 3]))
		self.assertIsInstance(result.data, frozenset)

		with self.assertRaises(TypeValidationError):
			Model(data=frozenset(["a"]))  # type: ignore[arg-type]


class TestAbcContainers(unittest.TestCase):
	def test_sequence(self) -> None:
		class Model(Statica):
			items: abc.Sequence[int]

		self.assertEqual(list(Model(items=[1, 2, 3]).items), [1, 2, 3])
		self.assertEqual(list(Model(items=(1, 2, 3)).items), [1, 2, 3])

		with self.assertRaises(TypeValidationError):
			Model(items=[1, "x"])  # type: ignore[arg-type]

	def test_mapping(self) -> None:
		class Model(Statica):
			data: abc.Mapping[str, int]

		self.assertEqual(dict(Model(data={"a": 1}).data), {"a": 1})

		with self.assertRaises(TypeValidationError):
			Model(data={"a": "x"})  # type: ignore[arg-type]

		with self.assertRaises(TypeValidationError):
			Model(data={1: 1})  # type: ignore[arg-type]

	def test_set_and_collection(self) -> None:
		class Model(Statica):
			s: abc.Set[int]
			c: abc.Collection[int]

		m = Model(s={1, 2}, c=[1, 2, 3])
		self.assertEqual(set(m.s), {1, 2})

		with self.assertRaises(TypeValidationError):
			Model(s={"x"}, c=[1])  # type: ignore[arg-type]

	def test_str_rejected_for_sequence(self) -> None:
		class Model(Statica):
			items: abc.Sequence[int]

		with self.assertRaises(TypeValidationError):
			Model(items="abc")  # type: ignore[arg-type]

	def test_bare_iterable_rejected(self) -> None:
		class Model(Statica):
			it: abc.Iterable[int]

		with self.assertRaisesRegex(TypeValidationError, r"unsupported"):
			Model(it=[1, 2, 3])


class TestOldStyleTypingAliases(unittest.TestCase):
	"""typing.List / typing.Dict must validate, not crash."""

	def test_typing_list(self) -> None:
		class Model(Statica):
			items: List[int]  # noqa: UP006

		self.assertEqual(Model(items=[1, 2]).items, [1, 2])
		with self.assertRaises(TypeValidationError):
			Model(items=["x"])  # type: ignore[list-item]

	def test_typing_dict(self) -> None:
		class Model(Statica):
			data: Dict[str, int]  # noqa: UP006

		self.assertEqual(Model(data={"a": 1}).data, {"a": 1})
		with self.assertRaises(TypeValidationError):
			Model(data={"a": "x"})  # type: ignore[dict-item]


class TestAlreadySupported(unittest.TestCase):
	"""Lock behavior of Optional / Literal / Any (documented, previously untested)."""

	def test_optional_old_style(self) -> None:
		class Model(Statica):
			x: Optional[int]  # noqa: UP045

		self.assertIsNone(Model(x=None).x)
		self.assertEqual(Model(x=5).x, 5)
		with self.assertRaises(TypeValidationError):
			Model(x="bad")  # type: ignore[arg-type]

	def test_any_accepts_everything(self) -> None:
		class Model(Statica):
			x: Any

		self.assertEqual(Model(x="anything").x, "anything")
		self.assertEqual(Model(x=[1, 2]).x, [1, 2])
		self.assertIsNone(Model(x=None).x)

	def test_literal(self) -> None:
		class Model(Statica):
			mode: Literal["r", "w"]

		self.assertEqual(Model(mode="r").mode, "r")
		with self.assertRaises(TypeValidationError):
			Model(mode="x")  # type: ignore[arg-type]


if __name__ == "__main__":
	unittest.main()
