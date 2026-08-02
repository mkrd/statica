"""
Scenario: parsing, validating and serializing e-commerce orders.

Exercises, end to end:
- Nested models and lists of models (Order -> LineItem -> Product -> Money)
- JSON ingest via `from_map` with camelCase aliases from an external API
- Coercion of UUID / datetime / Decimal / Enum from JSON strings
- Frozen value objects (Money) used for value-equality and hashing
- Field-level validators (positive quantity) and constraints (SKU length)
- Cross-field invariants via `__post_init__` (subtotal, discount, currency)
- Full serialization round-trips and precise error paths for bad input
"""

import unittest
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from statica import (
	ConstraintValidationError,
	Field,
	FrozenInstanceError,
	Statica,
	TypeValidationError,
)

ORDER_ID = "3f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8"


class Currency(Enum):
	USD = "USD"
	EUR = "EUR"


class OrderStatus(Enum):
	PENDING = "pending"
	PAID = "paid"
	SHIPPED = "shipped"


class Money(Statica, frozen=True):
	"""Immutable, hashable value object."""

	amount: Decimal
	currency: Currency


class Product(Statica):
	sku: str = Field(min_length=3, max_length=20, strip_whitespace=True)
	name: str = Field(min_length=1)
	unit_price: Money = Field(alias="unitPrice")
	tags: frozenset[str] = Field(default=frozenset(), cast_to=frozenset)


def _positive_quantity(value: int) -> int:
	if value <= 0:
		msg = "quantity must be positive"
		raise ValueError(msg)
	return value


class LineItem(Statica):
	product: Product
	quantity: int = Field(validator=_positive_quantity)


class Order(Statica):
	order_id: UUID = Field(alias="orderId")
	status: OrderStatus
	created_at: datetime = Field(alias="createdAt")
	currency: Currency
	items: list[LineItem]
	subtotal: Decimal
	discount: Decimal = Field(default=Decimal(0))

	def __post_init__(self) -> None:
		computed = sum(
			(item.product.unit_price.amount * item.quantity for item in self.items),
			Decimal(0),
		)
		if computed != self.subtotal:
			msg = f"subtotal mismatch: computed {computed}, declared {self.subtotal}"
			raise ValueError(msg)
		if self.discount > self.subtotal:
			msg = "discount cannot exceed subtotal"
			raise ValueError(msg)
		for item in self.items:
			if item.product.unit_price.currency is not self.currency:
				msg = "line item currency does not match order currency"
				raise ValueError(msg)

	def total(self) -> Money:
		return Money(amount=self.subtotal - self.discount, currency=self.currency)


def _valid_payload() -> dict[str, Any]:
	return {
		"orderId": ORDER_ID,
		"status": "paid",
		"createdAt": "2024-03-15T10:30:00",
		"currency": "USD",
		"items": [
			{
				"product": {
					"sku": "WIDGET-01",
					"name": "Blue Widget",
					"unitPrice": {"amount": "9.99", "currency": "USD"},
					"tags": ["hardware", "blue"],
				},
				"quantity": 3,
			},
			{
				"product": {
					"sku": "GADGET-02",
					"name": "Red Gadget",
					"unitPrice": {"amount": "4.50", "currency": "USD"},
				},
				"quantity": 2,
			},
		],
		"subtotal": "38.97",
		"discount": "5.00",
	}


