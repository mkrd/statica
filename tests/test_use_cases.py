"""Real-world use case integration tests.

Each test models a realistic domain scenario and exercises multiple Statica
features in combination (aliases, constraints, defaults, cast_to, nested
objects, optional fields, from_map, to_dict, Literal, collections, custom
error classes).
"""

from typing import Any, Literal

import pytest

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


def test_user_profile_full_payload() -> None:
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
	assert user.first_name == "Alice"
	assert user.last_name == "Smith"
	assert user.address is not None
	assert user.address.city == "Berlin"
	assert user.role == "admin"

	# Round-trip preserves aliases
	serialized = user.to_dict()
	assert serialized["firstName"] == "Alice"
	assert serialized["homeAddress"]["cityName"] == "Berlin"

	user2 = UserProfile.from_map(serialized)
	assert user2.first_name == user.first_name
	assert user2.address is not None
	assert user2.address.zip_code == user.address.zip_code


def test_user_profile_minimal_payload_uses_defaults() -> None:
	payload = {
		"firstName": "Bob",
		"lastName": "Jones",
		"userAge": 25,
		"emailAddress": "bob@example.com",
	}

	user = UserProfile.from_map(payload)
	assert user.role == DEFAULT_ROLE
	assert user.bio is None
	assert user.address is None


def test_user_profile_rejects_invalid_role() -> None:
	payload = {
		"firstName": "Eve",
		"lastName": "Hacker",
		"userAge": 99,
		"emailAddress": "eve@example.com",
		"role": "superadmin",
	}
	with pytest.raises(TypeValidationError):
		UserProfile.from_map(payload)


def test_user_profile_rejects_short_email() -> None:
	payload = {
		"firstName": "X",
		"lastName": "Y",
		"userAge": 20,
		"emailAddress": "a@b",
	}
	with pytest.raises(ConstraintValidationError):
		UserProfile.from_map(payload)


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


def test_paginated_response_happy_path() -> None:
	raw = {
		"meta": {"page": 2, "pageSize": 10, "totalItems": 55},
		"items": ["SKU-001", "SKU-002", "SKU-003"],
	}
	resp = ProductListResponse.from_map(raw)
	page_num = 2
	page_size = 10
	total_items = 55
	item_count = 3

	assert resp.meta.current_page == page_num
	assert resp.meta.page_size == page_size
	assert resp.meta.total_items == total_items
	assert len(resp.items) == item_count

	# Serialize and verify aliases come back
	out = resp.to_dict()
	assert out["meta"]["page"] == page_num
	assert out["meta"]["pageSize"] == page_size


def test_paginated_response_defaults() -> None:
	raw: dict[str, Any] = {"meta": {"totalItems": 0}, "items": []}
	resp = ProductListResponse.from_map(raw)
	assert resp.meta.current_page == DEFAULT_PAGE
	assert resp.meta.page_size == DEFAULT_PAGE_SIZE
	assert resp.items == []


def test_paginated_response_rejects_oversized_page() -> None:
	raw: dict[str, Any] = {"meta": {"pageSize": 500, "totalItems": 10}, "items": []}
	with pytest.raises(ConstraintValidationError):
		ProductListResponse.from_map(raw)


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


def test_order_creation_and_serialization() -> None:
	raw = {
		"orderId": "ORD-2026-001",
		"status": "pending",
		"currency": "USD",
		"items": ["Widget A", "Widget B"],
		"discountPercent": DISCOUNT_PERCENT,
		"notes": "  rush delivery  ",
	}

	order = Order.from_map(raw)
	assert order.order_id == "ORD-2026-001"
	assert order.status == "pending"
	assert order.notes == "rush delivery"
	assert order.discount_percent == DISCOUNT_PERCENT

	# Serialize without aliases → Python field names
	flat = order.to_dict(with_aliases=False)
	assert "order_id" in flat
	assert "orderId" not in flat
	assert flat["notes"] == "rush delivery"


