class ValidationError(Exception):
	"""Base validation error."""


class TypeValidationError(ValidationError):
	"""Raised when type validation fails."""


class ConstraintValidationError(ValidationError):
	"""Raised when constraint validation fails."""
