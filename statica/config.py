from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StaticaConfig:
	type_error_message: str
	min_length_error_message: str
	max_length_error_message: str
	min_value_error_message: str
	max_value_error_message: str


default_config = StaticaConfig(
	type_error_message="expected type '{expected_type}', got '{found_type}'",
	min_length_error_message="{field_name} length must be at least {min_length}",
	max_length_error_message="{field_name} length must be at most {max_length}",
	min_value_error_message="{field_name} must be at least {min_value}",
	max_value_error_message="{field_name} must be at most {max_value}",
)
