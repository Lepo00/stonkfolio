from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PriceResult
from apps.portfolios.models import Holding, Portfolio, Transaction, TransactionType
from apps.users.models import User


@pytest.mark.django_db
class TestPortfolioDividendView:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")
        self.aapl = Instrument.objects.create(
            isin="US0378331005",
            ticker="AAPL",
            name="Apple Inc",
            currency="USD",
            asset_type="STOCK",
        )
        self.msft = Instrument.objects.create(
            isin="US5949181045",
            ticker="MSFT",
            name="Microsoft Corp",
            currency="USD",
            asset_type="STOCK",
        )
        self.etf = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="iShares MSCI World",
            currency="EUR",
            asset_type="ETF",
        )
        # Holdings: AAPL and MSFT have holdings, ETF has a holding but no dividends
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.aapl,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("150.00"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.msft,
            quantity=Decimal("5"),
            avg_buy_price=Decimal("300.00"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.etf,
            quantity=Decimal("20"),
            avg_buy_price=Decimal("75.00"),
        )

    def _create_dividend(self, instrument, amount, tx_date, ref):
        """Helper: create a DIVIDEND transaction. quantity=1, price=amount."""
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=instrument,
            type=TransactionType.DIVIDEND,
            quantity=Decimal("1"),
            price=Decimal(str(amount)),
            fee=Decimal("0"),
            date=tx_date,
            broker_source="manual",
            broker_reference=ref,
        )

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_summary(self, MockService):
        """Summary metrics are computed correctly."""
        MockService.return_value.get_current_price.return_value = PriceResult(price=Decimal("160.00"), currency="USD")
        today = date.today()
        # Recent dividends (within 12 months)
        self._create_dividend(self.aapl, "25.00", today - timedelta(days=30), "d1")
        self._create_dividend(self.aapl, "25.00", today - timedelta(days=120), "d2")
        self._create_dividend(self.msft, "15.00", today - timedelta(days=60), "d3")
        # Old dividend (outside 12 months)
        self._create_dividend(self.aapl, "20.00", today - timedelta(days=400), "d4")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        summary = resp.data["summary"]
        assert summary["total_dividends_12m"] == "65.00"
        assert summary["total_dividends_all_time"] == "85.00"
        assert summary["monthly_average_12m"] == "5.42"  # 65 / 12
        assert summary["dividend_holding_count"] == 2  # AAPL and MSFT
        assert summary["total_holding_count"] == 3

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_trailing_yield(self, MockService):
        """Trailing yield = total_12m / portfolio_value * 100."""
        # Portfolio value: AAPL 10*160=1600 + MSFT 5*300=1500 + ETF 20*80=1600 = 4700
        MockService.return_value.get_current_price.side_effect = [
            PriceResult(price=Decimal("160.00"), currency="USD"),
            PriceResult(price=Decimal("300.00"), currency="USD"),
            PriceResult(price=Decimal("80.00"), currency="EUR"),
        ]
        today = date.today()
        self._create_dividend(self.aapl, "100.00", today - timedelta(days=30), "d1")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK
        # yield = 100 / 4700 * 100 = 2.13
        assert resp.data["summary"]["trailing_yield_pct"] == "2.13"

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_monthly_history(self, MockService):
        """Monthly history returns 24 months, fills gaps with 0.00."""
        MockService.return_value.get_current_price.return_value = PriceResult(price=Decimal("160.00"), currency="USD")
        today = date.today()
        self._create_dividend(self.aapl, "25.00", today.replace(day=15), "d1")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        history = resp.data["monthly_history"]
        assert len(history) == 24
        # Most recent month first
        current_month = today.strftime("%Y-%m")
        assert history[0]["month"] == current_month
        assert history[0]["amount"] == "25.00"
        # Other months should be 0.00
        assert history[1]["amount"] == "0.00"

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_by_instrument(self, MockService):
        """By-instrument breakdown sorted by 12m total descending."""
        MockService.return_value.get_current_price.return_value = PriceResult(price=Decimal("160.00"), currency="USD")
        today = date.today()
        self._create_dividend(self.aapl, "50.00", today - timedelta(days=30), "d1")
        self._create_dividend(self.aapl, "50.00", today - timedelta(days=120), "d2")
        self._create_dividend(self.msft, "30.00", today - timedelta(days=60), "d3")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        by_inst = resp.data["by_instrument"]
        assert len(by_inst) == 2
        # AAPL first (100 > 30)
        assert by_inst[0]["ticker"] == "AAPL"
        assert by_inst[0]["total_12m"] == "100.00"
        assert by_inst[0]["payment_count_12m"] == 2
        # MSFT second
        assert by_inst[1]["ticker"] == "MSFT"
        assert by_inst[1]["total_12m"] == "30.00"
        # Percentages
        assert by_inst[0]["pct_of_total"] == "76.9"  # 100/130*100
        assert by_inst[1]["pct_of_total"] == "23.1"  # 30/130*100

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_recent_payments(self, MockService):
        """Recent payments returns last 10, newest first."""
        MockService.return_value.get_current_price.return_value = PriceResult(price=Decimal("160.00"), currency="USD")
        today = date.today()
        for i in range(12):
            self._create_dividend(self.aapl, "10.00", today - timedelta(days=i * 30), f"d{i}")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        recent = resp.data["recent_payments"]
        assert len(recent) == 10
        # Newest first
        assert recent[0]["date"] == str(today)
        assert recent[0]["instrument_name"] == "Apple Inc"
        assert recent[0]["ticker"] == "AAPL"
        assert recent[0]["amount"] == "10.00"

    def test_dividends_empty_portfolio(self):
        """No dividends returns zero summary and empty lists."""
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["summary"]["total_dividends_12m"] == "0.00"
        assert resp.data["summary"]["total_dividends_all_time"] == "0.00"
        assert resp.data["summary"]["trailing_yield_pct"] == "0.00"
        assert resp.data["summary"]["monthly_average_12m"] == "0.00"
        assert resp.data["by_instrument"] == []
        assert resp.data["recent_payments"] == []

    def test_dividends_other_user_forbidden(self):
        """Cannot access another user's portfolio dividends."""
        other = User.objects.create_user(username="other", password="pass12345")
        other_portfolio = Portfolio.objects.create(user=other, name="Other")
        resp = self.client.get(f"/api/portfolios/{other_portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
