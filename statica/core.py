from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from types import UnionType
from typing import (
	TYPE_CHECKING,
	Any,
	Generic,
	Self,
	TypeVar,
	cast,
	dataclass_transform,
	get_args,
	get_origin,
	get_type_hints,
	overload,
)

from statica.exceptions import ConstraintValidationError, TypeValidationError

if TYPE_CHECKING:
	from collections.abc import Callable, Mapping

T = TypeVar("T")


########################################################################################
#### MARK: Internal functions


def _type_allows_none(expected_type: Any) -> bool:
	"""
	Check if the expected type allows None.

	Examples:
	.. code-block:: python
		_allows_none(int | None)  # True
		_allows_none(int)  # False
	"""
	if isinstance(expected_type, UnionType):
		return type(None) in get_args(expected_type)
	return expected_type is type(None) or expected_type is Any


def _value_matches_type(value: Any | None, expected_type: Any) -> bool:
	"""
	Check if the value matches the expected type.
	Handles basic types, Union types, and generic types.

	Examples:
	.. code-block:: python
		_value_matches_type(1, int)  # True
		_value_matches_type(None, int | None)  # True
		_value_matches_type(None, int)  # False
	"""
	# If expected_type is e.g. int | None, pass if value is None
	if _type_allows_none(expected_type) and value is None:
		return True

	# Basic types like int, str, etc.
	if (origin := get_origin(expected_type)) is None:
		return isinstance(value, expected_type)

	# Handle Union types
	if origin is UnionType or origin is type(None) or origin is Any:
		types = get_args(expected_type)
		return any(_value_matches_type(value, t) for t in types if t is not type(None))

	# Handle generic types
	return isinstance(value, origin)


def _validate_type(value: Any, expected_type: type | UnionType) -> None:
	"""
	Validate that the value matches the expected type.
	Throws TypeValidationError if the type does not match.

	Examples:
	.. code-block:: python
		_validate_type(1, int)  # No exception
		_validate_type("abc", str)  # No exception
		_validate_type(1, str)  # Raises TypeValidationError
		_validate_type(None, int | None)  # No exception
		_validate_type(None, int)  # Raises TypeValidationError
	"""
	if not _value_matches_type(value, expected_type):
		expected_type_str = str(expected_type) if type(expected_type) is UnionType else expected_type.__name__

		msg = f"expected type '{expected_type_str}', got '{type(value).__name__}'"
		raise TypeValidationError(msg)


def _get_expected_type(cls: type, attr_name: str) -> Any:
	"""
	Get the expected type for a class attribute.
	Handles type hints and Field descriptors.

	Examples:
	.. code-block:: python
		class MyClass(Statica):
			age: int | None
			name: str = Field()

		_get_expected_type(MyClass, "age")  # int | None
		_get_expected_type(MyClass, "name")  # str
	"""

	expected_type = get_type_hints(cls).get(attr_name, Any)

	if get_origin(expected_type) is FieldDescriptor:
		return get_args(expected_type)[0]  # Get type from generic

	return expected_type


########################################################################################
#### MARK: Field descriptor


@dataclass
class FieldDescriptor(Generic[T]):
	"""
	Descriptor for validated fields.
	"""

	name: str = dataclass_field(init=False, repr=False)
	owner: type = dataclass_field(init=False, repr=False)
	expected_type: type = dataclass_field(init=False, repr=False)

	min_length: int | None = None
	max_length: int | None = None
	min_value: float | None = None
	max_value: float | None = None
	strip_whitespace: bool | None = None
	cast_to: Callable[..., T] | None = None

	def __set_name__(self, owner: Any, name: str) -> None:
		self.name = name
		self.owner = owner
		self.expected_type = _get_expected_type(owner, name)

	@overload
	def __get__(self, instance: None, owner: Any) -> FieldDescriptor[T]: ...

	@overload
	def __get__(self, instance: object, owner: Any) -> T: ...

	def __get__(self, instance: object | None, owner: Any) -> Any:
		if instance is None:
			return self  # Accessed on the class, return the descriptor
		return instance.__dict__.get(self.name)

	def __set__(self, instance: object, value: T) -> None:
		instance.__dict__[self.name] = self.validate(value)

	def validate(self, value: Any) -> Any:
		try:
			if self.cast_to is not None:
				value = self.cast_to(value)

			_validate_type(value, self.expected_type)

			if value is not None:
				value = self._validate_constraints(value)

		except TypeValidationError as e:
			msg = f"{self.name}: {e!s}"
			error_class = getattr(self.owner, "type_error_class", TypeValidationError)
			raise error_class(msg) from e
		except ConstraintValidationError as e:
			msg = f"{self.name}: {e!s}"
			error_class = getattr(self.owner, "constraint_error_class", ConstraintValidationError)
			raise error_class(msg) from e
		except ValueError as e:
			msg = f"{self.name}: {e!s}"
			raise TypeValidationError(msg) from e
		return value

	def _validate_constraints(self, value: Any) -> Any:
		if self.strip_whitespace and isinstance(value, str):
			value = value.strip()

		if isinstance(value, str | list | tuple | dict):
			if self.min_length is not None and len(value) < self.min_length:
				msg = f"length must be at least {self.min_length}"
				raise ConstraintValidationError(msg)
			if self.max_length is not None and len(value) > self.max_length:
				msg = f"length must be at most {self.max_length}"
				raise ConstraintValidationError(msg)

		if isinstance(value, int | float):
			if self.min_value is not None and value < self.min_value:
				msg = f"must be at least {self.min_value}"
				raise ConstraintValidationError(msg)
			if self.max_value is not None and value > self.max_value:
				msg = f"must be at most {self.max_value}"
				raise ConstraintValidationError(msg)

		return value


