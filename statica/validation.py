"""
The backus naur grammar for supported types is as follows:
T ::= Statica
	| Any
	| int | float | str | bool | None
	| datetime | date | time | UUID | Decimal | <Enum subclass>
	| (T1 | T2)                 # union, both `X | Y` and typing.Union / Optional
	| list[T] | set[T] | frozenset[T]
	| tuple[T, ...] | tuple[T1, T2, ...] | tuple[()]
	| dict[T1, T2]
	| Literal[V1, ...]
	| Sequence[T] | Mapping[T1, T2] | Set[T] | Collection[T] | Container[T]
	| (and their Mutable* variants)

Notes:
- Coercion (codecs for datetime/UUID/... and Enum) happens during validation and
  is applied recursively for concrete containers, so `list[datetime]` decodes each
  item. `validate_or_raise` therefore returns the (possibly coerced) value.
- Abstract (collections.abc) containers are validated but their items are NOT
  coerced/rebuilt, since the concrete result type is unknown.
- str/bytes are rejected for abstract containers to avoid per-character validation.
"""

from __future__ import annotations

from collections import abc
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any, Literal, NoReturn, Union, get_args, get_origin

from statica.config import StaticaConfig, default_config
from statica.exceptions import ConstraintValidationError, TypeValidationError

########################################################################################
#### MARK: Statica base (lazy import to avoid a cycle with statica.core)


_statica_base: type | None = None


def _get_statica_base() -> type:
	global _statica_base  # noqa: PLW0603
	if _statica_base is None:
		from statica.core import Statica  # noqa: PLC0415

		_statica_base = Statica
	return _statica_base


def _is_statica_type(expected_type: Any) -> bool:
	if not isinstance(expected_type, type):
		return False
	return issubclass(expected_type, _get_statica_base())


########################################################################################
#### MARK: Abstract container classification


_ABC_MAPPINGS: tuple[type, ...] = (abc.Mapping, abc.MutableMapping)
_ABC_ITERABLE_CONTAINERS: tuple[type, ...] = (
	abc.Sequence,
	abc.MutableSequence,
	abc.Set,
	abc.MutableSet,
	abc.Collection,
)
_ABC_ISINSTANCE_ONLY: tuple[type, ...] = (abc.Container,)
_ABC_REJECTED: tuple[type, ...] = (
	abc.Iterable,
	abc.Iterator,
	abc.Generator,
	abc.Reversible,
	abc.AsyncIterable,
	abc.AsyncIterator,
	abc.AsyncGenerator,
)


########################################################################################
#### MARK: Helpers


def _type_name(expected_type: Any) -> str:
	return getattr(expected_type, "__name__", None) or str(expected_type)


def _raise_type_error(
	expected_name: str,
	value: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
	*,
	cause: BaseException | None = None,
) -> NoReturn:
	msg = config.type_error_message.format(
		expected_type=expected_name,
		found_type=type(value).__name__,
	)
	raise TypeValidationError(msg, loc=list(loc)) from cause


########################################################################################
#### MARK: Type Validation


def validate_or_raise(  # noqa: PLR0911
	value: Any,
	expected_type: Any,
	config: StaticaConfig = default_config,
	loc: tuple[str, ...] = (),
) -> Any:
	"""
	Validate `value` against `expected_type`, returning the (possibly coerced)
	value. Raises TypeValidationError on mismatch.
	"""

	# Handle typing.Any, which accepts any value

	if expected_type is Any:
		return value

	origin = get_origin(expected_type)

	# Handle unions: both `X | Y` (UnionType) and typing.Union / typing.Optional

	if origin is Union or origin is UnionType or isinstance(expected_type, UnionType):
		return _validate_union(value, expected_type, config, loc)

	# Handle Literal[...]

	if origin is Literal:
		_validate_literal(value, expected_type, loc)
		return value

	# Handle parameterized generics (list[int], dict[str, int], Sequence[int], ...)

	if origin is not None:
		return _validate_generic(value, expected_type, origin, config, loc)

	# Handle Enum subclasses (decode from the member value if needed)

	if isinstance(expected_type, type) and issubclass(expected_type, Enum):
		return _coerce_enum(value, expected_type, config, loc)

	# Handle codec-backed types (datetime, UUID, Decimal, ...)

	if isinstance(expected_type, type):
		codec = config.codecs.get(expected_type)
		if codec is not None:
			return _coerce_codec(value, expected_type, codec, config, loc)

	# Handle nested Statica models

	if _is_statica_type(expected_type):
		return _validate_statica(value, expected_type, config, loc)

	# Handle all other (plain) types

	if isinstance(value, expected_type):
		return value

	_raise_type_error(_type_name(expected_type), value, config, loc)


