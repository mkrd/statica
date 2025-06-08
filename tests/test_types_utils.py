from typing import Generic, TypeVar

from statica.types_utils import type_allows_none, value_matches_type


def test_allows_none() -> None:
	assert type_allows_none(type(None))
	assert type_allows_none(int | None)
	assert not type_allows_none(int)


def test_value_matches_type() -> None:
	assert value_matches_type(1, int)
	assert value_matches_type("abc", str)
	assert not value_matches_type(1, str)
	assert value_matches_type(None, int | None)
	assert value_matches_type(1, int | None)
	assert not value_matches_type(None, int)
	assert value_matches_type(1, int | None)
	assert not value_matches_type("abc", int | None)

	# Test with generics

	T = TypeVar("T")

	class GenericTest(Generic[T]):
		value: T

		def __init__(self, value: T) -> None:
			self.value = value

	assert value_matches_type(GenericTest[int](1), GenericTest[int])
	assert value_matches_type(GenericTest[int](1), GenericTest[str])  # Is this correct?
