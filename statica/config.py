from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class StaticaConfig:
	"""
	Templates for validation error messages. Set them per model with
	`class Model(Statica, config=StaticaConfig(...))`.
	"""

	type_error_message: str = "expected type '{expected_type}', got '{found_type}'"
	literal_error_message: str = "expected one of {allowed_values}, got '{value}'"
	min_length_error_message: str = "{field_name} length must be at least {min_length}"
	max_length_error_message: str = "{field_name} length must be at most {max_length}"
	min_value_error_message: str = "{field_name} must be at least {min_value}"
	max_value_error_message: str = "{field_name} must be at most {max_value}"


default_config = StaticaConfig()
