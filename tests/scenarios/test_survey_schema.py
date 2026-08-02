"""
Scenario: a survey / form schema definition.

Exercises, end to end:
- Field validators that normalize input (key slugified) and reject bad values
- strip_whitespace + min/max_length string constraints
- Literal question kinds with conditional cross-field rules in __post_init__
- Mutable default safety: each question gets an independent options list
- A per-field serializer hook (tags emitted as a sorted list for stable output)
- Aliases, with_aliases=False, and round-trips
"""

import unittest
from typing import Any, Literal

from statica import ConstraintValidationError, Field, Statica, TypeValidationError


class SurveyError(ValueError):
	"""Raised for invalid survey/question definitions."""


def _normalize_key(value: str) -> str:
	key = value.strip().lower()
	if not key:
		msg = "question key must not be empty"
		raise ValueError(msg)
	if not all(char.isalnum() or char == "_" for char in key):
		msg = f"question key {value!r} may only contain alphanumerics and underscores"
		raise ValueError(msg)
	return key


class Question(Statica):
	key: str = Field(validator=_normalize_key)
	label: str = Field(min_length=1, max_length=200, strip_whitespace=True)
	kind: Literal["text", "number", "single_choice", "boolean"]
	required: bool = Field(default=False)
	options: list[str] = Field(default=[])
	minimum: int | None = Field(default=None)
	maximum: int | None = Field(default=None)
	default_value: str | int | bool | None = Field(default=None, alias="default")

	def __post_init__(self) -> None:
		if self.kind == "single_choice":
			if len(self.options) < 2:  # noqa: PLR2004
				msg = f"question {self.key!r}: single_choice needs at least two options"
				raise SurveyError(msg)
			if self.default_value is not None and self.default_value not in self.options:
				msg = f"question {self.key!r}: default is not one of the options"
				raise SurveyError(msg)
		elif self.kind == "number" and (
			self.minimum is not None and self.maximum is not None and self.minimum > self.maximum
		):
			msg = f"question {self.key!r}: minimum exceeds maximum"
			raise SurveyError(msg)


class Form(Statica):
	form_id: str = Field(alias="formId")
	title: str = Field(min_length=1, strip_whitespace=True)
	questions: list[Question]
	tags: frozenset[str] = Field(
		default=frozenset(),
		cast_to=frozenset,
		serializer=sorted,  # stable, ordered output
	)

	def __post_init__(self) -> None:
		keys = [q.key for q in self.questions]
		if len(keys) != len(set(keys)):
			msg = "question keys must be unique"
			raise SurveyError(msg)


def _valid_form() -> dict[str, Any]:
	return {
		"formId": "signup-survey",
		"title": "  Signup Survey  ",
		"tags": ["onboarding", "beta"],
		"questions": [
			{"key": "Full_Name", "label": "  Your name  ", "kind": "text", "required": True},
			{"key": "AGE", "label": "Age", "kind": "number", "minimum": 0, "maximum": 120},
			{
				"key": "plan",
				"label": "Preferred plan",
				"kind": "single_choice",
				"options": ["free", "pro", "team"],
				"default": "free",
			},
		],
	}


class TestSurveySchemaScenario(unittest.TestCase):
	def test_parse_and_normalize(self) -> None:
		form = Form.from_map(_valid_form())
		self.assertEqual(form.form_id, "signup-survey")
		self.assertEqual(form.title, "Signup Survey")  # stripped
		# Keys are normalized (lower-cased) by the field validator.
		self.assertEqual([q.key for q in form.questions], ["full_name", "age", "plan"])
		self.assertEqual(form.questions[0].label, "Your name")  # stripped
		self.assertTrue(form.questions[0].required)
		self.assertEqual(form.questions[2].options, ["free", "pro", "team"])
		self.assertEqual(form.questions[2].default_value, "free")

	def test_bad_key_rejected_with_path(self) -> None:
		data = _valid_form()
		data["questions"][0]["key"] = "not a key!"
		with self.assertRaises(ConstraintValidationError) as cm:
			Form.from_map(data)
		self.assertIn("Form.questions[0].key:", str(cm.exception))
		self.assertIn("alphanumerics and underscores", str(cm.exception))

	def test_label_too_long_error_path(self) -> None:
		data = _valid_form()
		data["questions"][1]["label"] = "x" * 201
		with self.assertRaises(ConstraintValidationError) as cm:
			Form.from_map(data)
		self.assertEqual(
			str(cm.exception),
			"Form.questions[1].label: length must be at most 200",
		)

	def test_invalid_kind_literal_error_path(self) -> None:
		data = _valid_form()
		data["questions"][0]["kind"] = "essay"
		with self.assertRaises(TypeValidationError) as cm:
			Form.from_map(data)
		self.assertIn("Form.questions[0].kind:", str(cm.exception))
		self.assertIn("expected one of", str(cm.exception))

	def test_single_choice_needs_options(self) -> None:
		data = _valid_form()
		data["questions"][2]["options"] = ["only-one"]
		with self.assertRaisesRegex(SurveyError, "at least two options"):
			Form.from_map(data)

	def test_default_not_in_options(self) -> None:
		data = _valid_form()
		data["questions"][2]["default"] = "enterprise"
		with self.assertRaisesRegex(SurveyError, "not one of the options"):
			Form.from_map(data)

	def test_number_minimum_exceeds_maximum(self) -> None:
		data = _valid_form()
		data["questions"][1]["minimum"] = 200
		with self.assertRaisesRegex(SurveyError, "minimum exceeds maximum"):
			Form.from_map(data)

	def test_duplicate_keys_rejected(self) -> None:
		data = _valid_form()
		# After normalization "AGE" and "age" collide.
		data["questions"][1]["key"] = "Full_Name"
		with self.assertRaisesRegex(SurveyError, "keys must be unique"):
			Form.from_map(data)

	def test_mutable_default_options_are_independent(self) -> None:
		q1 = Question(key="a", label="A", kind="text")
		q2 = Question(key="b", label="B", kind="text")
		q1.options.append("x")
		self.assertEqual(q1.options, ["x"])
		self.assertEqual(q2.options, [])  # not shared

	def test_serializer_and_round_trip(self) -> None:
		form = Form.from_map(_valid_form())
		serialized = form.to_dict()
		# Tags serialized as a sorted list via the per-field serializer.
		self.assertEqual(serialized["tags"], ["beta", "onboarding"])
		self.assertEqual(serialized["questions"][0]["default"], None)
		# Object round-trip (frozenset compares by value).
		self.assertEqual(Form.from_map(serialized), form)

	def test_without_aliases(self) -> None:
		form = Form.from_map(_valid_form())
		plain = form.to_dict(with_aliases=False)
		self.assertIn("form_id", plain)
		self.assertEqual(plain["questions"][2]["default_value"], "free")


if __name__ == "__main__":
	unittest.main()