def test_order_uses_default_currency() -> None:
	raw = {
		"orderId": "ORD-2026-002",
		"status": "paid",
		"items": ["Gadget X"],
	}
	order = Order.from_map(raw)
	assert order.currency == DEFAULT_CURRENCY
	assert order.discount_percent is None
	assert order.notes is None


def test_order_rejects_invalid_status() -> None:
	raw: dict[str, Any] = {
		"orderId": "ORD-BAD",
		"status": "refunded",
		"items": [],
	}
	with pytest.raises(TypeValidationError):
		Order.from_map(raw)


def test_order_item_casts_quantity() -> None:
	raw = {"productName": "Bolt", "unitPrice": 0.99, "qty": "12"}
	item = OrderItem.from_map(raw)
	quantity = 12
	assert item.quantity == quantity
	assert isinstance(item.quantity, int)


def test_order_item_rejects_zero_quantity() -> None:
	raw = {"productName": "Bolt", "unitPrice": 0.99, "qty": 0}
	with pytest.raises(ConstraintValidationError):
		OrderItem.from_map(raw)


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


def test_webhook_full_config() -> None:
	raw = {
		"callbackUrl": "https://hooks.example.com/events",
		"method": "POST",
		"headers": {"Authorization": "Bearer tok_123", "X-Custom": "value"},
		"retryCount": 5,
		"signingSecret": "whsec_abc123",
	}
	hook = WebhookEndpoint.from_map(raw)
	retry_count = 5
	assert hook.url == "https://hooks.example.com/events"
	assert hook.retry_count == retry_count
	assert hook.headers["Authorization"] == "Bearer tok_123"
	expected_secret = "whsec_abc123"  # noqa: S105
	assert hook.secret == expected_secret


def test_webhook_defaults() -> None:
	raw = {"callbackUrl": "https://hooks.example.com/events"}
	hook = WebhookEndpoint.from_map(raw)
	assert hook.method == "POST"
	assert hook.headers == {}
	assert hook.retry_count == WEBHOOK_RETRY_COUNT
	assert hook.secret is None


def test_webhook_mutable_default_isolation() -> None:
	raw = {"callbackUrl": "https://hooks.example.com/a"}
	hook1 = WebhookEndpoint.from_map(raw)
	hook2 = WebhookEndpoint.from_map(raw)

	hook1.headers["X-Trace"] = "trace-1"
	assert "X-Trace" not in hook2.headers


def test_webhook_raises_domain_error_on_bad_type() -> None:
	raw = {"callbackUrl": 42}  # wrong type
	with pytest.raises(WebhookError):
		WebhookEndpoint.from_map(raw)


def test_webhook_raises_domain_error_on_short_url() -> None:
	raw = {"callbackUrl": "http://x"}
	with pytest.raises(WebhookError):
		WebhookEndpoint.from_map(raw)


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


def test_sensor_reading_full() -> None:
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

	assert reading.sensor_id == "sensor-42"
	assert reading.value == SENSOR_TEMP
	assert reading.tags == {"indoor", "lab"}  # deduplicated via cast_to=set
	assert reading.location is not None
	assert reading.location.lat == LAT_BERLIN
	assert reading.metadata["firmware"] == "v2.1"

	serialized = reading.to_dict()
	assert serialized["sensorId"] == "sensor-42"


def test_sensor_reading_minimal() -> None:
	raw = {
		"sensorId": "sensor-99",
		"reading_type": "humidity",
		"value": SENSOR_HUMIDITY,
		"unit": "%",
	}
	reading = SensorReading.from_map(raw)
	assert reading.tags == set()
	assert reading.location is None
	assert reading.metadata == {}


def test_sensor_reading_rejects_bad_reading_type() -> None:
	raw = {
		"sensorId": "sensor-1",
		"reading_type": "noise",
		"value": 50,
		"unit": "dB",
	}
	with pytest.raises(TypeValidationError):
		SensorReading.from_map(raw)


