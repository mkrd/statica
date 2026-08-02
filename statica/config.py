from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
	from collections.abc import Callable, Mapping


@dataclass(frozen=True, slots=True)
class Codec:
	"""
	A pair of functions describing how to convert a value of a specific type
	to and from a JSON-friendly representation.

	`decode` is called on input (e.g. a string from `from_map`) to produce the
	typed value; it is only invoked when the value is not already the target type.
	`encode` is called by `to_dict` to produce a JSON-friendly value.
	"""

	decode: Callable[[Any], Any]
	encode: Callable[[Any], Any]


def _decode_uuid(value: Any) -> UUID:
	return value if isinstance(value, UUID) else UUID(value)


DEFAULT_CODECS: dict[type, Codec] = {
	datetime: Codec(decode=datetime.fromisoformat, encode=lambda v: v.isoformat()),
	date: Codec(decode=date.fromisoformat, encode=lambda v: v.isoformat()),
	time: Codec(decode=time.fromisoformat, encode=lambda v: v.isoformat()),
	UUID: Codec(decode=_decode_uuid, encode=str),
	Decimal: Codec(decode=Decimal, encode=str),
}
"""
Built-in codecs for common types that are not natively JSON-serializable.
Users can extend or override these per config via `StaticaConfig.create(codecs=...)`.
"""


@dataclass(frozen=True, slots=True)
class StaticaConfig:
	type_error_message: str
	min_length_error_message: str
	max_length_error_message: str
	min_value_error_message: str
	max_value_error_message: str
	codecs: Mapping[type, Codec]

	@classmethod
	def create(
		cls,
		*,
		type_error_message: str = "expected type '{expected_type}', got '{found_type}'",
		min_length_error_message: str = "length must be at least {min_length}",
		max_length_error_message: str = "length must be at most {max_length}",
		min_value_error_message: str = "must be at least {min_value}",
		max_value_error_message: str = "must be at most {max_value}",
		codecs: Mapping[type, Codec] | None = None,
	) -> StaticaConfig:
		merged_codecs: dict[type, Codec] = dict(DEFAULT_CODECS)
		if codecs:
			merged_codecs.update(codecs)

		return cls(
			type_error_message=type_error_message,
			min_length_error_message=min_length_error_message,
			max_length_error_message=max_length_error_message,
			min_value_error_message=min_value_error_message,
			max_value_error_message=max_value_error_message,
			codecs=merged_codecs,
		)


default_config = StaticaConfig.create()
