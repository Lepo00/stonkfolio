from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PricePoint
from apps.portfolios.models import Holding, Portfolio, Transaction, TransactionType
from apps.portfolios.risk_metrics import _calculate_risk_metrics_uncached
from apps.users.models import User


@pytest.mark.django_db
class TestRiskMetrics:
    def setup_method(self):
        self.user = User.objects.create_user(username="risk_test", password="pass1234567890")
        self.portfolio = Portfolio.objects.create(user=self.user, name="Risk")
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="MSCI World",
            currency="EUR",
            asset_type="ETF",
            sector="Diversified",
            country="Ireland",
        )

    def _create_holding(self, qty="10", price="100"):
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal(qty),
            price=Decimal(price),
            fee=Decimal("0"),
            date=date(2024, 1, 1),
            broker_source="test",
            broker_reference="ref1",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal(qty),
            avg_buy_price=Decimal(price),
        )

    def _make_service(self, portfolio_prices, benchmark_prices):
        """Build a mock service that returns given price lists."""
        service = MagicMock()
        service.get_historical_prices.return_value = portfolio_prices
        service.get_historical_prices_by_ticker.return_value = benchmark_prices
        return service

    def test_no_transactions_returns_none(self):
        service = MagicMock()
        result = _calculate_risk_metrics_uncached(self.portfolio, service)
        assert result["sharpe_ratio"] is None
        assert result["sortino_ratio"] is None
        assert result["beta"] is None
        assert result["alpha"] is None

    @patch("apps.portfolios.risk_metrics.date")
    def test_insufficient_data_returns_none(self, mock_date):
        """Fewer than MIN_DATA_POINTS should return all None."""
        mock_date.today.return_value = date(2024, 1, 20)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        # Only 10 days of data (need MIN_DATA_POINTS+1)
        prices = [PricePoint(date=date(2024, 1, 1) + timedelta(days=i), price=Decimal("100")) for i in range(10)]
        service = self._make_service(prices, prices)

        result = _calculate_risk_metrics_uncached(self.portfolio, service)
        assert result["sharpe_ratio"] is None

    @patch("apps.portfolios.risk_metrics.date")
    def test_sharpe_with_known_returns(self, mock_date):
        """With constant daily return, Sharpe should be deterministic."""
        n_days = 100
        mock_date.today.return_value = date(2024, 1, 1) + timedelta(days=n_days)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        # Portfolio: steady 0.1% daily gain
        daily_return = 0.001
        port_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(round(100 * (1 + daily_return) ** i, 6))),
            )
            for i in range(n_days + 1)
        ]

        # Benchmark: steady 0.05% daily gain
        bench_return = 0.0005
        bench_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(round(5000 * (1 + bench_return) ** i, 6))),
            )
            for i in range(n_days + 1)
        ]

        service = self._make_service(port_prices, bench_prices)
        result = _calculate_risk_metrics_uncached(self.portfolio, service)

        assert result["sharpe_ratio"] is not None
        # With constant returns, std is very small -> Sharpe is very large
        assert result["sharpe_ratio"] > 10

    @patch("apps.portfolios.risk_metrics.date")
    def test_sortino_no_downside_returns_none(self, mock_date):
        """If all returns are positive, sortino should be None (no downside)."""
        n_days = 50
        mock_date.today.return_value = date(2024, 1, 1) + timedelta(days=n_days)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        # Strictly increasing prices (all returns positive)
        port_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(100 + i)),
            )
            for i in range(n_days + 1)
        ]
        bench_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(5000 + i)),
            )
            for i in range(n_days + 1)
        ]

        service = self._make_service(port_prices, bench_prices)
        result = _calculate_risk_metrics_uncached(self.portfolio, service)

        assert result["sortino_ratio"] is None

    @patch("apps.portfolios.risk_metrics.date")
    def test_beta_one_when_matching_benchmark(self, mock_date):
        """If portfolio returns exactly match benchmark, beta should be ~1."""
        n_days = 60
        mock_date.today.return_value = date(2024, 1, 1) + timedelta(days=n_days)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        # Same return pattern for both
        import random

        random.seed(42)
        base_prices = [Decimal("100")]
        for _ in range(n_days):
            change = Decimal(str(round(random.gauss(0, 0.01), 6)))
            base_prices.append(base_prices[-1] * (1 + change))

        port_prices = [
            PricePoint(date=date(2024, 1, 1) + timedelta(days=i), price=p) for i, p in enumerate(base_prices)
        ]
        # Benchmark uses same returns but different price level
        bench_prices = [
            PricePoint(date=date(2024, 1, 1) + timedelta(days=i), price=p * 50) for i, p in enumerate(base_prices)
        ]

        service = self._make_service(port_prices, bench_prices)
        result = _calculate_risk_metrics_uncached(self.portfolio, service)

        assert result["beta"] is not None
        assert abs(result["beta"] - 1.0) < 0.01

    @patch("apps.portfolios.risk_metrics.date")
    def test_alpha_calculated(self, mock_date):
        """Alpha should be annualized_portfolio_return - beta * annualized_benchmark_return."""
        n_days = 60
        mock_date.today.return_value = date(2024, 1, 1) + timedelta(days=n_days)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        # Portfolio outperforms benchmark
        port_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(round(100 * 1.001**i, 6))),
            )
            for i in range(n_days + 1)
        ]
        bench_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(round(5000 * 1.0005**i, 6))),
            )
            for i in range(n_days + 1)
        ]

        service = self._make_service(port_prices, bench_prices)
        result = _calculate_risk_metrics_uncached(self.portfolio, service)

        assert result["alpha"] is not None
        # Portfolio grows faster, so alpha should be positive
        assert result["alpha"] > 0

    @patch("apps.portfolios.risk_metrics.date")
    def test_benchmark_fetch_failure_returns_empty(self, mock_date):
        """If benchmark data fetch fails, return all None."""
        n_days = 50
        mock_date.today.return_value = date(2024, 1, 1) + timedelta(days=n_days)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        port_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal("100"),
            )
            for i in range(n_days + 1)
        ]

        service = MagicMock()
        service.get_historical_prices.return_value = port_prices
        service.get_historical_prices_by_ticker.side_effect = Exception("Network error")

        result = _calculate_risk_metrics_uncached(self.portfolio, service)
        assert result["sharpe_ratio"] is None
        assert result["beta"] is None

    @patch("apps.portfolios.risk_metrics.date")
    def test_annualized_volatility_positive(self, mock_date):
        """Annualized volatility should be positive with varying prices."""
        n_days = 60
        mock_date.today.return_value = date(2024, 1, 1) + timedelta(days=n_days)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        self._create_holding()

        # Oscillating prices
        port_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(100 + (5 if i % 2 == 0 else -5))),
            )
            for i in range(n_days + 1)
        ]
        bench_prices = [
            PricePoint(
                date=date(2024, 1, 1) + timedelta(days=i),
                price=Decimal(str(5000 + i)),
            )
            for i in range(n_days + 1)
        ]

        service = self._make_service(port_prices, bench_prices)
        result = _calculate_risk_metrics_uncached(self.portfolio, service)

        assert result["annualized_volatility"] is not None
        assert result["annualized_volatility"] > 0
