from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PricePoint, PriceResult
from apps.portfolios.models import Holding, Portfolio, Transaction, TransactionType
from apps.portfolios.returns import calculate_twr, calculate_xirr
from apps.users.models import User


@pytest.mark.django_db
class TestCalculateTWR:
    def setup_method(self):
        self.user = User.objects.create_user(username="twr_test", password="pass1234567890")
        self.portfolio = Portfolio.objects.create(user=self.user, name="TWR")
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="MSCI World",
            currency="EUR",
            asset_type="ETF",
            sector="Diversified",
            country="Ireland",
        )

    def test_no_transactions_returns_none(self):
        service = MagicMock()
        assert calculate_twr(self.portfolio, service) is None

    @patch("apps.portfolios.returns.date")
    def test_single_holding_steady_price(self, mock_date):
        """If price doesn't change, TWR should be ~0%."""
        mock_date.today.return_value = date(2025, 2, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("100"),
        )

        service = MagicMock()
        prices = [PricePoint(date=date(2025, 1, 1) + timedelta(days=i), price=Decimal("100")) for i in range(31)]
        service.get_historical_prices.return_value = prices

        result = calculate_twr(self.portfolio, service)
        assert result is not None
        assert result == Decimal("0.00")

    @patch("apps.portfolios.returns.date")
    def test_positive_return(self, mock_date):
        """Price goes from 100 to 110 over 365 days -> ~10% annualized."""
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("100"),
        )

        service = MagicMock()
        # Linear price increase over 365 days: 100 -> 110
        prices = [
            PricePoint(
                date=date(2025, 1, 1) + timedelta(days=i),
                price=Decimal("100") + Decimal(str(i * 10 / 365)),
            )
            for i in range(366)
        ]
        service.get_historical_prices.return_value = prices

        result = calculate_twr(self.portfolio, service)
        assert result is not None
        # Over exactly 1 year, 10% gain -> annualized ~10%
        assert Decimal("9") < result < Decimal("11")


@pytest.mark.django_db
class TestCalculateXIRR:
    def setup_method(self):
        self.user = User.objects.create_user(username="xirr_test", password="pass1234567890")
        self.portfolio = Portfolio.objects.create(user=self.user, name="XIRR")
        self.inst = Instrument.objects.create(
            isin="US0378331005",
            ticker="AAPL",
            name="Apple Inc",
            currency="USD",
            asset_type="Stock",
            sector="Technology",
            country="US",
        )

    def test_no_transactions_returns_none(self):
        service = MagicMock()
        assert calculate_xirr(self.portfolio, service) is None

    @patch("apps.portfolios.returns.date")
    def test_simple_buy_and_hold(self, mock_date):
        """Buy at 100, now worth 110 after 1 year -> XIRR ~10%."""
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("100"),
        )

        service = MagicMock()
        service.get_current_price.return_value = PriceResult(
            price=Decimal("110"),
            currency="USD",
        )

        result = calculate_xirr(self.portfolio, service)
        assert result is not None
        # Cash flows: -1000 on 2025-01-01, +1100 on 2026-01-01 -> XIRR = 10%
        assert Decimal("9.5") < result < Decimal("10.5")

    @patch("apps.portfolios.returns.date")
    def test_buy_with_fee(self, mock_date):
        """Fees reduce the effective return."""
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("10"),
            date=date(2025, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("100"),
        )

        service = MagicMock()
        service.get_current_price.return_value = PriceResult(
            price=Decimal("110"),
            currency="USD",
        )

        result = calculate_xirr(self.portfolio, service)
        assert result is not None
        # Cash flows: -1010 on 2025-01-01, +1100 on 2026-01-01 -> ~8.9%
        assert result < Decimal("10.0")

    @patch("apps.portfolios.returns.date")
    def test_dividend_increases_return(self, mock_date):
        """Dividends are positive cash flows that increase XIRR."""
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.DIVIDEND,
            quantity=Decimal("10"),
            price=Decimal("2"),  # $2/share dividend
            fee=Decimal("0"),
            date=date(2025, 7, 1),
            broker_source="test",
            broker_reference="ref2",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("100"),
        )

        service = MagicMock()
        service.get_current_price.return_value = PriceResult(
            price=Decimal("110"),
            currency="USD",
        )

        result = calculate_xirr(self.portfolio, service)
        assert result is not None
        # Should be higher than 10% because of the dividend
        assert result > Decimal("10.0")

    def test_only_fee_transactions_returns_none(self):
        """FEE-only transactions should not produce cash flows for XIRR."""
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.FEE,
            quantity=Decimal("1"),
            price=Decimal("5"),
            fee=Decimal("5"),
            date=date(2025, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        service = MagicMock()
        assert calculate_xirr(self.portfolio, service) is None
