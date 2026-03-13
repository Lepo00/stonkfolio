from datetime import date
from decimal import Decimal

import pytest

from apps.instruments.models import Instrument
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.users.models import User


@pytest.mark.django_db
class TestPortfolioModels:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.instrument = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="MSCI World",
            currency="EUR",
            asset_type="ETF",
        )

    def test_create_portfolio(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        assert p.name == "Main"
        assert p.user == self.user

    def test_create_transaction(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        t = Transaction.objects.create(
            portfolio=p,
            instrument=self.instrument,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("2.00"),
            date=date(2025, 1, 15),
            broker_source="degiro",
            broker_reference="abc123",
        )
        assert t.quantity == Decimal("10")
        assert t.type == TransactionType.BUY

    def test_broker_reference_unique_per_portfolio(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        Transaction.objects.create(
            portfolio=p,
            instrument=self.instrument,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("0"),
            date=date(2025, 1, 15),
            broker_source="degiro",
            broker_reference="abc123",
        )
        with pytest.raises(Exception):
            Transaction.objects.create(
                portfolio=p,
                instrument=self.instrument,
                type=TransactionType.BUY,
                quantity=Decimal("5"),
                price=Decimal("76.00"),
                fee=Decimal("0"),
                date=date(2025, 1, 16),
                broker_source="degiro",
                broker_reference="abc123",
            )
