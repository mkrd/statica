from __future__ import annotations

import copy
import sys
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import (
	TYPE_CHECKING,
	Any,
	Generic,
	Self,
	TypeVar,
	dataclass_transform,
	get_type_hints,
	overload,
)

from statica.config import StaticaConfig, default_config
from statica.exceptions import ConstraintValidationError, TypeValidationError
from statica.validation import is_union, validate_constraints, validate_or_raise

if TYPE_CHECKING:
	from collections.abc import Callable, Mapping

T = TypeVar("T")

if sys.version_info >= (3, 14):
	from annotationlib import Format, call_annotate_function, get_annotate_from_class_namespace


def _get_class_annotations(namespace: dict[str, Any]) -> dict[str, Any]:
	"""
	Retrieve the annotations declared in a class body from its namespace.

	Python 3.14 (PEP 749) no longer stores `__annotations__` in the class
	namespace during metaclass creation; the annotate function must instead be
	retrieved via `annotationlib.get_annotate_from_class_namespace`, since the
	key it is stored under in the namespace is an implementation detail. This
	helper supports both the old and new behavior.
	"""

	if sys.version_info >= (3, 14):
		annotate = get_annotate_from_class_namespace(namespace)
		if annotate is not None:
			return call_annotate_function(annotate, Format.FORWARDREF)

	return namespace.get("__annotations__", {})


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

	owner: type[Statica] = dataclass_field(init=False)
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

	statica_sub_class: type[Statica] | None = dataclass_field(init=False, repr=False)
	"""
	Statica subclass if the expected_type is a Statica subclass or a union where one
	of the types is a Statica subclass.
	For example, if expected_type is `Union[Statica, int]`, then this will be `Statica`.
	"""

	# User-facing dataclass fields

	default: T | Any | None = None
	min_length: int | None = None
	max_length: int | None = None
	min_value: float | None = None
	max_value: float | None = None
	strip_whitespace: bool | None = None
	cast_to: Callable[..., T] | None = None

	alias: str | None = None

	def __set_name__(self, owner: Any, name: str) -> None:
		self.name = name
		self.owner = owner
		self.expected_type = get_type_hints(owner)[name]
		self.statica_sub_class = get_statica_subclass(self.expected_type)

	def get_default_safe(self) -> Any:
		"""
		Get the default value of the field, safely handling mutable defaults.
		"""
		if isinstance(self.default, (list, dict, set)):
			return copy.copy(self.default)
		return self.default

	def __get__(self, instance: object | None, owner: Any) -> Any:
		"""
		Get the value of the field from the instance.
		For example user.age will invoke this method.
		"""

		if instance is None:
			return self  # Accessed on the class, return the descriptor
		return instance.__dict__.get(self.name)

	def __set__(self, instance: Statica, value: T) -> None:
		"""
		Set the value of the field on the instance.
		For example user.age = 30 will invoke this method.
		"""

		vars(instance)[self.name] = self.validate(value, type(instance))

	def validate(self, value: Any, model_class: type[Statica]) -> Any:
		"""
		Takes config and error classes from `model_class`, the class of the instance, so a
		field inherited from a parent uses the settings of the child.
		"""

		try:
			config = model_class.__config__

			# (1/4) Cast to required type if cast_to is provided.
			# None marks a missing value, so an optional field stays None.

			if self.cast_to is not None and value is not None:
				try:
					value = self.cast_to(value)
				except (ValueError, TypeError) as e:
					raise TypeValidationError(str(e)) from e

			# (2/4) On dict assignments initialize Statica subclass if it exists

			if self.statica_sub_class is not None and isinstance(value, dict):
				value = self.statica_sub_class.from_map(value)

			# (3/4) Validate type of the value

			validate_or_raise(value, self.expected_type, config=config)

			# (4/4) Validate constraints if any are set

			value = validate_constraints(
				self.name,
				value,
				min_length=self.min_length,
				max_length=self.max_length,
				min_value=self.min_value,
				max_value=self.max_value,
				strip_whitespace=self.strip_whitespace,
				config=config,
			)

		except TypeValidationError as e:
			raise model_class.type_error_class(str(e)) from e

		except ConstraintValidationError as e:
			raise model_class.constraint_error_class(str(e)) from e

		return value


def get_statica_subclass(expected_type: Any) -> type[Statica] | None:
	"""
	Get the first Statica subclass among the union members of the expected type.
	Returns None if no Statica subclass is found.
	"""

	members = expected_type.__args__ if is_union(expected_type) else (expected_type,)

	for member in members:
		# Members like `list[int]` or `Literal["a"]` are not classes, `issubclass` rejects them
		if isinstance(member, type) and issubclass(member, Statica):
			return member
	return None


########################################################################################
#### MARK: Type-safe field function


@overload
def Field(
	*,
	default: T,  # If default is used, the return type is T
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
	cast_to: Callable[..., T] | None = None,
	alias: str | None = None,
) -> T: ...


