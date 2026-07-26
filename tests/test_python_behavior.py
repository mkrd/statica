"""
These tests are not meant to test python directly, but rather to document the behavior
of different built-ins.
"""

import unittest
from types import GenericAlias, UnionType


class TestPythonBehavior(unittest.TestCase):
	def test_isinstance_behavior(self) -> None:
		self.assertIsInstance(1, int)
		self.assertIsInstance("abc", str)
		self.assertIsInstance(None, int | None)
		self.assertIsInstance(1, int | None)

		self.assertNotIsInstance(1, str)
		self.assertNotIsInstance("abc", int)
		self.assertNotIsInstance(None, int)
		self.assertNotIsInstance("abc", int | None)

		self.assertIsInstance({"key": 1}, dict)

	def test_parametrized_generic_behavior(self) -> None:
		dict_str_int = dict[str, int]

		self.assertIs(type(dict_str_int), GenericAlias)

		with self.assertRaises(TypeError):
			isinstance({"key": 1}, dict_str_int)  # type: ignore[misc]

		union_with_generic = int | dict[str, int]

		self.assertIs(type(union_with_generic), UnionType)

		# We can't use isinstance for unions, because they might contain generics
		with self.assertRaises(TypeError):
			isinstance({"key": 1}, union_with_generic)
