"""Real-world use case integration tests.

Each test models a realistic domain scenario and exercises multiple Statica
features in combination (aliases, constraints, defaults, cast_to, nested
objects, optional fields, from_map, to_dict, Literal, collections, custom
error classes).
"""

import unittest
from typing import Any, Literal

from statica import Field, Statica, TypeValidationError
from statica.config import StaticaConfig
from statica.exceptions import ConstraintValidationError

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
MIN_AGE = 0
MAX_AGE = 150
MIN_NAME_LEN = 1
MAX_NAME_LEN = 100
MIN_EMAIL_LEN = 5
MAX_EMAIL_LEN = 254
DEFAULT_ROLE = "viewer"
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
HTTP_OK = 200
HTTP_NOT_FOUND = 404
DEFAULT_CURRENCY = "EUR"
PRODUCT_PRICE = 29.99
PRODUCT_QUANTITY = 3
DISCOUNT_PERCENT = 10.0
ORDER_TOTAL = 89.97
LAT_BERLIN = 52.52
LON_BERLIN = 13.405
SENSOR_TEMP = 22.5
SENSOR_HUMIDITY = 45
WEBHOOK_RETRY_COUNT = 3


# ---------------------------------------------------------------------------
# 1. User profile with address — nested objects, aliases, constraints,
#    optional fields, defaults, strip_whitespace
# ---------------------------------------------------------------------------


class Address(Statica):
	street: str = Field(alias="streetAddress", min_length=1, strip_whitespace=True)
	city: str = Field(alias="cityName", min_length=1, strip_whitespace=True)
	zip_code: str = Field(alias="zipCode", min_length=3, max_length=10)
	country: str = Field(alias="countryCode", min_length=2, max_length=2)


class UserProfile(Statica):
	first_name: str = Field(
		alias="firstName",
		min_length=MIN_NAME_LEN,
		max_length=MAX_NAME_LEN,
		strip_whitespace=True,
	)
	last_name: str = Field(
		alias="lastName",
		min_length=MIN_NAME_LEN,
		max_length=MAX_NAME_LEN,
		strip_whitespace=True,
	)
	age: int = Field(alias="userAge", min_value=MIN_AGE, max_value=MAX_AGE)
	email: str = Field(alias="emailAddress", min_length=MIN_EMAIL_LEN, max_length=MAX_EMAIL_LEN)
	role: Literal["admin", "editor", "viewer"] = Field(default="viewer")
	bio: str | None = Field(default=None, alias="biography")
	address: Address | None = Field(default=None, alias="homeAddress")


# ---------------------------------------------------------------------------
# 2. Paginated API response — generics (list), defaults, value constraints,
#    aliases, nested Statica in a list, to_dict round-trip
# ---------------------------------------------------------------------------


class PageMeta(Statica):
	current_page: int = Field(alias="page", default=DEFAULT_PAGE, min_value=1)
	page_size: int = Field(
		alias="pageSize",
		default=DEFAULT_PAGE_SIZE,
		min_value=1,
		max_value=MAX_PAGE_SIZE,
	)
	total_items: int = Field(alias="totalItems", min_value=0)


class ProductItem(Statica):
	sku: str = Field(alias="productSku", min_length=1)
	name: str = Field(alias="productName", min_length=1, max_length=MAX_NAME_LEN)
	price: float = Field(alias="unitPrice", min_value=0.0)
	in_stock: bool = Field(alias="inStock")


class ProductListResponse(Statica):
	meta: PageMeta
	items: list[str]  # serialised product SKUs for the lightweight endpoint


# ---------------------------------------------------------------------------
# 3. E-commerce order — multiple nested models, cast_to, constraints,
#    Literal status, optional discount, to_dict without aliases
# ---------------------------------------------------------------------------


class OrderItem(Statica):
	product_name: str = Field(alias="productName", min_length=1)
	unit_price: float = Field(alias="unitPrice", min_value=0.0)
	quantity: int = Field(alias="qty", min_value=1, cast_to=int)


