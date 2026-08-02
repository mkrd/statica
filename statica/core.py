from __future__ import annotations

import copy
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import Enum
from typing import (
	TYPE_CHECKING,
	Any,
	Generic,
	NoReturn,
	Self,
	TypeVar,
	dataclass_transform,
	get_type_hints,
	overload,
)

from statica.config import StaticaConfig, default_config
from statica.exceptions import (
	ConstraintValidationError,
	FrozenInstanceError,
	TypeValidationError,
	ValidationError,
)
from statica.validation import validate_constraints, validate_or_raise

if TYPE_CHECKING:
	from collections.abc import Callable, Mapping

T = TypeVar("T")

try:
	from annotationlib import (
		Format,  # type: ignore[missing-module-attribute]
		call_annotate_function,  # type: ignore[missing-module-attribute]
		get_annotate_from_class_namespace,  # type: ignore[missing-module-attribute]
	)
except ImportError:  # Python < 3.14 has no annotationlib
	Format, call_annotate_function, get_annotate_from_class_namespace = None, None, None


#: Sentinel marking a class argument as "not provided", so it can be inherited.
_UNSET: Any = object()

#: Sentinel marking a field's expected type as not yet resolved.
_UNRESOLVED: Any = object()


def _get_class_annotations(namespace: dict[str, Any]) -> dict[str, Any]:
	"""
	Retrieve the annotations declared in a class body from its namespace.

	Python 3.14 (PEP 749) no longer stores `__annotations__` in the class
	namespace during metaclass creation; the annotate function must instead be
	retrieved via `annotationlib.get_annotate_from_class_namespace`, since the
	key it is stored under in the namespace is an implementation detail. This
	helper supports both the old and new behavior.
	"""

	if (
		Format is not None
		and call_annotate_function is not None
		and get_annotate_from_class_namespace is not None
	):
		annotate = get_annotate_from_class_namespace(namespace)
		if annotate is not None:
			return call_annotate_function(annotate, Format.FORWARDREF)

	return namespace.get("__annotations__", {})


########################################################################################
#### MARK: Field descriptor