def test_sensor_custom_error_message() -> None:
	raw = {
		"sensorId": 123,  # wrong type
		"reading_type": "temperature",
		"value": 20,
		"unit": "°C",
	}
	with pytest.raises(TypeValidationError, match="Sensor validation"):
		SensorReading.from_map(raw)


def test_sensor_metadata_isolation() -> None:
	raw = {
		"sensorId": "s-1",
		"reading_type": "pressure",
		"value": 1013,
		"unit": "hPa",
	}
	r1 = SensorReading.from_map(raw)
	r2 = SensorReading.from_map(raw)
	r1.metadata["calibrated"] = "yes"
	assert "calibrated" not in r2.metadata


# ---------------------------------------------------------------------------
# 6. Multi-step form wizard — demonstrates mutating an instance after creation
#    and that descriptors re-validate on every __set__
# ---------------------------------------------------------------------------


class RegistrationForm(Statica):
	username: str = Field(min_length=3, max_length=30, strip_whitespace=True)
	password: str = Field(min_length=8)
	accepted_terms: bool


TEST_PASSWORD = "Str0ng!Pass"  # noqa: S105


def test_registration_form_valid_flow() -> None:
	form = RegistrationForm(
		username="  alice_dev  ",
		password=TEST_PASSWORD,
		accepted_terms=True,
	)
	assert form.username == "alice_dev"

	# Mutate after creation — descriptor should re-validate
	form.username = "bob_dev"
	assert form.username == "bob_dev"


def test_registration_form_rejects_mutation_violating_constraint() -> None:
	form = RegistrationForm(
		username="alice",
		password=TEST_PASSWORD,
		accepted_terms=True,
	)

	with pytest.raises(ConstraintValidationError):
		form.username = "ab"  # too short

	# Original value unchanged
	assert form.username == "alice"


def test_registration_form_rejects_mutation_wrong_type() -> None:
	form = RegistrationForm(
		username="alice",
		password=TEST_PASSWORD,
		accepted_terms=True,
	)

	with pytest.raises(TypeValidationError):
		form.accepted_terms = "yes"  # type: ignore[assignment]

	assert form.accepted_terms is True


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


def test_api_error_response_full() -> None:
	raw = {
		"status": HTTP_NOT_FOUND,
		"errorType": "not_found",
		"details": ["Resource /users/999 not found"],
		"requestId": "req-abc-123",
	}

	err = ApiErrorResponse.from_map(raw)
	assert err.status == HTTP_NOT_FOUND
	assert err.error_type == "not_found"
	assert len(err.details) == 1
	assert err.request_id == "req-abc-123"

	# Round-trip
	out = err.to_dict()
	err2 = ApiErrorResponse.from_map(out)
	assert err2.status == err.status
	assert err2.details == err.details


def test_api_error_validation_type() -> None:
	raw = {
		"status": HTTP_OK,
		"errorType": "validation",
		"details": ["name is required", "email is invalid"],
	}

	err = ApiErrorResponse.from_map(raw)
	detail_count = 2
	assert len(err.details) == detail_count
	assert err.request_id is None


def test_api_error_rejects_invalid_status_code() -> None:
	raw: dict[str, Any] = {"status": 999, "errorType": "server", "details": []}
	with pytest.raises(ConstraintValidationError):
		ApiErrorResponse.from_map(raw)


def test_error_detail_with_optional_code() -> None:
	raw_with = {"field": "email", "msg": "Invalid format", "code": "E1001"}
	detail = ErrorDetail.from_map(raw_with)
	assert detail.error_code == "E1001"

	raw_without = {"field": "name", "msg": "Required"}
	detail2 = ErrorDetail.from_map(raw_without)
	assert detail2.error_code is None

	# to_dict uses aliases
	assert detail.to_dict() == {"field": "email", "msg": "Invalid format", "code": "E1001"}
	assert detail2.to_dict() == {"field": "name", "msg": "Required", "code": None}
