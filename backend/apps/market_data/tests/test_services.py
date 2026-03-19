from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.instruments.models import Instrument
from apps.market_data.models import PriceCache
from apps.market_data.providers.base import PricePoint
from apps.market_data.services import BENCHMARK_MAP, MarketDataService


@pytest.mark.django_db
class TestMarketDataService:
    def setup_method(self):
        self.instrument = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="Test",
            currency="EUR",
            asset_type="ETF",
        )
        self.inst = self.instrument
        self.inst_no_ticker = Instrument.objects.create(
            isin="XX0000000000",
            name="No Ticker",
            currency="EUR",
            asset_type="OTHER",
        )

    @patch("apps.market_data.providers.yfinance_provider.yf")
    def test_get_current_price_fetches_and_caches(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 75.5, "currency": "EUR"}
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService()
        result = service.get_current_price(self.instrument)

        assert result.price == Decimal("75.5")
        assert PriceCache.objects.filter(instrument=self.instrument).exists()

    @patch("apps.market_data.providers.yfinance_provider.yf")
    def test_get_current_price_uses_cache_if_fresh(self, mock_yf):
        PriceCache.objects.create(instrument=self.instrument, price=Decimal("70.00"))

        service = MarketDataService()
        result = service.get_current_price(self.instrument)

        assert result.price == Decimal("70.00")
        mock_yf.Ticker.assert_not_called()

    @patch("apps.market_data.providers.yfinance_provider.yf")
    def test_get_historical_prices(self, mock_yf):
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [74.0, 75.0, 76.0]},
            index=pd.to_datetime(["2025-01-13", "2025-01-14", "2025-01-15"]),
        )
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService()
        prices = service.get_historical_prices(self.instrument, date(2025, 1, 13), date(2025, 1, 15))

        assert len(prices) == 3
        assert prices[0].price == Decimal("74.0")

    def test_get_ohlcv_delegates_to_provider(self):
        mock_provider = MagicMock()
        expected_df = pd.DataFrame({"Close": [100.0]})
        mock_provider.get_ohlcv.return_value = expected_df

        service = MarketDataService(provider=mock_provider)
        result = service.get_ohlcv(self.inst, "6mo", "1d")

        mock_provider.get_ohlcv.assert_called_once_with("IWDA.AS", "6mo", "1d")
        assert result is expected_df

    def test_get_ohlcv_no_ticker_raises(self):
        service = MarketDataService()
        with pytest.raises(ValueError, match="No ticker"):
            service.get_ohlcv(self.inst_no_ticker, "6mo", "1d")


@pytest.mark.django_db
class TestGetBenchmarkSeries:
    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_returns_base100_series(self, mock_hist):
        mock_hist.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("100.00")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("105.00")),
            PricePoint(date=date(2025, 1, 3), price=Decimal("110.00")),
        ]
        service = MarketDataService()
        result = service.get_benchmark_series("sp500", date(2025, 1, 1), date(2025, 1, 3))

        assert result is not None
        assert len(result) == 3
        assert result[0]["value"] == "100.00"
        assert result[1]["value"] == "105.00"
        assert result[2]["value"] == "110.00"

    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_normalizes_to_base_100(self, mock_hist):
        mock_hist.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("5000.00")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("5100.00")),
        ]
        service = MarketDataService()
        result = service.get_benchmark_series("sp500", date(2025, 1, 1), date(2025, 1, 2))

        assert result[0]["value"] == "100.00"
        assert result[1]["value"] == "102.00"

    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_unknown_benchmark_returns_none(self, mock_hist):
        service = MarketDataService()
        result = service.get_benchmark_series("nasdaq", date(2025, 1, 1), date(2025, 1, 3))

        assert result is None
        mock_hist.assert_not_called()

    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_empty_prices_returns_none(self, mock_hist):
        mock_hist.return_value = []
        service = MarketDataService()
        result = service.get_benchmark_series("sp500", date(2025, 6, 1), date(2025, 6, 3))

        assert result is None

    def test_benchmark_map_has_expected_keys(self):
        assert "sp500" in BENCHMARK_MAP
        assert "msci_world" in BENCHMARK_MAP
        assert BENCHMARK_MAP["sp500"]["ticker"] == "^GSPC"
        assert BENCHMARK_MAP["msci_world"]["ticker"] == "IWDA.AS"
