"""
Scenario: parsing and validating a service deployment manifest.

Exercises, end to end:
- A shared base that configures `config` once, inherited by every model (proven by the
  custom Duration codec being available in models that never restate the config)
- A custom codec (Duration like "30s") registered through StaticaConfig
- Literal fields, tuple-via-cast (semantic version), abc Mapping fields, ordered tuple tags,
  and optional nested models
- dict[str, Model] parsing (named services) with per-value error paths
- Field validators (port range), constraints, and cross-field invariants via __post_init__
- Serialization round-trips through the custom codec and precise error reporting
"""

import unittest
from collections.abc import Mapping
from enum import Enum
from typing import Any, ClassVar, Literal

from statica import (
	Codec,
	ConstraintValidationError,
	Field,
	FrozenInstanceError,
	Statica,
	StaticaConfig,
	TypeValidationError,
)

MIN_DURATION_LEN = 2
MAX_PORT = 65535


class Duration:
	"""A small duration value parsed from strings like '30s', '5m', '2h'."""

	__slots__ = ("seconds",)
	_UNITS: ClassVar[dict[str, int]] = {"s": 1, "m": 60, "h": 3600}

	def __init__(self, seconds: int) -> None:
		self.seconds = seconds

	@classmethod
	def parse(cls, text: object) -> "Duration":
		if isinstance(text, Duration):
			return text
		if not isinstance(text, str) or len(text) < MIN_DURATION_LEN or text[-1] not in cls._UNITS:
			msg = f"invalid duration: {text!r}"
			raise ValueError(msg)
		return cls(int(text[:-1]) * cls._UNITS[text[-1]])

	def __eq__(self, other: object) -> bool:
		return isinstance(other, Duration) and other.seconds == self.seconds

	def __hash__(self) -> int:
		return hash(self.seconds)

	def __repr__(self) -> str:
		return f"Duration({self.seconds}s)"


class LogLevel(Enum):
	DEBUG = "debug"
	INFO = "info"
	WARNING = "warning"


DEPLOY_CONFIG = StaticaConfig.create(
	codecs={Duration: Codec(decode=Duration.parse, encode=lambda d: f"{d.seconds}s")},
)


class ConfigModel(Statica, config=DEPLOY_CONFIG, frozen=True):
	"""Shared base: immutable manifest models sharing the Duration codec via config."""


def _valid_port(port: int) -> int:
	if not (1 <= port <= MAX_PORT):
		msg = f"port {port} out of range 1-65535"
		raise ValueError(msg)
	return port


class ResourceLimits(ConfigModel, frozen=True):
	cpu_millis: int = Field(alias="cpuMillis", min_value=1)
	memory_mb: int = Field(alias="memoryMb", min_value=16)


class HealthCheck(ConfigModel, frozen=True):
	interval: Duration
	timeout: Duration
	path: str = Field(default="/health")


class ServiceSpec(ConfigModel, frozen=True):
	image: str = Field(min_length=1)
	replicas: int = Field(min_value=1, max_value=100)
	min_replicas: int = Field(alias="minReplicas", min_value=1)
	max_replicas: int = Field(alias="maxReplicas", min_value=1)
	port: int = Field(validator=_valid_port)
	version: tuple[int, int, int] = Field(cast_to=tuple)
	graceful_shutdown: Duration = Field(alias="gracefulShutdown")
	resources: ResourceLimits
	protocol: Literal["http", "grpc", "tcp"] = Field(default="http")
	env: Mapping[str, str] = Field(default={})
	health: HealthCheck | None = Field(default=None)
	tags: tuple[str, ...] = Field(default=(), cast_to=tuple)

	def __post_init__(self) -> None:
		if self.min_replicas > self.max_replicas:
			msg = "min_replicas cannot exceed max_replicas"
			raise ValueError(msg)
		if not (self.min_replicas <= self.replicas <= self.max_replicas):
			msg = "replicas must be within [min_replicas, max_replicas]"
			raise ValueError(msg)


class DeploymentManifest(ConfigModel, frozen=True):
	name: str = Field(min_length=1)
	environment: Literal["dev", "staging", "prod"]
	services: dict[str, ServiceSpec]
	default_log_level: LogLevel = Field(default=LogLevel.INFO, alias="defaultLogLevel")
	revision: int = Field(default=1, min_value=1)


def _valid_manifest() -> dict[str, Any]:
	return {
		"name": "payments-platform",
		"environment": "prod",
		"revision": 7,
		"services": {
			"api": {
				"image": "registry/api:1.4.2",
				"replicas": 3,
				"minReplicas": 2,
				"maxReplicas": 10,
				"port": 8080,
				"version": [1, 4, 2],
				"gracefulShutdown": "45s",
				"protocol": "http",
				"env": {"LOG_FORMAT": "json", "REGION": "eu-west"},
				"resources": {"cpuMillis": 500, "memoryMb": 512},
				"health": {"interval": "30s", "timeout": "5s", "path": "/healthz"},
				"tags": ["public", "tier-1"],
			},
			"worker": {
				"image": "registry/worker:1.4.2",
				"replicas": 5,
				"minReplicas": 1,
				"maxReplicas": 20,
				"port": 9000,
				"version": [1, 4, 2],
				"gracefulShutdown": "10s",
				"protocol": "grpc",
				"resources": {"cpuMillis": 250, "memoryMb": 256},
			},
		},
	}