class TestEcommerceOrderScenario(unittest.TestCase):
	def test_parse_valid_order(self) -> None:
		order = Order.from_map(_valid_payload())

		self.assertEqual(order.order_id, UUID(ORDER_ID))
		self.assertIs(order.status, OrderStatus.PAID)
		self.assertEqual(order.created_at, datetime(2024, 3, 15, 10, 30, 0))  # noqa: DTZ001
		self.assertIs(order.currency, Currency.USD)
		self.assertEqual(len(order.items), 2)

		first = order.items[0]
		self.assertEqual(first.quantity, 3)
		self.assertEqual(first.product.sku, "WIDGET-01")
		expected_price = Money(amount=Decimal("9.99"), currency=Currency.USD)
		self.assertEqual(first.product.unit_price, expected_price)
		self.assertEqual(first.product.tags, frozenset({"hardware", "blue"}))
		self.assertEqual(order.items[1].product.tags, frozenset())

	def test_computed_total(self) -> None:
		order = Order.from_map(_valid_payload())
		# subtotal 38.97 - discount 5.00 = 33.97
		self.assertEqual(order.total(), Money(amount=Decimal("33.97"), currency=Currency.USD))

	def test_money_value_object_semantics(self) -> None:
		price_a = Money(amount=Decimal("9.99"), currency=Currency.USD)
		price_b = Money(amount=Decimal("9.99"), currency=Currency.USD)
		price_c = Money(amount=Decimal("9.99"), currency=Currency.EUR)

		self.assertEqual(price_a, price_b)
		self.assertNotEqual(price_a, price_c)
		# Hashable and de-duplicated by value.
		self.assertEqual(len({price_a, price_b, price_c}), 2)
		# Immutable.
		with self.assertRaises(FrozenInstanceError):
			price_a.amount = Decimal(0)  # type: ignore[read-only]

	def test_serialization_round_trip(self) -> None:
		order = Order.from_map(_valid_payload())
		serialized = order.to_dict()

		# Aliases and codec encodings appear in the serialized form.
		self.assertEqual(serialized["orderId"], ORDER_ID)
		self.assertEqual(serialized["createdAt"], "2024-03-15T10:30:00")
		self.assertEqual(serialized["subtotal"], "38.97")
		self.assertEqual(
			serialized["items"][0]["product"]["unitPrice"],
			{"amount": "9.99", "currency": "USD"},
		)

		# Re-parsing the serialized form yields an equal order (handles frozenset
		# ordering by value equality).
		self.assertEqual(Order.from_map(serialized), order)

	def test_two_independent_parses_are_equal(self) -> None:
		self.assertEqual(Order.from_map(_valid_payload()), Order.from_map(_valid_payload()))

	def test_subtotal_mismatch_rejected(self) -> None:
		payload = _valid_payload()
		payload["subtotal"] = "40.00"
		with self.assertRaisesRegex(ValueError, "subtotal mismatch"):
			Order.from_map(payload)

	def test_discount_exceeds_subtotal_rejected(self) -> None:
		payload = _valid_payload()
		payload["discount"] = "999.00"
		with self.assertRaisesRegex(ValueError, "discount cannot exceed"):
			Order.from_map(payload)

	def test_currency_mismatch_rejected(self) -> None:
		payload = _valid_payload()
		payload["items"][0]["product"]["unitPrice"]["currency"] = "EUR"
		with self.assertRaisesRegex(ValueError, "currency does not match"):
			Order.from_map(payload)

	def test_non_positive_quantity_error_path(self) -> None:
		payload = _valid_payload()
		payload["items"][0]["quantity"] = 0
		with self.assertRaises(ConstraintValidationError) as cm:
			Order.from_map(payload)
		self.assertEqual(str(cm.exception), "Order.items[0].quantity: quantity must be positive")

	def test_sku_too_short_error_path(self) -> None:
		payload = _valid_payload()
		payload["items"][1]["product"]["sku"] = "AB"
		with self.assertRaises(ConstraintValidationError) as cm:
			Order.from_map(payload)
		self.assertEqual(
			str(cm.exception),
			"Order.items[1].product.sku: length must be at least 3",
		)

	def test_bad_nested_price_type_error_path(self) -> None:
		payload = _valid_payload()
		payload["items"][0]["product"]["unitPrice"]["amount"] = "not-a-number"
		with self.assertRaises(TypeValidationError) as cm:
			Order.from_map(payload)
		self.assertEqual(
			str(cm.exception),
			"Order.items[0].product.unit_price.amount: expected type 'Decimal', got 'str'",
		)


if __name__ == "__main__":
	unittest.main()
