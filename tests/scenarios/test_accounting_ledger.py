"""
Scenario: a double-entry accounting ledger.

Exercises, end to end:
- A shared base defining domain-specific error classes, inherited by every model, with
  correct (non-doubled) nested error paths
- Frozen `Money` value objects (Decimal + Currency) with value equality and hashing
- Numeric constraints applied to Decimal fields (min_value / max_value)
- Cross-field invariants via __post_init__: each entry must balance (debits == credits),
  use a single currency, and have at least two postings
- order=True to sort journal entries chronologically
- dict[str, Enum] chart of accounts, lists of nested models, aliases, and round-trips
"""

import unittest
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from statica import (
	ConstraintValidationError,
	Field,
	FrozenInstanceError,
	Statica,
	TypeValidationError,
)


class LedgerTypeError(TypeValidationError):
	"""Domain-specific type error."""


class LedgerConstraintError(ConstraintValidationError):
	"""Domain-specific constraint error."""


class LedgerError(ValueError):
	"""Business-rule violation raised from cross-field validation."""


class Currency(Enum):
	USD = "USD"
	EUR = "EUR"


class Direction(Enum):
	DEBIT = "debit"
	CREDIT = "credit"


class AccountType(Enum):
	ASSET = "asset"
	LIABILITY = "liability"
	EQUITY = "equity"
	REVENUE = "revenue"
	EXPENSE = "expense"


class LedgerModel(Statica):
	type_error_class = LedgerTypeError
	constraint_error_class = LedgerConstraintError


class Money(LedgerModel, frozen=True):
	amount: Decimal = Field(min_value=0)
	currency: Currency


class Posting(LedgerModel):
	account: str = Field(min_length=2)
	direction: Direction
	amount: Money


class JournalEntry(LedgerModel, order=True):
	date: datetime
	entry_id: str = Field(alias="entryId")
	memo: str
	postings: list[Posting]

	def __post_init__(self) -> None:
		if len(self.postings) < 2:  # noqa: PLR2004
			msg = "a journal entry needs at least two postings"
			raise LedgerError(msg)
		if len({p.amount.currency for p in self.postings}) != 1:
			msg = "all postings must share one currency"
			raise LedgerError(msg)
		debit_total = sum(
			(p.amount.amount for p in self.postings if p.direction is Direction.DEBIT),
			Decimal(0),
		)
		credit_total = sum(
			(p.amount.amount for p in self.postings if p.direction is Direction.CREDIT),
			Decimal(0),
		)
		if debit_total != credit_total:
			msg = f"entry does not balance: debits {debit_total} != credits {credit_total}"
			raise LedgerError(msg)


class Ledger(LedgerModel):
	name: str
	accounts: dict[str, AccountType]
	entries: list[JournalEntry]

	def balance_for(self, account: str) -> Decimal:
		"""Net debit balance for an account across all entries."""
		total = Decimal(0)
		for entry in self.entries:
			for posting in entry.postings:
				if posting.account != account:
					continue
				if posting.direction is Direction.DEBIT:
					total += posting.amount.amount
				else:
					total -= posting.amount.amount
		return total


def _valid_ledger() -> dict[str, Any]:
	return {
		"name": "main",
		"accounts": {"Cash": "asset", "Equity": "equity", "Equipment": "asset"},
		"entries": [
			{
				"entryId": "je-001",
				"date": "2024-01-01T09:00:00",
				"memo": "Initial funding",
				"postings": [
					{
						"account": "Cash",
						"direction": "debit",
						"amount": {"amount": "1000.00", "currency": "USD"},
					},
					{
						"account": "Equity",
						"direction": "credit",
						"amount": {"amount": "1000.00", "currency": "USD"},
					},
				],
			},
			{
				"entryId": "je-002",
				"date": "2024-01-05T14:30:00",
				"memo": "Buy equipment",
				"postings": [
					{
						"account": "Equipment",
						"direction": "debit",
						"amount": {"amount": "300.00", "currency": "USD"},
					},
					{
						"account": "Cash",
						"direction": "credit",
						"amount": {"amount": "300.00", "currency": "USD"},
					},
				],
			},
		],
	}


