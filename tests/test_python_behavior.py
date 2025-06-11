"""
These tests are not meant to test python directly, but rather to document the behavior
of different built-ins.
"""

from types import GenericAlias, UnionType

import pytest


def test_isinstance_behavior() -> None:
	assert isinstance(1, int)
	assert isinstance("abc", str)
	assert isinstance(None, int | None)
	assert isinstance(1, int | None)

	assert not isinstance(1, str)
	assert not isinstance("abc", int)
	assert not isinstance(None, int)
	assert not isinstance("abc", int | None)

	assert isinstance({"key": 1}, dict)


def test_parametrized_generic_behavior() -> None:
	dict_str_int = dict[str, int]

	assert type(dict_str_int) is GenericAlias

	with pytest.raises(TypeError):
		isinstance({"key": 1}, dict_str_int)  # type: ignore[misc]

	union_with_generic = int | dict[str, int]

	assert type(union_with_generic) is UnionType

	# We can't use isinstance for unions, because they might contain generics
	with pytest.raises(TypeError):
		isinstance({"key": 1}, union_with_generic)
