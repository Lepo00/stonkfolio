from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.market_data.currency import CurrencyConverter


class TestCurrencyConverter:
    @patch("apps.market_data.currency.yf")
    def test_convert_eur_to_usd(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 1.08}
        mock_yf.Ticker.return_value = mock_ticker

        converter = CurrencyConverter()
        result = converter.convert(Decimal("100"), "EUR", "USD")
        assert result == Decimal("108.00")

    def test_same_currency_no_conversion(self):
        converter = CurrencyConverter()
        result = converter.convert(Decimal("100"), "EUR", "EUR")
        assert result == Decimal("100")