def _reraise_as(error: ValidationError, error_class: type[Exception]) -> NoReturn:
	"""
	Re-raise a validation error as the class configured on the owner model.

	If the target class is a `ValidationError` subclass, the structured location
	(`loc`/`root`) is preserved so nested paths still compose into a single path
	(e.g. `Book.account.code`). Otherwise the message, which already contains the
	rendered path, is baked into the new exception.
	"""

	if isinstance(error, error_class):
		raise error
	if issubclass(error_class, ValidationError):
		raise error_class(error.message, loc=error.loc, root=error.root) from error
	raise error_class(str(error)) from error


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
	Owner class of the field descriptor (the class the field is declared on).
	"""

	_resolved_type: Any = dataclass_field(init=False, default=_UNRESOLVED, repr=False)
	"""Cache for the lazily-resolved `expected_type` (see the property below)."""

	# User-facing dataclass fields

	default: T | Any | None = None
	min_length: int | None = None
	max_length: int | None = None
	min_value: float | None = None
	max_value: float | None = None
	strip_whitespace: bool | None = None
	cast_to: Callable[..., T] | None = None
	validator: Callable[[Any], Any] | None = None
	serializer: Callable[[Any], Any] | None = None

	alias: str | None = None

	def __set_name__(self, owner: Any, name: str) -> None:
		self.name = name
		self.owner = owner
		# `expected_type` is resolved lazily (see the property) rather than here,
		# so that self-referential and forward-referenced models work: at class
		# creation time the class is not yet bound in its module namespace.

	@property
	def expected_type(self) -> Any:
		"""
		Expected type of the field, resolved lazily from the owner's annotations.

		Example 1: `int | None` (of type UnionType) for the field `age: int | None`.
		Example 2: `<class 'int'>` for a field `number: int`.
		"""
		if self._resolved_type is _UNRESOLVED:
			self._resolved_type = get_type_hints(self.owner)[self.name]
		return self._resolved_type

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

		instance.__dict__[self.name] = self.validate(value, type(instance))

	def _run_validator(self, value: Any) -> Any:
		assert self.validator is not None
		try:
			return self.validator(value)
		except (TypeValidationError, ConstraintValidationError) as e:
			if not e.loc:
				e.loc = [self.name]
			raise
		except ValueError as e:
			raise ConstraintValidationError(str(e), loc=[self.name]) from e

	def validate(self, value: Any, owner: type[Statica]) -> Any:
		config: StaticaConfig = owner.__config__

		try:
			# (1) Cast to required type if cast_to is provided. A failing cast is a
			# type error; this is scoped narrowly so it does not swallow ValueErrors
			# raised by nested models' __post_init__ (which must propagate as-is).
			if self.cast_to is not None:
				try:
					value = self.cast_to(value)
				except (ValueError, TypeError) as e:
					raise TypeValidationError(str(e), loc=[self.name]) from e

			# (2) Validate type (also coerces codecs/enums and builds nested models)
			value = validate_or_raise(value, self.expected_type, config, (self.name,))

			# (3) Validate constraints if any are set
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

			# (4) Run the custom field validator last, on a well-typed value
			if self.validator is not None:
				value = self._run_validator(value)

		except TypeValidationError as e:
			e.root = owner.__name__
			_reraise_as(e, getattr(owner, "type_error_class", TypeValidationError))

		except ConstraintValidationError as e:
			e.root = owner.__name__
			_reraise_as(e, getattr(owner, "constraint_error_class", ConstraintValidationError))

		return value


def get_field_descriptors(cls: type[Statica]) -> list[FieldDescriptor[Any]]:
	"""
	Get all Field descriptors for a class, including inherited ones.

	The list is computed once by the metaclass at class-creation time and cached
	as `__field_descriptors__` (base fields first, then own fields), so repeated
	calls (e.g. from `from_map` or `to_dict`) don't need to rescan the class.
	"""

	return cls.__field_descriptors__


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
	validator: Callable[[Any], Any] | None = None,
	serializer: Callable[[Any], Any] | None = None,
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
	validator: Callable[[Any], Any] | None = None,
	serializer: Callable[[Any], Any] | None = None,
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
	validator: Callable[[Any], Any] | None = None,
	serializer: Callable[[Any], Any] | None = None,
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
		validator=validator,
		serializer=serializer,
		alias=alias,
	)


########################################################################################
#### MARK: Generated methods


def _statica_init(self: Statica, **kwargs: Any) -> None:
	cls = type(self)
	instance_dict = self.__dict__

	for field_descriptor in cls.__field_descriptors__:
		name = field_descriptor.name

		if name in kwargs:
			raw_value = kwargs[name]
		elif field_descriptor.default is not None:
			raw_value = field_descriptor.get_default_safe()
		else:
			raw_value = None

		# Write straight to __dict__ so frozen instances can still be initialized.
		instance_dict[name] = field_descriptor.validate(raw_value, cls)

	post_init = getattr(cls, "__post_init__", None)
	if post_init is not None:
		post_init(self)


def _field_values(obj: Any) -> tuple[Any, ...]:
	"""Tuple of all field values, used for eq/order/hash."""

	return tuple(getattr(obj, fd.name) for fd in type(obj).__field_descriptors__)


def _statica_eq(self: Statica, other: object) -> Any:
	if other.__class__ is not self.__class__:
		return NotImplemented
	return _field_values(self) == _field_values(other)


def _statica_hash(self: Statica) -> int:
	return hash(_field_values(self))


def _statica_lt(self: Statica, other: object) -> Any:
	if other.__class__ is not self.__class__:
		return NotImplemented
	return _field_values(self) < _field_values(other)


def _statica_le(self: Statica, other: object) -> Any:
	if other.__class__ is not self.__class__:
		return NotImplemented
	return _field_values(self) <= _field_values(other)


def _statica_gt(self: Statica, other: object) -> Any:
	if other.__class__ is not self.__class__:
		return NotImplemented
	return _field_values(self) > _field_values(other)


def _statica_ge(self: Statica, other: object) -> Any:
	if other.__class__ is not self.__class__:
		return NotImplemented
	return _field_values(self) >= _field_values(other)


def _make_frozen_setattr(action: str) -> Callable[..., None]:
	def _frozen(self: object, name: str, *_: Any) -> None:
		msg = f"cannot {action} field {name!r} of frozen instance {type(self).__name__!r}"
		raise FrozenInstanceError(msg)

	return _frozen


########################################################################################
#### MARK: Internal metaclass


def _resolve(value: Any, bases: tuple[type, ...], attr: str, *, default: Any) -> Any:
	"""Resolve a class argument, inheriting from the nearest base when unset."""

	if value is not _UNSET:
		return value
	for base in bases:
		if hasattr(base, attr):
			return getattr(base, attr)
	return default


def _collect_field_descriptors(
	bases: tuple[type, ...],
	own: dict[str, FieldDescriptor[Any]],
) -> list[FieldDescriptor[Any]]:
	"""Merge inherited field descriptors (base-first) with own fields."""

	merged: dict[str, FieldDescriptor[Any]] = {}
	for base in reversed(bases):
		for field_descriptor in getattr(base, "__field_descriptors__", []):
			merged[field_descriptor.name] = field_descriptor
	merged.update(own)
	return list(merged.values())


@dataclass_transform(
	eq_default=True,
	order_default=False,
	kw_only_default=True,
	frozen_default=False,
)
class StaticaMeta(type):
	__config__: StaticaConfig
	__field_descriptors__: list[FieldDescriptor[Any]]
	__statica_init__: bool
	__statica_frozen__: bool
	__statica_eq__: bool
	__statica_order__: bool
	type_error_class: type[Exception] = TypeValidationError
	constraint_error_class: type[Exception] = ConstraintValidationError

	def __new__(
		cls,
		name: str,
		bases: tuple[type, ...],
		namespace: dict[str, Any],
		*,
		config: StaticaConfig = _UNSET,
		init: bool = _UNSET,
		frozen: bool = _UNSET,
		eq: bool = _UNSET,
		order: bool = _UNSET,
	) -> type:
		"""
		Set up Field descriptors for each type-hinted attribute which does not have one
		already, but only for subclasses of Statica.
		"""

		if name == "Statica":
			return super().__new__(cls, name, bases, namespace)

		# Resolve class arguments, inheriting from the nearest base when unset.
		config = _resolve(config, bases, "__config__", default=default_config)
		init = _resolve(init, bases, "__statica_init__", default=True)
		frozen = _resolve(frozen, bases, "__statica_frozen__", default=False)
		eq = _resolve(eq, bases, "__statica_eq__", default=True)
		order = _resolve(order, bases, "__statica_order__", default=False)

		namespace["__config__"] = config
		namespace["__statica_init__"] = init
		namespace["__statica_frozen__"] = frozen
		namespace["__statica_eq__"] = eq
		namespace["__statica_order__"] = order

		annotations = _get_class_annotations(namespace)

		# Set up Field descriptors for type-hinted attributes without one.
		own_fields: dict[str, FieldDescriptor[Any]] = {}
		for attr_annotated in annotations:
			existing_value = namespace.get(attr_annotated)
			if not isinstance(existing_value, FieldDescriptor):
				existing_value = FieldDescriptor(default=existing_value)
				namespace[attr_annotated] = existing_value
			own_fields[attr_annotated] = existing_value

		namespace["__field_descriptors__"] = _collect_field_descriptors(bases, own_fields)

		# Generate the __init__ method (unless the user opted out).
		if init:
			namespace["__init__"] = _statica_init

		# Frozen instances block attribute mutation after initialization.
		if frozen:
			namespace["__setattr__"] = _make_frozen_setattr("assign to")
			namespace["__delattr__"] = _make_frozen_setattr("delete")
		elif any(getattr(base, "__statica_frozen__", False) for base in bases):
			# A frozen base would otherwise leak its blocking __setattr__/__delattr__.
			namespace.setdefault("__setattr__", object.__setattr__)
			namespace.setdefault("__delattr__", object.__delattr__)

		# Value-based equality and hashing (mirrors dataclasses' rules).
		if eq:
			namespace["__eq__"] = _statica_eq
			namespace["__hash__"] = _statica_hash if frozen else None

		# Ordering operators.
		if order:
			namespace["__lt__"] = _statica_lt
			namespace["__le__"] = _statica_le
			namespace["__gt__"] = _statica_gt
			namespace["__ge__"] = _statica_ge

		return super().__new__(cls, name, bases, namespace)


########################################################################################
#### MARK: Statica base class


class Statica(metaclass=StaticaMeta):
	@classmethod
	def from_map(cls, mapping: Mapping[str, Any]) -> Self:
		# Fields might have aliases, so we need to map them correctly

		kwargs = {}
		for field_descriptor in get_field_descriptors(cls):
			expected_field_name = field_descriptor.alias or field_descriptor.name

			if expected_field_name in mapping:
				kwargs[field_descriptor.name] = mapping[expected_field_name]

		return cls(**kwargs)  # Init function will validate fields and set defaults

	def to_dict(self, *, with_aliases: bool = True) -> dict[str, Any]:
		"""
		Convert the instance to a dictionary, using the field names as keys.

		Args:
		- `with_aliases`: If True, use field aliases as keys if they exist.
		Otherwise, use the field names.
		"""

		cls = type(self)
		config: StaticaConfig = cls.__config__
		result_dict: dict[str, Any] = {}

		for field_descriptor in get_field_descriptors(cls):
			key_name = (
				field_descriptor.alias
				if with_aliases and field_descriptor.alias is not None
				else field_descriptor.name
			)

			field_value = getattr(self, field_descriptor.name)

			if field_descriptor.serializer is not None:
				result_dict[key_name] = field_descriptor.serializer(field_value)
			else:
				result_dict[key_name] = _serialize_value(
					field_value,
					config,
					with_aliases=with_aliases,
				)

		return result_dict


def _serialize_value(value: Any, config: StaticaConfig, *, with_aliases: bool) -> Any:
	"""Recursively convert a field value into a JSON-friendly representation."""

	if isinstance(value, Statica):
		return value.to_dict(with_aliases=with_aliases)

	if isinstance(value, (list, tuple, set, frozenset)):
		return [_serialize_value(item, config, with_aliases=with_aliases) for item in value]

	if isinstance(value, dict):
		return {
			key: _serialize_value(item, config, with_aliases=with_aliases)
			for key, item in value.items()
		}

	if isinstance(value, Enum):
		return value.value

	codec = config.codecs.get(type(value))
	if codec is not None:
		return codec.encode(value)

	return value
