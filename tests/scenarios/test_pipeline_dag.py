"""
Scenario: a build/CI pipeline defined as a job dependency graph.

Exercises, end to end:
- dict[str, Job] with frozenset dependency sets (parsed from JSON lists via cast_to)
- Numeric + length constraints with precise dict-keyed error paths
- Cross-entity validation in __post_init__: dependencies must exist, no self-dependency,
  and the graph must be acyclic (topological sort)
- A domain method (topological_order) computing a deterministic execution order
- Object round-trips through frozenset fields
"""

import unittest
from typing import Any

from statica import ConstraintValidationError, Field, Statica


class PipelineError(ValueError):
	"""Raised for structural problems in the pipeline graph."""


class Job(Statica):
	command: str = Field(min_length=1)
	needs: frozenset[str] = Field(default=frozenset(), cast_to=frozenset)
	retries: int = Field(default=0, min_value=0, max_value=5)


class Pipeline(Statica):
	name: str = Field(min_length=1)
	jobs: dict[str, Job]

	def __post_init__(self) -> None:
		for job_name, job in self.jobs.items():
			for dependency in job.needs:
				if dependency == job_name:
					msg = f"job {job_name!r} depends on itself"
					raise PipelineError(msg)
				if dependency not in self.jobs:
					msg = f"job {job_name!r} needs unknown job {dependency!r}"
					raise PipelineError(msg)
		# Building the order also detects cycles.
		self.topological_order()

	def topological_order(self) -> list[str]:
		"""Deterministic execution order (Kahn's algorithm, ties broken by name)."""
		indegree = {name: len(job.needs) for name, job in self.jobs.items()}
		dependents: dict[str, list[str]] = {name: [] for name in self.jobs}
		for name, job in self.jobs.items():
			for dependency in job.needs:
				dependents[dependency].append(name)

		ready = sorted(name for name, count in indegree.items() if count == 0)
		order: list[str] = []
		while ready:
			name = ready.pop(0)
			order.append(name)
			for dependent in sorted(dependents[name]):
				indegree[dependent] -= 1
				if indegree[dependent] == 0:
					ready.append(dependent)
					ready.sort()

		if len(order) != len(self.jobs):
			msg = "pipeline contains a dependency cycle"
			raise PipelineError(msg)
		return order


def _valid_pipeline() -> dict[str, Any]:
	return {
		"name": "release",
		"jobs": {
			"lint": {"command": "ruff check ."},
			"test": {"command": "pytest", "needs": ["lint"], "retries": 2},
			"build": {"command": "make build", "needs": ["test"]},
			"publish": {"command": "make publish", "needs": ["build", "test"]},
		},
	}


class TestPipelineDagScenario(unittest.TestCase):
	def test_parse_and_topological_order(self) -> None:
		pipeline = Pipeline.from_map(_valid_pipeline())
		self.assertEqual(pipeline.name, "release")
		self.assertEqual(pipeline.jobs["test"].needs, frozenset({"lint"}))
		self.assertEqual(pipeline.jobs["test"].retries, 2)

		order = pipeline.topological_order()
		self.assertEqual(order, ["lint", "test", "build", "publish"])
		# Every dependency precedes its dependents.
		for name, job in pipeline.jobs.items():
			for dependency in job.needs:
				self.assertLess(order.index(dependency), order.index(name))

	def test_default_retries_and_needs(self) -> None:
		lint = Pipeline.from_map(_valid_pipeline()).jobs["lint"]
		self.assertEqual(lint.needs, frozenset())
		self.assertEqual(lint.retries, 0)

	def test_round_trip(self) -> None:
		pipeline = Pipeline.from_map(_valid_pipeline())
		# frozenset serializes to a list; re-parsing casts back and compares by value.
		self.assertEqual(Pipeline.from_map(pipeline.to_dict()), pipeline)

	def test_retries_constraint_error_path(self) -> None:
		data = _valid_pipeline()
		data["jobs"]["test"]["retries"] = 99
		with self.assertRaises(ConstraintValidationError) as cm:
			Pipeline.from_map(data)
		self.assertEqual(
			str(cm.exception),
			"Pipeline.jobs['test'].retries: must be at most 5",
		)

	def test_unknown_dependency_rejected(self) -> None:
		data = _valid_pipeline()
		data["jobs"]["build"]["needs"] = ["test", "ghost"]
		with self.assertRaisesRegex(PipelineError, "unknown job 'ghost'"):
			Pipeline.from_map(data)

	def test_self_dependency_rejected(self) -> None:
		data = _valid_pipeline()
		data["jobs"]["lint"]["needs"] = ["lint"]
		with self.assertRaisesRegex(PipelineError, "depends on itself"):
			Pipeline.from_map(data)

	def test_cycle_rejected(self) -> None:
		data = _valid_pipeline()
		# Introduce a cycle: lint <-> test
		data["jobs"]["lint"]["needs"] = ["publish"]
		with self.assertRaisesRegex(PipelineError, "cycle"):
			Pipeline.from_map(data)

	def test_diamond_dependencies_order(self) -> None:
		data = {
			"name": "diamond",
			"jobs": {
				"a": {"command": "a"},
				"b": {"command": "b", "needs": ["a"]},
				"c": {"command": "c", "needs": ["a"]},
				"d": {"command": "d", "needs": ["b", "c"]},
			},
		}
		order = Pipeline.from_map(data).topological_order()
		self.assertEqual(order[0], "a")
		self.assertEqual(order[-1], "d")
		self.assertLess(order.index("b"), order.index("d"))
		self.assertLess(order.index("c"), order.index("d"))


if __name__ == "__main__":
	unittest.main()
