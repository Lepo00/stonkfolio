from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.brokers.importers.base import TransactionData, TransactionType
from apps.brokers.services import ImportService
from apps.instruments.models import Instrument
from apps.portfolios.models import Holding, Portfolio, Transaction
from apps.users.models import User


@pytest.mark.django_db
class TestImportService:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")
        self.instrument = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="MSCI World",
            currency="EUR",
            asset_type="ETF",
        )

    def _make_tx(self, quantity="10", price="75.50", ref="ref1"):
        return TransactionData(
            isin="IE00B4L5Y983",
            product_name="MSCI World",
            type=TransactionType.BUY,
            quantity=Decimal(quantity),
            price=Decimal(price),
            fee=Decimal("2.00"),
            date=date(2025, 1, 15),
            currency="EUR",
            broker_reference=ref,
        )

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_creates_transactions(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        result = service.import_transactions(self.portfolio, [self._make_tx()])

        assert result.imported == 1
        assert result.skipped == 0
        assert Transaction.objects.filter(portfolio=self.portfolio).count() == 1

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_skips_duplicates(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(self.portfolio, [self._make_tx()])
        result = service.import_transactions(self.portfolio, [self._make_tx()])

        assert result.imported == 0
        assert result.skipped == 1
        assert Transaction.objects.filter(portfolio=self.portfolio).count() == 1

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_recalculates_holdings(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(
            self.portfolio,
            [
                self._make_tx(quantity="10", price="75.50", ref="ref1"),
                self._make_tx(quantity="5", price="76.00", ref="ref2"),
            ],
        )

        holding = Holding.objects.get(portfolio=self.portfolio, instrument=self.instrument)
        assert holding.quantity == Decimal("15")
        # (10*75.50 + 2.00 + 5*76.00 + 2.00) / 15 = 1139/15 = 75.9333
        assert abs(holding.avg_buy_price - Decimal("75.9333")) < Decimal("0.001")

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_sell_reduces_holding(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(
            self.portfolio,
            [
                self._make_tx(quantity="10", price="75.50", ref="ref1"),
            ],
        )
        sell_tx = TransactionData(
            isin="IE00B4L5Y983",
            product_name="MSCI World",
            type=TransactionType.SELL,
            quantity=Decimal("4"),
            price=Decimal("80.00"),
            fee=Decimal("2.00"),
            date=date(2025, 1, 20),
            currency="EUR",
            broker_reference="ref_sell",
        )
        service.import_transactions(self.portfolio, [sell_tx])

        holding = Holding.objects.get(portfolio=self.portfolio, instrument=self.instrument)
        assert holding.quantity == Decimal("6")
        # (10*75.50 + 2.00) / 10 = 75.70, unchanged after sell
        assert holding.avg_buy_price == Decimal("75.70")

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_full_sell_deletes_holding(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(
            self.portfolio,
            [
                self._make_tx(quantity="10", price="75.50", ref="ref1"),
            ],
        )
        sell_tx = TransactionData(
            isin="IE00B4L5Y983",
            product_name="MSCI World",
            type=TransactionType.SELL,
            quantity=Decimal("10"),
            price=Decimal("80.00"),
            fee=Decimal("2.00"),
            date=date(2025, 1, 20),
            currency="EUR",
            broker_reference="ref_sell_all",
        )
        service.import_transactions(self.portfolio, [sell_tx])

        assert not Holding.objects.filter(portfolio=self.portfolio, instrument=self.instrument).exists()
