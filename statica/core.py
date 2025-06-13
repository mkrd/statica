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
	get_type_hints,
)

from statica.exceptions import ConstraintValidationError, TypeValidationError
from statica.validation import validate_constraints, validate_or_raise

if TYPE_CHECKING:
	from collections.abc import Callable, Mapping

T = TypeVar("T")


########################################################################################
#### MARK: Field descriptor


@dataclass(slots=True)
class FieldDescriptor(Generic[T]):
	"""
	Descriptor for statica fields. They will be used to validate fields:

	Example:
	.. code-block:: python
		class User(Statica):
			name: str  # Will be initialized as FieldDescriptor during class creation
			age: int | None = Field(min_value=0, max_value=120)
	"""

	# Descriptor attributes

	name: str = dataclass_field(init=False)
	"""
	Name of the field in the class.
	Example: `"age"` for the field `age: int | None`.
	"""

	owner: type = dataclass_field(init=False)
	"""
	Owner class of the field descriptor.
	Example: `<class '__main__.User'>` for the field `age: int | None`.
	"""

	expected_type: Any = dataclass_field(init=False)
	"""
	Expected type of the field.
	Example 1: `int | None` (of type UnionType) for the field `age: int | None`.
	Example 2: `<class 'int'>` for a field `number: int`.
	"""

	sub_types: tuple[type, ...] = dataclass_field(init=False, default_factory=tuple)
	"""
	List of types that expected_type is composed of.
	If expected_type is not of type UnionType, then it is just a tuple with one element.
	"""

	statica_sub_class: type[Statica] | None = dataclass_field(init=False, repr=False)
	"""
	Statica subclass if the expected_type is a Statica subclass or a union where one
	of the types is a Statica subclass.
	For example, if expected_type is `Union[Statica, int]`, then this will be `Statica`.
	"""

	# User-facing dataclass fields

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
		self.expected_type = get_type_hints(owner)[name]
		self.sub_types = self.get_sub_types(self.expected_type)
		self.statica_sub_class = self.get_statica_subclass(self.sub_types)

	def get_sub_types(self, expected_type: Any) -> tuple[type | Any, ...]:
		"""
		Get all subtypes of the expected type.
		For example, if the expected type is Union[str, int], return [str, int].
		"""

		if type(expected_type) is UnionType:
			return tuple(t for t in expected_type.__args__)

		return (expected_type,)

	def get_statica_subclass(self, sub_types: tuple[type, ...]) -> type[Statica] | None:
		"""
		Get the first Statica subclass from the sub_types.
		Returns None if no Statica subclass is found.
		"""

		try:
			for sub_type in sub_types:
				if issubclass(sub_type, Statica):
					return sub_type
		except TypeError:
			pass
		return None

	def __get__(self, instance: object | None, owner: Any) -> Any:
		"""
		Get the value of the field from the instance.
		For example user.age will invoke this method.
		"""

		if instance is None:
			return self  # Accessed on the class, return the descriptor
		return instance.__dict__.get(self.name)

	def __set__(self, instance: object, value: T) -> None:
		"""
		Set the value of the field on the instance.
		For example user.age = 30 will invoke this method.
		"""

		instance.__dict__[self.name] = self.validate(value)

	def validate(self, value: Any) -> Any:
		try:
			# (1/4) Cast to required type if cast_to is provided

			if self.cast_to is not None:
				value = self.cast_to(value)

			# (2/4) On dict assignments initialize Statica subclass if it exists

			if self.statica_sub_class is not None and isinstance(value, dict):
				value = self.statica_sub_class.from_map(value)

			# (3/4) Validate type of the value

			validate_or_raise(value, self.expected_type)

			# (4/4) Validate constraints if any are set

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

		def statica_init(self: Statica, **kwargs: Any) -> None:
			for field_name in annotations:
				setattr(self, field_name, kwargs.get(field_name))

		namespace["__init__"] = statica_init

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
		# Fields might have aliases, so we need to map them correctly.
		# Here we map the chosen alias to the original field name.
		# If no alias is provided, we use the field name itself.
		# Priority: parsing alias > general alias > field name
		mapping_key_to_field_keys = {}

		for field_descriptor in get_field_descriptors(cls):
			# Use alias for parsing if it exists
			alias = (
				field_descriptor.alias_for_parsing
				or field_descriptor.alias
				or field_descriptor.name
			)
			mapping_key_to_field_keys[alias] = field_descriptor.name

		parsed_mapping = {mapping_key_to_field_keys[k]: v for k, v in mapping.items()}

		return cls(**parsed_mapping)  # Init function will validate fields

	def to_dict(self) -> dict[str, Any]:
		"""
		Convert the instance to a dictionary, using the field names as keys.
		"""
		result = {}
		for field_descriptor in get_field_descriptors(self.__class__):
			# Use alias for serialization if it exists
			alias = (
				field_descriptor.alias_for_serialization
				or field_descriptor.alias
				or field_descriptor.name
			)
			result[alias] = getattr(self, field_descriptor.name)

		return result


########################################################################################
#### MARK: Main

if __name__ == "__main__":

	class User(Statica):
		data: dict[str, int]

	u = User.from_map({})

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