class TestDeploymentManifestScenario(unittest.TestCase):
	def test_parse_valid_manifest(self) -> None:
		manifest = DeploymentManifest.from_map(_valid_manifest())

		self.assertEqual(manifest.name, "payments-platform")
		self.assertEqual(manifest.environment, "prod")
		self.assertEqual(manifest.revision, 7)
		self.assertIs(manifest.default_log_level, LogLevel.INFO)  # default applied
		self.assertEqual(set(manifest.services), {"api", "worker"})

		api = manifest.services["api"]
		self.assertEqual(api.image, "registry/api:1.4.2")
		self.assertEqual(api.replicas, 3)
		self.assertEqual(api.port, 8080)
		self.assertEqual(api.protocol, "http")
		self.assertEqual(api.version, (1, 4, 2))
		self.assertIsInstance(api.version, tuple)
		self.assertEqual(api.graceful_shutdown, Duration(45))
		self.assertEqual(dict(api.env), {"LOG_FORMAT": "json", "REGION": "eu-west"})
		self.assertEqual(api.resources, ResourceLimits(cpu_millis=500, memory_mb=512))
		self.assertEqual(api.tags, ("public", "tier-1"))
		assert api.health is not None
		self.assertEqual(api.health.interval, Duration(30))
		self.assertEqual(api.health.timeout, Duration(5))
		self.assertEqual(api.health.path, "/healthz")

	def test_defaults_applied(self) -> None:
		worker = DeploymentManifest.from_map(_valid_manifest()).services["worker"]
		self.assertIsNone(worker.health)
		self.assertEqual(dict(worker.env), {})
		self.assertEqual(worker.tags, ())
		self.assertEqual(worker.protocol, "grpc")

	def test_config_inheritance_provides_codec(self) -> None:
		# A model that does NOT inherit DEPLOY_CONFIG lacks the Duration codec.
		class Bare(Statica):
			d: Duration

		with self.assertRaises(TypeValidationError):
			Bare.from_map({"d": "30s"})

		# HealthCheck inherits the config from ConfigModel and decodes the same value.
		health = HealthCheck.from_map({"interval": "30s", "timeout": "5s"})
		self.assertEqual(health.interval, Duration(30))

	def test_frozen_inherited_immutable_and_hashable(self) -> None:
		limits = ResourceLimits(cpu_millis=100, memory_mb=64)
		with self.assertRaises(FrozenInstanceError):
			limits.cpu_millis = 1  # type: ignore[read-only]
		# Frozen + all-hashable fields => hashable and de-duplicated by value.
		same = {
			ResourceLimits(cpu_millis=1, memory_mb=16),
			ResourceLimits(cpu_millis=1, memory_mb=16),
		}
		self.assertEqual(len(same), 1)

	def test_custom_codec_round_trip(self) -> None:
		manifest = DeploymentManifest.from_map(_valid_manifest())
		serialized = manifest.to_dict()

		api = serialized["services"]["api"]
		self.assertEqual(api["gracefulShutdown"], "45s")
		self.assertEqual(api["health"]["interval"], "30s")
		self.assertEqual(api["version"], [1, 4, 2])
		self.assertEqual(api["resources"], {"cpuMillis": 500, "memoryMb": 512})
		self.assertEqual(serialized["defaultLogLevel"], "info")

		# Full object round-trip.
		self.assertEqual(DeploymentManifest.from_map(serialized), manifest)

	def test_replicas_out_of_range_error_path(self) -> None:
		manifest = _valid_manifest()
		manifest["services"]["api"]["replicas"] = 200
		with self.assertRaises(ConstraintValidationError) as cm:
			DeploymentManifest.from_map(manifest)
		self.assertEqual(
			str(cm.exception),
			"DeploymentManifest.services['api'].replicas: must be at most 100",
		)

	def test_invalid_protocol_literal_error_path(self) -> None:
		manifest = _valid_manifest()
		manifest["services"]["worker"]["protocol"] = "ftp"
		with self.assertRaises(TypeValidationError) as cm:
			DeploymentManifest.from_map(manifest)
		message = str(cm.exception)
		self.assertIn("DeploymentManifest.services['worker'].protocol:", message)
		self.assertIn("expected one of", message)

	def test_invalid_port_validator_error_path(self) -> None:
		manifest = _valid_manifest()
		manifest["services"]["api"]["port"] = 70000
		with self.assertRaises(ConstraintValidationError) as cm:
			DeploymentManifest.from_map(manifest)
		self.assertEqual(
			str(cm.exception),
			"DeploymentManifest.services['api'].port: port 70000 out of range 1-65535",
		)

	def test_autoscale_invariant_violation(self) -> None:
		# __post_init__ raises a plain ValueError; it is not wrapped, and this holds
		# whether the model is top-level or nested inside another model.
		manifest = _valid_manifest()
		manifest["services"]["api"]["minReplicas"] = 50  # exceeds maxReplicas
		with self.assertRaisesRegex(ValueError, "min_replicas cannot exceed"):
			DeploymentManifest.from_map(manifest)

	def test_bad_duration_error_path(self) -> None:
		manifest = _valid_manifest()
		manifest["services"]["api"]["gracefulShutdown"] = "quickly"
		with self.assertRaises(TypeValidationError) as cm:
			DeploymentManifest.from_map(manifest)
		self.assertEqual(
			str(cm.exception),
			"DeploymentManifest.services['api'].graceful_shutdown: "
			"expected type 'Duration', got 'str'",
		)

	def test_bad_field_in_optional_model_reports_union_summary(self) -> None:
		# Known limitation: a bad field inside the OPTIONAL `health` model surfaces
		# the union summary, not the precise inner path (the union suppresses the
		# inner branch failure). Required nested models keep the precise path.
		manifest = _valid_manifest()
		manifest["services"]["api"]["health"]["interval"] = "quickly"
		with self.assertRaises(TypeValidationError) as cm:
			DeploymentManifest.from_map(manifest)
		message = str(cm.exception)
		self.assertIn("DeploymentManifest.services['api'].health:", message)
		self.assertIn("HealthCheck | NoneType", message)


if __name__ == "__main__":
	unittest.main()
