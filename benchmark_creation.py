import time
from typing import Any

import statica

test_data = {"name": "John Doe", "age": 30, "email": "john.doe@example.com", "salary": 75000.0}


class StaticaModel(statica.Statica):
	name: str
	age: int
	email: str
	salary: float | None = None


def benchmark_creation(cls: Any, iterations: int = 1_000_000) -> int:
	t0 = time.perf_counter()

	for _ in range(iterations):
		_ = cls(**test_data)

	return int((time.perf_counter() - t0) * 1000)


if __name__ == "__main__":
	creation_time = benchmark_creation(StaticaModel)

	print(f"Time to create 1,000,000 instances of {StaticaModel.__name__}: {creation_time} ms")

	# Profile this script with Tachyon, the statistical profiler shipped with
	# Python 3.15 (`profiling.sampling`):
	#
	#   just profile
	#
	# Tachyon samples the whole process from the outside, so it needs no in-process
	# instrumentation and adds virtually zero overhead.

	# 2025-06-09 - main - 1204ms
	# 2025-06-09 - nested-init - 1201ms
