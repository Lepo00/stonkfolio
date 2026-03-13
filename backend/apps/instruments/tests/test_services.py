from unittest.mock import MagicMock, patch

import pytest

from apps.instruments.models import Instrument
from apps.instruments.services import InstrumentResolver


@pytest.mark.django_db
class TestInstrumentResolver:
    def test_resolve_existing_instrument(self):
        inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="Test",
            currency="EUR",
            asset_type="ETF",
        )
        resolver = InstrumentResolver()
        result = resolver.get_or_create("IE00B4L5Y983", name="Test", currency="EUR")
        assert result.id == inst.id

    @patch("apps.instruments.services.yf")
    def test_resolve_new_instrument_from_yfinance(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = [{"symbol": "IWDA.AS", "shortname": "iShares MSCI World"}]
        mock_yf.Search.return_value = mock_search
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "sector": "Diversified",
            "country": "Ireland",
            "quoteType": "ETF",
        }
        mock_yf.Ticker.return_value = mock_ticker

        resolver = InstrumentResolver()
        result = resolver.get_or_create("IE00B4L5Y983", name="Test", currency="EUR")

        assert result.ticker == "IWDA.AS"
        assert result.sector == "Diversified"
        assert result.asset_type == "ETF"

    @patch("apps.instruments.services.yf")
    def test_resolve_unresolvable_instrument(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = []
        mock_yf.Search.return_value = mock_search

        resolver = InstrumentResolver()
        result = resolver.get_or_create("XX0000000000", name="Unknown", currency="EUR")

        assert result.ticker is None
        assert result.isin == "XX0000000000"