class Order(Statica):
	order_id: str = Field(alias="orderId", min_length=1)
	status: Literal["pending", "paid", "shipped", "delivered", "cancelled"]
	currency: str = Field(default=DEFAULT_CURRENCY, min_length=3, max_length=3)
	items: list[str]  # product names as a flat list for the summary view
	discount_percent: float | None = Field(alias="discountPercent", default=None)
	notes: str | None = Field(default=None, strip_whitespace=True)


# ---------------------------------------------------------------------------
# 4. Webhook configuration — custom error class, casting, constraints,
#    Literal, defaults, dict field, optional nested
# ---------------------------------------------------------------------------


class WebhookError(Exception):
	"""Domain-specific error for webhook validation."""


class WebhookEndpoint(Statica):
	type_error_class = WebhookError
	constraint_error_class = WebhookError

	url: str = Field(alias="callbackUrl", min_length=10)
	method: Literal["GET", "POST", "PUT", "PATCH"] = Field(default="POST")
	headers: dict[str, str] = Field(default={})
	retry_count: int = Field(
		alias="retryCount",
		default=WEBHOOK_RETRY_COUNT,
		min_value=0,
		max_value=10,
	)
	secret: str | None = Field(default=None, alias="signingSecret")


# ---------------------------------------------------------------------------
# 5. IoT sensor reading — typed dict, union fields, cast_to, custom config
#    error messages, set field
# ---------------------------------------------------------------------------


sensor_config = StaticaConfig.create(
	type_error_message="Sensor validation: expected {expected_type}, got {found_type}",
)


class GeoCoord(Statica):
	lat: float = Field(min_value=-90.0, max_value=90.0)
	lon: float = Field(min_value=-180.0, max_value=180.0)


class SensorReading(Statica, config=sensor_config):
	sensor_id: str = Field(alias="sensorId", min_length=1)
	reading_type: Literal["temperature", "humidity", "pressure"]
	value: int | float
	unit: str
	tags: set[str] = Field(default=set(), cast_to=set)
	location: GeoCoord | None = Field(default=None)
	metadata: dict[str, str] = Field(default={})


# ---------------------------------------------------------------------------
# 6. Multi-step form wizard — demonstrates mutating an instance after creation
#    and that descriptors re-validate on every __set__
# ---------------------------------------------------------------------------


class RegistrationForm(Statica):
	username: str = Field(min_length=3, max_length=30, strip_whitespace=True)
	password: str = Field(min_length=8)
	accepted_terms: bool


TEST_PASSWORD = "Str0ng!Pass"  # noqa: S105


# ---------------------------------------------------------------------------
# 7. API error response — combines everything in a realistic HTTP error body
# ---------------------------------------------------------------------------


class ErrorDetail(Statica):
	field_name: str = Field(alias="field")
	message: str = Field(alias="msg", min_length=1)
	error_code: str | None = Field(alias="code", default=None)


class ApiErrorResponse(Statica):
	status: int = Field(min_value=100, max_value=599)
	error_type: Literal["validation", "authentication", "not_found", "server"] = Field(
		alias="errorType",
	)
	details: list[str]
	request_id: str | None = Field(alias="requestId", default=None)


