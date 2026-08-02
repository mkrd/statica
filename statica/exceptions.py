from __future__ import annotations


def format_loc(root: str | None, loc: list[str]) -> str:
	"""
	Render a structured location path into a human-readable prefix.

	Field and mapping-key segments are joined with a dot, while index-style
	segments (``[0]``, ``['key']``, ``{'elem'}``) attach directly to the
	preceding segment.

	Example: ``format_loc("User", ["address", "street"])`` -> ``"User.address.street"``.
	Example: ``format_loc("Model", ["items", "[2]"])`` -> ``"Model.items[2]"``.
	"""

	result = root or ""
	for segment in loc:
		if segment.startswith(("[", "{")):
			result += segment
		elif result:
			result += "." + segment
		else:
			result = segment
	return result


class ValidationError(Exception):
	"""
	Base validation error.

	Carries a structured location (`loc`) and the originating model class name
	(`root`) so that nested errors can render a full path such as
	``User.address.street: expected type 'str', got 'int'``.
	"""

	def __init__(
		self,
		message: str = "",
		*,
		loc: list[str] | None = None,
		root: str | None = None,
	) -> None:
		super().__init__(message)
		self.message = message
		self.loc: list[str] = list(loc) if loc else []
		self.root: str | None = root

	def __str__(self) -> str:  # pyrefly: ignore[missing-override-decorator]
		path = format_loc(self.root, self.loc)
		if path:
			return f"{path}: {self.message}"
		return self.message


class TypeValidationError(ValidationError):
	"""Raised when type validation fails."""


class ConstraintValidationError(ValidationError):
	"""Raised when constraint validation fails."""


class FrozenInstanceError(AttributeError):
	"""Raised when attempting to mutate a field on a frozen Statica instance."""