class TestAccountingLedgerScenario(unittest.TestCase):
	def test_parse_valid_ledger(self) -> None:
		ledger = Ledger.from_map(_valid_ledger())
		self.assertEqual(ledger.name, "main")
		self.assertEqual(ledger.accounts["Cash"], AccountType.ASSET)
		self.assertEqual(ledger.accounts["Equity"], AccountType.EQUITY)
		self.assertEqual(len(ledger.entries), 2)

		first = ledger.entries[0]
		self.assertEqual(first.entry_id, "je-001")
		self.assertEqual(first.date, datetime(2024, 1, 1, 9, 0, 0))  # noqa: DTZ001
		self.assertEqual(first.postings[0].account, "Cash")
		self.assertEqual(first.postings[0].direction, Direction.DEBIT)
		self.assertEqual(
			first.postings[0].amount,
			Money(amount=Decimal("1000.00"), currency=Currency.USD),
		)

	def test_balance_computation(self) -> None:
		ledger = Ledger.from_map(_valid_ledger())
		self.assertEqual(ledger.balance_for("Cash"), Decimal("700.00"))
		self.assertEqual(ledger.balance_for("Equipment"), Decimal("300.00"))
		self.assertEqual(ledger.balance_for("Equity"), Decimal("-1000.00"))

	def test_money_value_object(self) -> None:
		a = Money(amount=Decimal("1000.00"), currency=Currency.USD)
		b = Money(amount=Decimal("1000.00"), currency=Currency.USD)
		self.assertEqual(a, b)
		self.assertEqual(len({a, b}), 1)  # hashable, de-duplicated
		with self.assertRaises(FrozenInstanceError):
			a.currency = Currency.EUR  # type: ignore[read-only]

	def test_entries_sort_chronologically(self) -> None:
		ledger = Ledger.from_map(_valid_ledger())
		reversed_entries = list(reversed(ledger.entries))
		self.assertEqual(sorted(reversed_entries), ledger.entries)
		self.assertLess(ledger.entries[0], ledger.entries[1])

	def test_round_trip(self) -> None:
		ledger = Ledger.from_map(_valid_ledger())
		serialized = ledger.to_dict()
		self.assertEqual(
			serialized["accounts"], {"Cash": "asset", "Equity": "equity", "Equipment": "asset"}
		)
		self.assertEqual(serialized["entries"][0]["entryId"], "je-001")
		self.assertEqual(
			serialized["entries"][0]["postings"][0]["amount"],
			{"amount": "1000.00", "currency": "USD"},
		)
		self.assertEqual(Ledger.from_map(serialized), ledger)

	def test_negative_amount_uses_domain_constraint_error(self) -> None:
		data = _valid_ledger()
		data["entries"][0]["postings"][0]["amount"]["amount"] = "-5.00"
		with self.assertRaises(LedgerConstraintError) as cm:
			Ledger.from_map(data)
		self.assertEqual(
			str(cm.exception),
			"Ledger.entries[0].postings[0].amount.amount: must be at least 0",
		)

	def test_bad_amount_type_uses_domain_type_error_with_path(self) -> None:
		data = _valid_ledger()
		data["entries"][0]["postings"][1]["amount"]["amount"] = "not-a-number"
		with self.assertRaises(LedgerTypeError) as cm:
			Ledger.from_map(data)
		# Single, non-doubled path even with a custom error class.
		self.assertEqual(
			str(cm.exception),
			"Ledger.entries[0].postings[1].amount.amount: expected type 'Decimal', got 'str'",
		)

	def test_unbalanced_entry_rejected(self) -> None:
		data = _valid_ledger()
		data["entries"][0]["postings"][0]["amount"]["amount"] = "999.00"
		with self.assertRaisesRegex(LedgerError, "does not balance"):
			Ledger.from_map(data)

	def test_mixed_currency_entry_rejected(self) -> None:
		data = _valid_ledger()
		data["entries"][0]["postings"][0]["amount"]["currency"] = "EUR"
		with self.assertRaisesRegex(LedgerError, "share one currency"):
			Ledger.from_map(data)

	def test_single_posting_entry_rejected(self) -> None:
		data = _valid_ledger()
		data["entries"][0]["postings"] = data["entries"][0]["postings"][:1]
		with self.assertRaisesRegex(LedgerError, "at least two postings"):
			Ledger.from_map(data)


if __name__ == "__main__":
	unittest.main()
