"""Tests for type coercion, custom codecs, and to_dict serialization."""

import unittest
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from uuid import UUID

from statica import Codec, Field, Statica, StaticaConfig, TypeValidationError

UUID_STR = "12345678-1234-5678-1234-567812345678"


class Color(Enum):
	RED = "red"
	GREEN = "green"


class TestCoercion(unittest.TestCase):
	def test_datetime_family(self) -> None:
		class Model(Statica):
			dt: datetime
			d: date
			t: time

		m = Model.from_map({"dt": "2020-01-02T03:04:05", "d": "2020-01-02", "t": "03:04:05"})
		self.assertEqual(m.dt, datetime(2020, 1, 2, 3, 4, 5))  # noqa: DTZ001
		self.assertEqual(m.d, date(2020, 1, 2))
		self.assertEqual(m.t, time(3, 4, 5))

	def test_uuid_and_decimal(self) -> None:
		class Model(Statica):
			id: UUID
			amount: Decimal

		m = Model.from_map({"id": UUID_STR, "amount": "9.99"})
		self.assertEqual(m.id, UUID(UUID_STR))
		self.assertEqual(m.amount, Decimal("9.99"))

	def test_enum(self) -> None:
		class Model(Statica):
			color: Color

		self.assertEqual(Model.from_map({"color": "red"}).color, Color.RED)
		self.assertEqual(Model(color=Color.GREEN).color, Color.GREEN)

		with self.assertRaises(TypeValidationError):
			Model.from_map({"color": "purple"})

	def test_already_typed_value_passes_through(self) -> None:
		class Model(Statica):
			dt: datetime

		now = datetime(2020, 1, 1)  # noqa: DTZ001
		self.assertIs(Model(dt=now).dt, now)

	def test_invalid_string_raises_type_error(self) -> None:
		class Model(Statica):
			dt: datetime

		with self.assertRaises(TypeValidationError):
			Model.from_map({"dt": "not-a-date"})

	def test_coercion_recurses_into_containers(self) -> None:
		class Model(Statica):
			stamps: list[datetime]
			ids: dict[str, UUID]

		m = Model.from_map(
			{
				"stamps": ["2020-01-01T00:00:00", "2021-01-01T00:00:00"],
				"ids": {"a": UUID_STR},
			},
		)
		self.assertTrue(all(isinstance(s, datetime) for s in m.stamps))
		self.assertEqual(m.ids["a"], UUID(UUID_STR))

	def test_optional_codec_type(self) -> None:
		class Model(Statica):
			dt: datetime | None

		self.assertIsNone(Model(dt=None).dt)
		self.assertEqual(
			Model.from_map({"dt": "2020-01-02T03:04:05"}).dt,
			datetime(2020, 1, 2, 3, 4, 5),  # noqa: DTZ001
		)


class TestToDict(unittest.TestCase):
	def test_encodes_special_types(self) -> None:
		class Model(Statica):
			dt: datetime
			id: UUID
			amount: Decimal
			color: Color

		m = Model(
			dt=datetime(2020, 1, 2, 3, 4, 5),  # noqa: DTZ001
			id=UUID(UUID_STR),
			amount=Decimal("9.99"),
			color=Color.RED,
		)
		self.assertEqual(
			m.to_dict(),
			{
				"dt": "2020-01-02T03:04:05",
				"id": UUID_STR,
				"amount": "9.99",
				"color": "red",
			},
		)

	def test_recurses_into_containers_of_models(self) -> None:
		class Item(Statica):
			name: str

		class Cart(Statica):
			items: list[Item]

		cart = Cart(items=[Item(name="a"), Item(name="b")])
		self.assertEqual(cart.to_dict(), {"items": [{"name": "a"}, {"name": "b"}]})

	def test_round_trip(self) -> None:
		class Model(Statica):
			dt: datetime
			ids: list[UUID]

		data = {"dt": "2020-01-02T03:04:05", "ids": [UUID_STR]}
		self.assertEqual(Model.from_map(data).to_dict(), data)


class TestSerializerHook(unittest.TestCase):
	def test_per_field_serializer(self) -> None:
		class Model(Statica):
			value: int = Field(serializer=lambda v: f"#{v}")

		self.assertEqual(Model(value=7).to_dict(), {"value": "#7"})


class TestCustomCodec(unittest.TestCase):
	def test_extend_codecs_via_config(self) -> None:
		class Temperature:
			def __init__(self, celsius: float) -> None:
				self.celsius = celsius

			def __eq__(self, other: object) -> bool:
				return isinstance(other, Temperature) and other.celsius == self.celsius

			__hash__ = None  # type: ignore[assignment]

		config = StaticaConfig.create(
			codecs={
				Temperature: Codec(
					decode=lambda v: Temperature(float(v)),
					encode=lambda v: v.celsius,
				),
			},
		)

		class Reading(Statica, config=config):
			temp: Temperature

		reading = Reading.from_map({"temp": "21.5"})
		self.assertEqual(reading.temp, Temperature(21.5))
		self.assertEqual(reading.to_dict(), {"temp": 21.5})


if __name__ == "__main__":
	unittest.main()