class TestUseCases(unittest.TestCase):
	def test_user_profile_full_payload(self) -> None:
		payload = {
			"firstName": "  Alice  ",
			"lastName": "  Smith  ",
			"userAge": 30,
			"emailAddress": "alice@example.com",
			"role": "admin",
			"biography": "Loves Python",
			"homeAddress": {
				"streetAddress": " 123 Main St ",
				"cityName": " Berlin ",
				"zipCode": "10115",
				"countryCode": "DE",
			},
		}

		user = UserProfile.from_map(payload)
		self.assertEqual(user.first_name, "Alice")
		self.assertEqual(user.last_name, "Smith")
		self.assertIsNotNone(user.address)
		self.assertEqual(user.address.city, "Berlin")
		self.assertEqual(user.role, "admin")

		# Round-trip preserves aliases
		serialized = user.to_dict()
		self.assertEqual(serialized["firstName"], "Alice")
		self.assertEqual(serialized["homeAddress"]["cityName"], "Berlin")

		user2 = UserProfile.from_map(serialized)
		self.assertEqual(user2.first_name, user.first_name)
		self.assertIsNotNone(user2.address)
		self.assertEqual(user2.address.zip_code, user.address.zip_code)

	def test_user_profile_minimal_payload_uses_defaults(self) -> None:
		payload = {
			"firstName": "Bob",
			"lastName": "Jones",
			"userAge": 25,
			"emailAddress": "bob@example.com",
		}

		user = UserProfile.from_map(payload)
		self.assertEqual(user.role, DEFAULT_ROLE)
		self.assertIsNone(user.bio)
		self.assertIsNone(user.address)

	def test_user_profile_rejects_invalid_role(self) -> None:
		payload = {
			"firstName": "Eve",
			"lastName": "Hacker",
			"userAge": 99,
			"emailAddress": "eve@example.com",
			"role": "superadmin",
		}
		with self.assertRaises(TypeValidationError):
			UserProfile.from_map(payload)

	def test_user_profile_rejects_short_email(self) -> None:
		payload = {
			"firstName": "X",
			"lastName": "Y",
			"userAge": 20,
			"emailAddress": "a@b",
		}
		with self.assertRaises(ConstraintValidationError):
			UserProfile.from_map(payload)

	def test_paginated_response_happy_path(self) -> None:
		raw = {
			"meta": {"page": 2, "pageSize": 10, "totalItems": 55},
			"items": ["SKU-001", "SKU-002", "SKU-003"],
		}
		resp = ProductListResponse.from_map(raw)
		page_num = 2
		page_size = 10
		total_items = 55
		item_count = 3

		self.assertEqual(resp.meta.current_page, page_num)
		self.assertEqual(resp.meta.page_size, page_size)
		self.assertEqual(resp.meta.total_items, total_items)
		self.assertEqual(len(resp.items), item_count)

		# Serialize and verify aliases come back
		out = resp.to_dict()
		self.assertEqual(out["meta"]["page"], page_num)
		self.assertEqual(out["meta"]["pageSize"], page_size)

	def test_paginated_response_defaults(self) -> None:
		raw: dict[str, Any] = {"meta": {"totalItems": 0}, "items": []}
		resp = ProductListResponse.from_map(raw)
		self.assertEqual(resp.meta.current_page, DEFAULT_PAGE)
		self.assertEqual(resp.meta.page_size, DEFAULT_PAGE_SIZE)
		self.assertEqual(resp.items, [])

	def test_paginated_response_rejects_oversized_page(self) -> None:
		raw: dict[str, Any] = {"meta": {"pageSize": 500, "totalItems": 10}, "items": []}
		with self.assertRaises(ConstraintValidationError):
			ProductListResponse.from_map(raw)

	def test_order_creation_and_serialization(self) -> None:
		raw = {
			"orderId": "ORD-2026-001",
			"status": "pending",
			"currency": "USD",
			"items": ["Widget A", "Widget B"],
			"discountPercent": DISCOUNT_PERCENT,
			"notes": "  rush delivery  ",
		}

		order = Order.from_map(raw)
		self.assertEqual(order.order_id, "ORD-2026-001")
		self.assertEqual(order.status, "pending")
		self.assertEqual(order.notes, "rush delivery")
		self.assertEqual(order.discount_percent, DISCOUNT_PERCENT)

		# Serialize without aliases → Python field names
		flat = order.to_dict(with_aliases=False)
		self.assertIn("order_id", flat)
		self.assertNotIn("orderId", flat)
		self.assertEqual(flat["notes"], "rush delivery")

	def test_order_uses_default_currency(self) -> None:
		raw = {
			"orderId": "ORD-2026-002",
			"status": "paid",
			"items": ["Gadget X"],
		}
		order = Order.from_map(raw)
		self.assertEqual(order.currency, DEFAULT_CURRENCY)
		self.assertIsNone(order.discount_percent)
		self.assertIsNone(order.notes)

	def test_order_rejects_invalid_status(self) -> None:
		raw: dict[str, Any] = {
			"orderId": "ORD-BAD",
			"status": "refunded",
			"items": [],
		}
		with self.assertRaises(TypeValidationError):
			Order.from_map(raw)

	def test_order_item_casts_quantity(self) -> None:
		raw = {"productName": "Bolt", "unitPrice": 0.99, "qty": "12"}
		item = OrderItem.from_map(raw)
		quantity = 12
		self.assertEqual(item.quantity, quantity)
		self.assertIsInstance(item.quantity, int)

	def test_order_item_rejects_zero_quantity(self) -> None:
		raw = {"productName": "Bolt", "unitPrice": 0.99, "qty": 0}
		with self.assertRaises(ConstraintValidationError):
			OrderItem.from_map(raw)

	def test_webhook_full_config(self) -> None:
		raw = {
			"callbackUrl": "https://hooks.example.com/events",
			"method": "POST",
			"headers": {"Authorization": "Bearer tok_123", "X-Custom": "value"},
			"retryCount": 5,
			"signingSecret": "whsec_abc123",
		}
		hook = WebhookEndpoint.from_map(raw)
		retry_count = 5
		self.assertEqual(hook.url, "https://hooks.example.com/events")
		self.assertEqual(hook.retry_count, retry_count)
		self.assertEqual(hook.headers["Authorization"], "Bearer tok_123")
		expected_secret = "whsec_abc123"  # noqa: S105
		self.assertEqual(hook.secret, expected_secret)

	def test_webhook_defaults(self) -> None:
		raw = {"callbackUrl": "https://hooks.example.com/events"}
		hook = WebhookEndpoint.from_map(raw)
		self.assertEqual(hook.method, "POST")
		self.assertEqual(hook.headers, {})
		self.assertEqual(hook.retry_count, WEBHOOK_RETRY_COUNT)
		self.assertIsNone(hook.secret)

	def test_webhook_mutable_default_isolation(self) -> None:
		raw = {"callbackUrl": "https://hooks.example.com/a"}
		hook1 = WebhookEndpoint.from_map(raw)
		hook2 = WebhookEndpoint.from_map(raw)

		hook1.headers["X-Trace"] = "trace-1"
		self.assertNotIn("X-Trace", hook2.headers)

	def test_webhook_raises_domain_error_on_bad_type(self) -> None:
		raw = {"callbackUrl": 42}  # wrong type
		with self.assertRaises(WebhookError):
			WebhookEndpoint.from_map(raw)

	def test_webhook_raises_domain_error_on_short_url(self) -> None:
		raw = {"callbackUrl": "http://x"}
		with self.assertRaises(WebhookError):
			WebhookEndpoint.from_map(raw)

	def test_sensor_reading_full(self) -> None:
		raw = {
			"sensorId": "sensor-42",
			"reading_type": "temperature",
			"value": SENSOR_TEMP,
			"unit": "°C",
			"tags": ["indoor", "lab", "indoor"],
			"location": {"lat": LAT_BERLIN, "lon": LON_BERLIN},
			"metadata": {"firmware": "v2.1"},
		}
		reading = SensorReading.from_map(raw)

		self.assertEqual(reading.sensor_id, "sensor-42")
		self.assertEqual(reading.value, SENSOR_TEMP)
		self.assertEqual(reading.tags, {"indoor", "lab"})  # deduplicated via cast_to=set
		self.assertIsNotNone(reading.location)
		self.assertEqual(reading.location.lat, LAT_BERLIN)
		self.assertEqual(reading.metadata["firmware"], "v2.1")

		serialized = reading.to_dict()
		self.assertEqual(serialized["sensorId"], "sensor-42")

	def test_sensor_reading_minimal(self) -> None:
		raw = {
			"sensorId": "sensor-99",
			"reading_type": "humidity",
			"value": SENSOR_HUMIDITY,
			"unit": "%",
		}
		reading = SensorReading.from_map(raw)
		self.assertEqual(reading.tags, set())
		self.assertIsNone(reading.location)
		self.assertEqual(reading.metadata, {})

	def test_sensor_reading_rejects_bad_reading_type(self) -> None:
		raw = {
			"sensorId": "sensor-1",
			"reading_type": "noise",
			"value": 50,
			"unit": "dB",
		}
		with self.assertRaises(TypeValidationError):
			SensorReading.from_map(raw)

	def test_sensor_custom_error_message(self) -> None:
		raw = {
			"sensorId": 123,  # wrong type
			"reading_type": "temperature",
			"value": 20,
			"unit": "°C",
		}
		with self.assertRaisesRegex(TypeValidationError, "Sensor validation"):
			SensorReading.from_map(raw)

	def test_sensor_metadata_isolation(self) -> None:
		raw = {
			"sensorId": "s-1",
			"reading_type": "pressure",
			"value": 1013,
			"unit": "hPa",
		}
		r1 = SensorReading.from_map(raw)
		r2 = SensorReading.from_map(raw)
		r1.metadata["calibrated"] = "yes"
		self.assertNotIn("calibrated", r2.metadata)

	def test_registration_form_valid_flow(self) -> None:
		form = RegistrationForm(
			username="  alice_dev  ",
			password=TEST_PASSWORD,
			accepted_terms=True,
		)
		self.assertEqual(form.username, "alice_dev")

		# Mutate after creation — descriptor should re-validate
		form.username = "bob_dev"
		self.assertEqual(form.username, "bob_dev")

	def test_registration_form_rejects_mutation_violating_constraint(self) -> None:
		form = RegistrationForm(
			username="alice",
			password=TEST_PASSWORD,
			accepted_terms=True,
		)

		with self.assertRaises(ConstraintValidationError):
			form.username = "ab"  # too short

		# Original value unchanged
		self.assertEqual(form.username, "alice")

	def test_registration_form_rejects_mutation_wrong_type(self) -> None:
		form = RegistrationForm(
			username="alice",
			password=TEST_PASSWORD,
			accepted_terms=True,
		)

		with self.assertRaises(TypeValidationError):
			form.accepted_terms = "yes"  # type: ignore[assignment]

		self.assertTrue(form.accepted_terms)

	def test_api_error_response_full(self) -> None:
		raw = {
			"status": HTTP_NOT_FOUND,
			"errorType": "not_found",
			"details": ["Resource /users/999 not found"],
			"requestId": "req-abc-123",
		}

		err = ApiErrorResponse.from_map(raw)
		self.assertEqual(err.status, HTTP_NOT_FOUND)
		self.assertEqual(err.error_type, "not_found")
		self.assertEqual(len(err.details), 1)
		self.assertEqual(err.request_id, "req-abc-123")

		# Round-trip
		out = err.to_dict()
		err2 = ApiErrorResponse.from_map(out)
		self.assertEqual(err2.status, err.status)
		self.assertEqual(err2.details, err.details)

	def test_api_error_validation_type(self) -> None:
		raw = {
			"status": HTTP_OK,
			"errorType": "validation",
			"details": ["name is required", "email is invalid"],
		}

		err = ApiErrorResponse.from_map(raw)
		detail_count = 2
		self.assertEqual(len(err.details), detail_count)
		self.assertIsNone(err.request_id)

	def test_api_error_rejects_invalid_status_code(self) -> None:
		raw: dict[str, Any] = {"status": 999, "errorType": "server", "details": []}
		with self.assertRaises(ConstraintValidationError):
			ApiErrorResponse.from_map(raw)

	def test_error_detail_with_optional_code(self) -> None:
		raw_with = {"field": "email", "msg": "Invalid format", "code": "E1001"}
		detail = ErrorDetail.from_map(raw_with)
		self.assertEqual(detail.error_code, "E1001")

		raw_without = {"field": "name", "msg": "Required"}
		detail2 = ErrorDetail.from_map(raw_without)
		self.assertIsNone(detail2.error_code)

		# to_dict uses aliases
		self.assertEqual(
			detail.to_dict(), {"field": "email", "msg": "Invalid format", "code": "E1001"}
		)
		self.assertEqual(detail2.to_dict(), {"field": "name", "msg": "Required", "code": None})
