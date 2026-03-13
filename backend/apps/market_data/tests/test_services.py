from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.instruments.models import Instrument
from apps.market_data.models import PriceCache
from apps.market_data.services import MarketDataService


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
