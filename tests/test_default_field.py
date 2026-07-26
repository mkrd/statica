"""Tests for default field functionality in Statica."""

import unittest

from statica import Field, Statica
from statica.exceptions import ConstraintValidationError, TypeValidationError


class TestDefaultField(unittest.TestCase):
	def test_basic_default_value(self) -> None:
		"""Test that default values are used when field is not provided."""

		age_default = 25

		class User(Statica):
			name: str
			age: int = Field(default=age_default)
			active: bool = Field(default=True)

		user = User(name="John")
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_default)
		self.assertTrue(user.active)

	def test_explicit_value_overrides_default(self) -> None:
		"""Test that explicitly provided values override defaults."""

		age_default = 25
		age_init = 30

		class User(Statica):
			name: str
			age: int = Field(default=age_default)
			active: bool = Field(default=True)

		user = User(name="John", age=age_init, active=False)
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_init)
		self.assertFalse(user.active)

	def test_none_as_default_value(self) -> None:
		"""Test that None can be used as a default value."""

		class User(Statica):
			name: str
			description: str | None = Field(default=None)

		user = User(name="John")
		self.assertEqual(user.name, "John")
		self.assertIsNone(user.description)

	def test_complex_default_values(self) -> None:
		"""Test default values with complex types."""

		retires_value = 3
		timeout_value = 30.0

		class Config(Statica):
			timeout: float = Field(default=timeout_value)
			retries: int = Field(default=retires_value)
			tags: list[str] | None = Field(default=None)

		config = Config()
		self.assertEqual(config.timeout, timeout_value)
		self.assertEqual(config.retries, retires_value)
		self.assertIsNone(config.tags)

	def test_default_value_validation(self) -> None:
		"""Test that default values are validated against constraints."""

		age_default = 25

		class User(Statica):
			name: str
			age: int = Field(default=age_default, min_value=18, max_value=100)

		# Should work with valid default
		user = User(name="John")
		self.assertEqual(user.age, age_default)

	def test_invalid_default_value_raises_error(self) -> None:
		"""Test that invalid default values raise validation errors."""

		class User(Statica):
			name: str
			age: int = Field(default=150, min_value=18, max_value=100)

		with self.assertRaises(ConstraintValidationError):
			User(name="John")  # This should trigger validation of default

	def test_default_with_casting(self) -> None:
		"""Test default values work with cast_to functionality."""

		age_default = 25

		class User(Statica):
			name: str
			age: int = Field(default=age_default, cast_to=int)

		user = User(name="John")
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_default)

		self.assertIsInstance(user.age, int)

	def test_from_map_with_defaults(self) -> None:
		"""Test that from_map uses defaults for missing keys."""

		age_default = 25
		active_default = True

		class User(Statica):
			name: str
			age: int = Field(default=age_default)
			active: bool = Field(default=active_default)

		user = User.from_map({"name": "John"})
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_default)
		self.assertIs(user.active, active_default)

	def test_from_map_overrides_defaults(self) -> None:
		"""Test that from_map explicit values override defaults."""

		age_default = 25
		age_init = 30
		active_default = True
		active_init = False

		class User(Statica):
			name: str
			age: int = Field(default=age_default)
			active: bool = Field(default=active_default)

		user = User.from_map({"name": "John", "age": age_init, "active": active_init})
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_init)
		self.assertIs(user.active, active_init)

	def test_nested_statica_with_defaults(self) -> None:
		"""Test default values in nested Statica objects."""

		class Address(Statica):
			street: str
			city: str = Field(default="Unknown")

		class User(Statica):
			name: str
			address: Address | None = Field(default=None)

		user = User(name="John")
		self.assertEqual(user.name, "John")
		self.assertIsNone(user.address)

	def test_nested_statica_from_map_with_defaults(self) -> None:
		"""Test nested Statica objects with defaults when using from_map."""

		class Address(Statica):
			street: str
			city: str = Field(default="Unknown")

		class User(Statica):
			name: str
			address: Address

		user = User.from_map({"name": "John", "address": {"street": "123 Main St"}})
		self.assertEqual(user.name, "John")
		self.assertEqual(user.address.street, "123 Main St")
		self.assertEqual(user.address.city, "Unknown")

	def test_default_with_aliases(self) -> None:
		"""Test that defaults work properly with field aliases."""

		age_default = 25
		age_init = 30

		class User(Statica):
			name: str
			age: int = Field(default=age_default, alias="userAge")

		# Using from_map with alias
		user1 = User.from_map({"name": "John"})
		self.assertEqual(user1.age, age_default)

		# Using from_map with explicit alias value
		user2 = User.from_map({"name": "Jane", "userAge": age_init})
		self.assertEqual(user2.age, age_init)

	def test_to_dict_with_defaults(self) -> None:
		"""Test that to_dict includes default values."""

		age_default = 25

		class User(Statica):
			name: str
			age: int = Field(default=age_default)
			active: bool = Field(default=True, alias="isActive")

		user = User(name="John")

		# Without aliases
		result = user.to_dict(with_aliases=False)
		expected = {"name": "John", "age": age_default, "active": True}
		self.assertEqual(result, expected)

		# With aliases
		result_with_aliases = user.to_dict(with_aliases=True)
		expected_with_aliases = {"name": "John", "age": age_default, "isActive": True}
		self.assertEqual(result_with_aliases, expected_with_aliases)

	def test_mutable_default_values_are_safe(self) -> None:
		"""Test that mutable default values don't cause shared state issues."""

		class Config(Statica):
			name: str
			tags: list[str] = Field(default=[])

		config1 = Config(name="config1")
		config2 = Config(name="config2")

		# Modify one instance
		config1.tags.append("tag1")

		# Other instance should not be affected
		self.assertEqual(config1.tags, ["tag1"])
		self.assertEqual(config2.tags, [])

	def test_default_value_with_strip_whitespace(self) -> None:
		"""Test default values work with strip_whitespace constraint."""

		class User(Statica):
			name: str = Field(default="  John  ", strip_whitespace=True)
			title: str | None = Field(default=None)

		user = User()
		self.assertEqual(user.name, "John")  # Should be stripped
		self.assertIsNone(user.title)

	def test_field_without_default_requires_value(self) -> None:
		"""Test that fields without defaults still require values."""

		age_default = 25

		class User(Statica):
			name: str  # No default
			age: int = Field(default=25)

		# Should work when name is provided
		user = User(name="John")
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_default)

		# Should fail when name is missing
		with self.assertRaises(TypeValidationError):
			User()  # type: ignore[call-arg]

	def test_default_value_without_field(self) -> None:
		"""Test that default values can be set without using Field."""

		age_default = 25

		class User(Statica):
			name: str
			age: int = age_default  # Direct assignment without Field

		user = User(name="John")
		self.assertEqual(user.name, "John")
		self.assertEqual(user.age, age_default)

		user_from_map = User.from_map({"name": "Jane"})
		self.assertEqual(user_from_map.name, "Jane")
		self.assertEqual(user_from_map.age, age_default)

	def test_direct_assignment_various_types(self) -> None:
		"""Test direct assignment of default values for various types."""

		default_count = 42
		default_ratio = 3.14

		class Config(Statica):
			name: str
			count: int = default_count
			ratio: float = default_ratio
			enabled: bool = True
			description: str | None = None

		config = Config(name="test")
		self.assertEqual(config.name, "test")
		self.assertEqual(config.count, default_count)
		self.assertEqual(config.ratio, default_ratio)
		self.assertTrue(config.enabled)
		self.assertIsNone(config.description)

		# Test from_map
		config_from_map = Config.from_map({"name": "mapped"})
		self.assertEqual(config_from_map.count, default_count)
		self.assertEqual(config_from_map.ratio, default_ratio)
		self.assertTrue(config_from_map.enabled)
		self.assertIsNone(config_from_map.description)

	def test_direct_assignment_with_mutable_types(self) -> None:
		"""Test direct assignment with mutable default values are handled safely."""

		class Container(Statica):
			name: str
			items: list[str] = []  # noqa: RUF012
			metadata: dict[str, int] = {}  # noqa: RUF012
			tags: set[str] = set()  # noqa: RUF012

		container1 = Container(name="first")
		container2 = Container(name="second")

		# Modify mutable defaults on one instance
		container1.items.append("item1")
		container1.metadata["key"] = 1
		container1.tags.add("tag1")

		# Other instance should not be affected (copies should be made)
		self.assertEqual(container1.items, ["item1"])
		self.assertEqual(container1.metadata, {"key": 1})
		self.assertEqual(container1.tags, {"tag1"})

		self.assertEqual(container2.items, [])
		self.assertEqual(container2.metadata, {})
		self.assertEqual(container2.tags, set())

	def test_direct_assignment_mixed_with_field(self) -> None:
		"""Test mixing direct assignment with Field() usage."""

		default_port = 8080
		default_timeout = 30.0
		default_max_connections = 100
		override_port = 9000

		class MixedConfig(Statica):
			# Direct assignments
			name: str
			port: int = default_port
			debug: bool = False

			# Field() assignments
			timeout: float = Field(default=default_timeout, min_value=1.0)
			max_connections: int = Field(
				default=default_max_connections, min_value=1, max_value=1000
			)

		config = MixedConfig(name="server")
		self.assertEqual(config.name, "server")
		self.assertEqual(config.port, default_port)
		self.assertFalse(config.debug)
		self.assertEqual(config.timeout, default_timeout)
		self.assertEqual(config.max_connections, default_max_connections)

		# Test from_map
		config_from_map = MixedConfig.from_map({"name": "api-server", "port": override_port})
		self.assertEqual(config_from_map.name, "api-server")
		self.assertEqual(config_from_map.port, override_port)
		self.assertFalse(config_from_map.debug)
		self.assertEqual(config_from_map.timeout, default_timeout)
		self.assertEqual(config_from_map.max_connections, default_max_connections)

	def test_direct_assignment_override_with_explicit_values(self) -> None:
		"""Test that explicit values override direct assignment defaults."""

		default_retries = 3
		default_delay = 1.5
		override_retries = 5
		override_delay = 2.0
		map_retries = 10

		class Settings(Statica):
			name: str
			retries: int = default_retries
			delay: float = default_delay
			verbose: bool = False

		# Override all defaults
		settings = Settings(
			name="custom", retries=override_retries, delay=override_delay, verbose=True
		)
		self.assertEqual(settings.name, "custom")
		self.assertEqual(settings.retries, override_retries)
		self.assertEqual(settings.delay, override_delay)
		self.assertTrue(settings.verbose)

		# Override some defaults via from_map
		settings_from_map = Settings.from_map(
			{
				"name": "partial",
				"retries": map_retries,
			},
		)
		self.assertEqual(settings_from_map.name, "partial")
		self.assertEqual(settings_from_map.retries, map_retries)
		self.assertEqual(settings_from_map.delay, default_delay)  # default used
		self.assertFalse(settings_from_map.verbose)  # default used

	def test_direct_assignment_with_complex_types(self) -> None:
		"""Test direct assignment with complex types like unions."""

		default_value = 42
		override_value = 3.14
		map_value = 99.9

		class ComplexConfig(Statica):
			name: str
			value: int | float = default_value
			optional_data: str | None = None
			status: str = "pending"

		config = ComplexConfig(name="test")
		self.assertEqual(config.name, "test")
		self.assertEqual(config.value, default_value)
		self.assertIsNone(config.optional_data)
		self.assertEqual(config.status, "pending")

		# Test type validation still works
		config2 = ComplexConfig(name="test2", value=override_value)
		self.assertEqual(config2.value, override_value)

		# Test from_map
		config_from_map = ComplexConfig.from_map(
			{
				"name": "mapped",
				"value": map_value,
				"optional_data": "some data",
			},
		)
		self.assertEqual(config_from_map.value, map_value)
		self.assertEqual(config_from_map.optional_data, "some data")
		self.assertEqual(config_from_map.status, "pending")  # default used

	def test_direct_assignment_nested_statica(self) -> None:
		"""Test direct assignment with nested Statica objects."""

		default_port = 5432

		class DatabaseConfig(Statica):
			host: str = "localhost"
			port: int = default_port
			ssl: bool = False

		class AppConfig(Statica):
			name: str
			database: DatabaseConfig | None = None

		# Test with default None
		app = AppConfig(name="myapp")
		self.assertEqual(app.name, "myapp")
		self.assertIsNone(app.database)

		# Test with provided nested object
		app_with_db = AppConfig(name="webapp", database=DatabaseConfig(host="prod.db"))
		self.assertIsNotNone(app_with_db.database)
		self.assertEqual(app_with_db.database.host, "prod.db")
		self.assertEqual(app_with_db.database.port, default_port)  # default used
		self.assertFalse(app_with_db.database.ssl)  # default used

	def test_direct_assignment_to_dict_serialization(self) -> None:
		"""Test that to_dict works correctly with direct assignment defaults."""

		class Profile(Statica):
			username: str
			bio: str = "No bio provided"
			public: bool = True
			followers: int = 0

		profile = Profile(username="john_doe")

		result = profile.to_dict()
		expected = {
			"username": "john_doe",
			"bio": "No bio provided",
			"public": True,
			"followers": 0,
		}
		self.assertEqual(result, expected)

	def test_direct_assignment_constants(self) -> None:
		"""Test direct assignment using constants and computed values."""

		default_timeout = 30
		default_retries = 3
		expected_max_size = 30  # 3 * 10

		class ServiceConfig(Statica):
			name: str
			timeout: int = default_timeout
			retries: int = default_retries
			max_size: int = default_retries * 10  # computed default

		config = ServiceConfig(name="auth-service")
		self.assertEqual(config.timeout, default_timeout)
		self.assertEqual(config.retries, default_retries)
		self.assertEqual(config.max_size, expected_max_size)