@overload
def Field(
	*,  # No default provided, return type is Any
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
	cast_to: Callable[..., T] | None = None,
	alias: str | None = None,
) -> Any: ...


def Field(  # noqa: N802
	*,
	default: T | Any | None = None,
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
	cast_to: Callable[..., T] | None = None,
	alias: str | None = None,
) -> Any:
	"""
	Type-safe field function that provides proper type checking for default values
	while creating a FieldDescriptor at runtime.

	When a default value is provided, the return type matches the default's type.
	This prevents type mismatches like: active: bool = Field(default="yes")
	"""
	return FieldDescriptor(
		default=default,
		min_length=min_length,
		max_length=max_length,
		min_value=min_value,
		max_value=max_value,
		strip_whitespace=strip_whitespace,
		cast_to=cast_to,
		alias=alias,
	)


########################################################################################
#### MARK: Internal metaclass


def statica_init(self: Statica, **kwargs: Any) -> None:
	"""The `__init__` of every Statica subclass, set by StaticaMeta."""

	for field_descriptor in type(self).__field_descriptors__:
		if field_descriptor.name in kwargs:
			value = kwargs[field_descriptor.name]
		else:
			value = field_descriptor.get_default_safe()
		setattr(self, field_descriptor.name, value)


@dataclass_transform(kw_only_default=True)
class StaticaMeta(type):
	__config__: StaticaConfig
	__field_descriptors__: list[FieldDescriptor[Any]]
	type_error_class: type[Exception] = TypeValidationError
	constraint_error_class: type[Exception] = ConstraintValidationError

	def __new__(
		cls,
		name: str,
		bases: tuple[type, ...],
		namespace: dict[str, Any],
		*,
		config: StaticaConfig | None = None,
	) -> type:
		"""
		Set up Field descriptors for each type-hinted attribute which does not have one
		already, but only for subclasses of Statica.
		"""

		# The root class Statica has no fields and holds the default config
		if not bases:
			root_field_descriptors: list[FieldDescriptor[Any]] = []
			namespace["__config__"] = default_config
			namespace["__field_descriptors__"] = root_field_descriptors
			return super().__new__(cls, name, bases, namespace)

		# Without an explicit config, the class inherits the config of its parent
		if config is not None:
			namespace["__config__"] = config

		namespace["__init__"] = statica_init

		annotations = _get_class_annotations(namespace)

		# Set up Field descriptors for type-hinted attributes

		for attr_annotated in annotations:
			existing_value = namespace.get(attr_annotated)

			if isinstance(existing_value, FieldDescriptor):
				# A Field() object can be reused for several fields, and __set_name__
				# binds a descriptor to one field, so each field gets its own copy
				namespace[attr_annotated] = copy.copy(existing_value)
				continue

			# A field without Field(), like `name: str` or `timeout: float = 30.0`.
			# The assigned value, if any, becomes the default.
			namespace[attr_annotated] = FieldDescriptor(default=namespace.get(attr_annotated))

		# Collect all fields, parents first. A field redeclared in this class keeps its
		# position and takes this class's descriptor.
		descriptors_by_name: dict[str, FieldDescriptor[Any]] = {}
		for base in reversed(bases):
			if isinstance(base, StaticaMeta):
				descriptors_by_name |= {
					inherited.name: inherited for inherited in base.__field_descriptors__
				}
		descriptors_by_name |= {field_name: namespace[field_name] for field_name in annotations}
		namespace["__field_descriptors__"] = list(descriptors_by_name.values())

		return super().__new__(cls, name, bases, namespace)


########################################################################################
#### MARK: Statica base class


class Statica(metaclass=StaticaMeta):
	@classmethod
	def from_map(cls, mapping: Mapping[str, Any]) -> Self:
		# Fields might have aliases, so we need to map them correctly

		kwargs = {}
		for field_descriptor in cls.__field_descriptors__:
			expected_field_name = field_descriptor.alias or field_descriptor.name

			if expected_field_name in mapping:
				kwargs[field_descriptor.name] = mapping[expected_field_name]

		return cls(**kwargs)  # Init function will validate fields and set defaults

	def to_dict(self, *, with_aliases: bool = True) -> dict[str, Any]:
		"""
		Convert the instance to a dictionary. A field's key is its alias if it has one
		and `with_aliases` is True, otherwise its name.
		"""

		result_dict = {}

		for field_descriptor in type(self).__field_descriptors__:
			key_name = (
				field_descriptor.alias
				if with_aliases and field_descriptor.alias is not None
				else field_descriptor.name
			)

			field_value = getattr(self, field_descriptor.name)

			# If the field is a Statica subclass, convert it to a dict
			if isinstance(field_value, Statica):
				field_value = field_value.to_dict(with_aliases=with_aliases)

			result_dict[key_name] = field_value

		return result_dict
