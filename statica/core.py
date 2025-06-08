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
from statica.types_utils import get_expected_type
from statica.validators import validate_constraints, validate_type

if TYPE_CHECKING:
	from collections.abc import Callable, Mapping

T = TypeVar("T")


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

	alias: str | None = None
	alias_for_parsing: str | None = None
	alias_for_serialization: str | None = None

	def __set_name__(self, owner: Any, name: str) -> None:
		self.name = name
		self.owner = owner
		self.expected_type = get_expected_type(owner, name)

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

			validate_type(value, self.expected_type)

			if value is not None:
				value = validate_constraints(
					value,
					min_length=self.min_length,
					max_length=self.max_length,
					min_value=self.min_value,
					max_value=self.max_value,
					strip_whitespace=self.strip_whitespace,
				)

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


def get_field_descriptors(cls: type[Statica]) -> list[FieldDescriptor]:
	"""
	Get all Field descriptors for a class.
	Returns a list of FieldDescriptor instances.
	"""

	descriptors = []

	for field_name in cls.__annotations__:
		field_descriptor = getattr(cls, field_name)
		assert isinstance(field_descriptor, FieldDescriptor)
		descriptors.append(field_descriptor)

	return descriptors


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
	alias: str | None = None,
	alias_for_parsing: str | None = None,
	alias_for_serialization: str | None = None,
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
		alias=alias,
		alias_for_parsing=alias_for_parsing,
		alias_for_serialization=alias_for_serialization,
	)

	if TYPE_CHECKING:
		return cast("Any", fd)

	return fd  # type: ignore[unreachable]


########################################################################################
#### MARK: Internal metaclass


@dataclass_transform(kw_only_default=True)
class StaticaMeta(type):
	type_error_class: type[Exception] = TypeValidationError
	constraint_error_class: type[Exception] = ConstraintValidationError

	def __new__(cls, name: str, bases: tuple, namespace: dict[str, Any]) -> type:
		"""
		Set up Field descriptors for each type-hinted attribute which does not have one
		already, but only for subclasses of Statica.
		"""

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
	@classmethod
	def from_map(cls, mapping: Mapping[str, Any]) -> Self:
		mapping_key_to_field_keys = {}  # Maps alias to field name

		for field_descriptor in get_field_descriptors(cls):
			# Use alias for parsing if it exists
			alias = field_descriptor.alias_for_parsing or field_descriptor.alias or field_descriptor.name
			mapping_key_to_field_keys[alias] = field_descriptor.name

		parsed_mapping = {mapping_key_to_field_keys[k]: v for k, v in mapping.items()}

		instance = cls(**parsed_mapping)

		# Go through type hints and set values
		for attribute_name in get_type_hints(instance.__class__):
			value = parsed_mapping.get(attribute_name)
			setattr(instance, attribute_name, value)  # Descriptor __set__ validates

		return instance

	def to_dict(self) -> dict[str, Any]:
		"""
		Convert the instance to a dictionary, using the field names as keys.
		"""
		result = {}
		for field_descriptor in get_field_descriptors(self.__class__):
			# Use alias for serialization if it exists
			alias = field_descriptor.alias_for_serialization or field_descriptor.alias or field_descriptor.name
			result[alias] = getattr(self, field_descriptor.name)

		return result


########################################################################################
#### MARK: Main

if __name__ == "__main__":

	class Payload(Statica):
		type_error_class = ValueError

		name: str = Field(min_length=3, max_length=50, strip_whitespace=True)
		description: str | None = Field(max_length=200)
		num: int | float
		float_num: float | None = Field(alias="floatNum")

	data = {
		"name": "Test Payload",
		"description": "ddf",
		"num": 5,
		"floatNum": 5.5,
	}

	payload = Payload.from_map(data)

	direct_init = Payload(
		name="Test",
		description="This is a test description.",
		num=42,
		float_num=3.14,
	)
