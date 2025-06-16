from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StaticaConfig:
	type_error_message: str
	min_length_error_message: str
	max_length_error_message: str
	min_value_error_message: str
	max_value_error_message: str

	@classmethod
	def create(
		cls,
		*,
		type_error_message: str = "expected type '{expected_type}', got '{found_type}'",
		min_length_error_message: str = "{field_name} length must be at least {min_length}",
		max_length_error_message: str = "{field_name} length must be at most {max_length}",
		min_value_error_message: str = "{field_name} must be at least {min_value}",
		max_value_error_message: str = "{field_name} must be at most {max_value}",
	) -> StaticaConfig:
		return cls(
			type_error_message=type_error_message,
			min_length_error_message=min_length_error_message,
			max_length_error_message=max_length_error_message,
			min_value_error_message=min_value_error_message,
			max_value_error_message=max_value_error_message,
		)


default_config = StaticaConfig.create()
