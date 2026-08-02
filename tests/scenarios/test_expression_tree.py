"""
Scenario: a recursive arithmetic expression tree parsed from JSON.

Exercises, end to end:
- Mutually/self-referential models via forward references (Number, BinaryOp)
- Union-based node discrimination (Number | BinaryOp) at arbitrary depth
- Recursive coercion through from_map and recursive to_dict round-trips
- A polymorphic evaluate() computing the whole tree, with a runtime ZeroDivisionError
- The documented union-summary behavior for malformed nodes inside a union field
"""

import unittest
from typing import Any, Literal

from statica import Statica, TypeValidationError


class Number(Statica):
	value: int | float

	def evaluate(self) -> float:
		return self.value


class BinaryOp(Statica):
	op: Literal["+", "-", "*", "/"]
	left: "Number | BinaryOp"
	right: "Number | BinaryOp"

	def evaluate(self) -> float:
		left = self.left.evaluate()
		right = self.right.evaluate()
		if self.op == "+":
			return left + right
		if self.op == "-":
			return left - right
		if self.op == "*":
			return left * right
		if right == 0:
			msg = "division by zero in expression"
			raise ZeroDivisionError(msg)
		return left / right


def _expr() -> dict[str, Any]:
	# ((1 + 2) * (10 - 4)) / 3  ==  (3 * 6) / 3  ==  6.0
	return {
		"op": "/",
		"left": {
			"op": "*",
			"left": {"op": "+", "left": {"value": 1}, "right": {"value": 2}},
			"right": {"op": "-", "left": {"value": 10}, "right": {"value": 4}},
		},
		"right": {"value": 3},
	}


class TestExpressionTreeScenario(unittest.TestCase):
	def test_parse_and_discriminate_nodes(self) -> None:
		tree = BinaryOp.from_map(_expr())
		self.assertIsInstance(tree, BinaryOp)
		self.assertEqual(tree.op, "/")
		# The right child is a leaf Number, the left child a nested BinaryOp.
		self.assertIsInstance(tree.right, Number)
		left = tree.left
		assert isinstance(left, BinaryOp)  # narrow the union for the type checker
		self.assertIsInstance(left.left, BinaryOp)

	def test_evaluate_full_tree(self) -> None:
		self.assertEqual(BinaryOp.from_map(_expr()).evaluate(), 6.0)

	def test_leaf_number(self) -> None:
		self.assertEqual(Number.from_map({"value": 42}).evaluate(), 42)

	def test_recursive_round_trip(self) -> None:
		tree = BinaryOp.from_map(_expr())
		self.assertEqual(BinaryOp.from_map(tree.to_dict()), tree)
		# Spot-check the serialized nested shape.
		serialized = tree.to_dict()
		self.assertEqual(serialized["right"], {"value": 3})
		self.assertEqual(serialized["left"]["op"], "*")

	def test_division_by_zero_at_eval_time(self) -> None:
		tree = BinaryOp.from_map({"op": "/", "left": {"value": 1}, "right": {"value": 0}})
		with self.assertRaisesRegex(ZeroDivisionError, "division by zero"):
			tree.evaluate()

	def test_deeper_tree_evaluates(self) -> None:
		# (2 * 3) + ((8 / 2) - 1) == 6 + 3 == 9.0
		expr = {
			"op": "+",
			"left": {"op": "*", "left": {"value": 2}, "right": {"value": 3}},
			"right": {
				"op": "-",
				"left": {"op": "/", "left": {"value": 8}, "right": {"value": 2}},
				"right": {"value": 1},
			},
		}
		self.assertEqual(BinaryOp.from_map(expr).evaluate(), 9.0)

	def test_malformed_node_reports_union_summary(self) -> None:
		# A node that is neither a valid Number nor BinaryOp collapses to the union
		# summary at the nearest union field (documented limitation), rather than a
		# path into the offending inner field.
		bad = {"op": "/", "left": {"value": 1}, "right": {"value": "oops"}}
		with self.assertRaises(TypeValidationError) as cm:
			BinaryOp.from_map(bad)
		message = str(cm.exception)
		self.assertIn("BinaryOp.right:", message)
		self.assertIn("Number | BinaryOp", message)

	def test_invalid_top_level_op(self) -> None:
		bad = {"op": "%", "left": {"value": 1}, "right": {"value": 2}}
		with self.assertRaises(TypeValidationError) as cm:
			BinaryOp.from_map(bad)
		# The top-level op is not behind a union, so it reports a precise path.
		self.assertIn("BinaryOp.op:", str(cm.exception))
		self.assertIn("expected one of", str(cm.exception))


if __name__ == "__main__":
	unittest.main()
