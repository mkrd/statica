import tracemalloc
from typing import Any

# benchmark_memory.py
from statica import Field, Statica

test_data = {"name": "John Doe", "age": 30, "email": "john.doe@example.com", "salary": 75000.0}


class StaticaModel(Statica):
	name: str
	age: int = Field(min_value=0, max_value=120)
	email: str
	salary: float | None = None


def measure_memory_usage_mb(cls: Any, num_objects: int = 100_000) -> float:
	tracemalloc.start()

	objects = []
	for _ in range(num_objects):
		objects.append(cls(**test_data))  # noqa: PERF401

	_, peak = tracemalloc.get_traced_memory()
	tracemalloc.stop()

	return peak / 1024 / 1024


if __name__ == "__main__":
	memory_usage = measure_memory_usage_mb(StaticaModel)
	print(f"Memory usage for {StaticaModel.__name__}: {memory_usage:.2f} MB")