########################################################################################
#### MARK: Type-safe field function


def Field(  # noqa: N802
	*,
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
	cast_to: Callable[..., T] | None = None,
) -> Any:
	"""
	Type-safe field function that returns the correct type for type checkers
	but creates a Field descriptor at runtime.
	"""

	fd = FieldDescriptor(
		min_length=min_length,
		max_length=max_length,
		min_value=min_value,
		max_value=max_value,
		strip_whitespace=strip_whitespace,
		cast_to=cast_to,
	)

	if TYPE_CHECKING:
		return cast("Any", fd)

	return fd  # type: ignore[unreachable]


########################################################################################
#### MARK: Internal metaclass


@dataclass_transform(kw_only_default=True)
class StaticaMeta(type):
	def __new__(cls, name: str, bases: tuple, namespace: dict[str, Any]) -> type:
		"""
		Set up Field descriptors for each type-hinted attribute which does not have one
		already, but only for subclasses of Statica.
		"""

		print(f"__new__({name=}, {bases=}, {namespace=})")

		if name == "Statica":
			return super().__new__(cls, name, bases, namespace)

		annotations = namespace.get("__annotations__", {})

		# Generate custom __init__ method

		def custom_init(self: Statica, **kwargs: Any) -> None:
			for field_name, field_type in annotations.items():
				# If it is union type with none continuation, skip it
				if get_origin(field_type) is UnionType and type(None) in get_args(field_type):
					if field_name not in kwargs:
						setattr(self, field_name, None)
					continue

				if field_name not in kwargs:
					msg = f"Missing required field: {field_name}"
					raise TypeValidationError(msg)
				setattr(self, field_name, kwargs[field_name])

		namespace["__init__"] = custom_init

		# Set up Field descriptors for type-hinted attributes

		for attr_annotated in namespace.get("__annotations__", {}):
			existing_value = namespace.get(attr_annotated)

			if isinstance(existing_value, FieldDescriptor):
				# Case 1: name: Field[str] = Field(...) OR name: str = field(...)
				# Both cases work - the Field is already there
				continue

			# Case 3: name: str (no assignment) or name: Field[str] (no assignment)
			# Create a default Field descriptor
			namespace[attr_annotated] = FieldDescriptor()

		return super().__new__(cls, name, bases, namespace)


########################################################################################
#### MARK: Statica base class


class Statica(metaclass=StaticaMeta):
	type_error_class: type[Exception] = TypeValidationError
	constraint_error_class: type[Exception] = ConstraintValidationError

	@classmethod
	def from_map(cls, mapping: Mapping[str, Any]) -> Self:
		instance = cls(**mapping)

		# Go through type hints and set values
		for attribute_name in get_type_hints(instance.__class__):
			value = mapping.get(attribute_name)
			setattr(instance, attribute_name, value)  # Descriptor __set__ validates

		return instance


########################################################################################
#### MARK: Main

if __name__ == "__main__":

	class Payload(Statica):
		type_error_class = ValueError

		name: str = Field(min_length=3, max_length=50, strip_whitespace=True)
		description: str | None = Field(max_length=200)
		num: int | float
		float_num: float | None

	data = {
		"name": "Test Payload",
		"description": "ddf",
		"num": 5,
		"float_num": 5.5,
	}

	payload = Payload.from_map(data)

	direct_init = Payload(
		name="Test",
		description="This is a test description.",
		num=42,
		float_num=3.14,
	)

	class ShortSyntax(Statica):
		name: str = Field(min_length=3, max_length=5, strip_whitespace=True)

	print("Testing ShortSyntax...")
	short = ShortSyntax(name="test")
	print(f"short.name = {short.name}")