def _validate_union(
	value: Any,
	expected_type: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	args = get_args(expected_type)
	for sub_type in args:
		try:
			return validate_or_raise(value, sub_type, config, loc)
		except (TypeValidationError, ConstraintValidationError):
			continue

	expected_name = " | ".join(_type_name(a) for a in args)
	_raise_type_error(expected_name, value, config, loc)


def _validate_literal(
	value: Any,
	expected_type: Any,
	loc: tuple[str, ...],
) -> None:
	args = get_args(expected_type)
	if value not in args:
		msg = f"expected one of {args}, got {value!r}"
		raise TypeValidationError(msg, loc=list(loc))


def _coerce_codec(
	value: Any,
	expected_type: type,
	codec: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	if isinstance(value, expected_type):
		return value
	try:
		return codec.decode(value)
	except (ValueError, TypeError, ArithmeticError) as e:
		# ValueError: datetime.fromisoformat / UUID; ArithmeticError: Decimal.
		_raise_type_error(expected_type.__name__, value, config, loc, cause=e)


def _coerce_enum(
	value: Any,
	enum_cls: type[Enum],
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	if isinstance(value, enum_cls):
		return value
	try:
		return enum_cls(value)
	except ValueError as e:
		_raise_type_error(enum_cls.__name__, value, config, loc, cause=e)


def _validate_statica(
	value: Any,
	expected_type: type,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	if isinstance(value, expected_type):
		return value
	if isinstance(value, dict):
		try:
			return expected_type.from_map(value)  # type: ignore[attr-defined]
		except (TypeValidationError, ConstraintValidationError) as e:
			e.loc = list(loc) + e.loc
			raise
	_raise_type_error(expected_type.__name__, value, config, loc)


########################################################################################
#### MARK: Generic alias validation


def _validate_generic(
	value: Any,
	expected_type: Any,
	origin: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	args = get_args(expected_type)

	if origin is list:
		return _validate_list(value, args[0], config, loc)
	if origin is set:
		return _validate_set(value, set, args[0], config, loc)
	if origin is frozenset:
		return _validate_set(value, frozenset, args[0], config, loc)
	if origin is tuple:
		return _validate_tuple(value, args, config, loc)
	if origin is dict:
		return _validate_dict(value, args[0], args[1], config, loc)

	return _validate_abc(value, origin, args, config, loc)


def _validate_list(
	value: Any,
	item_type: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> list[Any]:
	if not isinstance(value, list):
		_raise_type_error(f"list[{_type_name(item_type)}]", value, config, loc)
	return [
		validate_or_raise(item, item_type, config, (*loc, f"[{i}]")) for i, item in enumerate(value)
	]


def _validate_set(
	value: Any,
	target: type,
	item_type: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	if not isinstance(value, target):
		_raise_type_error(f"{target.__name__}[{_type_name(item_type)}]", value, config, loc)
	return target(
		validate_or_raise(item, item_type, config, (*loc, f"{{{item!r}}}")) for item in value
	)


def _validate_tuple(
	value: Any,
	args: tuple[Any, ...],
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> tuple[Any, ...]:
	if not isinstance(value, tuple):
		_raise_type_error(f"tuple[{', '.join(_type_name(a) for a in args)}]", value, config, loc)

	# Empty tuple: tuple[()]
	if args == ():
		if len(value) != 0:
			msg = f"expected empty tuple, got tuple of length {len(value)}"
			raise TypeValidationError(msg, loc=list(loc))
		return value

	# Variadic tuple: tuple[T, ...]
	if len(args) == 2 and args[1] is Ellipsis:  # noqa: PLR2004
		item_type = args[0]
		return tuple(
			validate_or_raise(item, item_type, config, (*loc, f"[{i}]"))
			for i, item in enumerate(value)
		)

	# Fixed-length tuple: tuple[T1, T2, ...]
	if len(value) != len(args):
		msg = f"expected tuple of length {len(args)}, got length {len(value)}"
		raise TypeValidationError(msg, loc=list(loc))
	return tuple(
		validate_or_raise(item, arg, config, (*loc, f"[{i}]"))
		for i, (item, arg) in enumerate(zip(value, args, strict=True))
	)


def _validate_dict(
	value: Any,
	key_type: Any,
	value_type: Any,
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> dict[Any, Any]:
	if not isinstance(value, dict):
		expected = f"dict[{_type_name(key_type)}, {_type_name(value_type)}]"
		_raise_type_error(expected, value, config, loc)

	result: dict[Any, Any] = {}
	for key, val in value.items():
		new_key = validate_or_raise(key, key_type, config, (*loc, f"<key {key!r}>"))
		new_val = validate_or_raise(val, value_type, config, (*loc, f"[{key!r}]"))
		result[new_key] = new_val
	return result


def _validate_abc(  # noqa: C901
	value: Any,
	origin: Any,
	args: tuple[Any, ...],
	config: StaticaConfig,
	loc: tuple[str, ...],
) -> Any:
	if origin in _ABC_REJECTED:
		msg = (
			f"unsupported type '{_type_name(origin)}': items cannot be validated "
			f"without consuming the iterable"
		)
		raise TypeValidationError(msg, loc=list(loc))

	# str/bytes technically satisfy Sequence/Collection/Container; reject them so
	# that Sequence[int] does not silently accept a string and validate characters.
	if isinstance(value, (str, bytes)):
		_raise_type_error(f"{_type_name(origin)}[...]", value, config, loc)

	if origin in _ABC_MAPPINGS:
		if not isinstance(value, abc.Mapping):
			_raise_type_error(f"{_type_name(origin)}[...]", value, config, loc)
		key_type, value_type = args
		for key, val in value.items():
			validate_or_raise(key, key_type, config, (*loc, f"<key {key!r}>"))
			validate_or_raise(val, value_type, config, (*loc, f"[{key!r}]"))
		return value

	if origin in _ABC_ISINSTANCE_ONLY:
		if not isinstance(value, origin):
			_raise_type_error(f"{_type_name(origin)}[...]", value, config, loc)
		return value

	if origin in _ABC_ITERABLE_CONTAINERS:
		# Validate each item, but do not coerce/rebuild: the concrete type is unknown.
		if not isinstance(value, origin):
			_raise_type_error(f"{_type_name(origin)}[...]", value, config, loc)
		item_type = args[0]
		for i, item in enumerate(value):
			validate_or_raise(item, item_type, config, (*loc, f"[{i}]"))
		return value

	msg = f"unsupported type '{_type_name(origin)}'"
	raise TypeValidationError(msg, loc=list(loc))


########################################################################################
#### MARK: Constraint Validation


def validate_constraints(
	field_name: str,
	value: Any,
	*,
	min_length: int | None = None,
	max_length: int | None = None,
	min_value: float | None = None,
	max_value: float | None = None,
	strip_whitespace: bool | None = None,
	config: StaticaConfig = default_config,
) -> Any:
	"""
	Apply constraint checks to `value`, returning the (possibly stripped) value.

	Length constraints apply to str/list/tuple/dict/set; value constraints apply
	to int/float/Decimal. Raises ConstraintValidationError on violation. The field
	name is carried as the error location so the full path can be rendered.
	"""

	# For performance, exit early if no constraints are provided
	if (
		min_length is None
		and max_length is None
		and min_value is None
		and max_value is None
		and strip_whitespace is None
	):
		return value

	if strip_whitespace and isinstance(value, str):
		value = value.strip()

	loc = [field_name]

	if isinstance(value, (str, list, tuple, dict, set, frozenset)):
		if min_length is not None and len(value) < min_length:
			msg = config.min_length_error_message.format(
				field_name=field_name,
				min_length=min_length,
			)
			raise ConstraintValidationError(msg, loc=loc)
		if max_length is not None and len(value) > max_length:
			msg = config.max_length_error_message.format(
				field_name=field_name,
				max_length=max_length,
			)
			raise ConstraintValidationError(msg, loc=loc)

	if isinstance(value, (int, float, Decimal)):
		if min_value is not None and value < min_value:
			msg = config.min_value_error_message.format(
				field_name=field_name,
				min_value=min_value,
			)
			raise ConstraintValidationError(msg, loc=loc)
		if max_value is not None and value > max_value:
			msg = config.max_value_error_message.format(
				field_name=field_name,
				max_value=max_value,
			)
			raise ConstraintValidationError(msg, loc=loc)

	return value
