from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PriceResult
from apps.users.models import User


@pytest.mark.django_db
class TestInstrumentDetailAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="iShares MSCI World",
            currency="EUR",
            asset_type="ETF",
            sector="Diversified",
            country="Ireland",
        )

    @patch("apps.instruments.views.MarketDataService")
    @patch("apps.instruments.views.InstrumentDetailView._get_news")
    def test_get_instrument_detail(self, mock_news, MockService):
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("80.00"),
            currency="EUR",
        )
        mock_news.return_value = [
            {
                "title": "MSCI World hits high",
                "publisher": "Reuters",
                "link": "https://example.com",
                "published": "",
                "thumbnail": "",
            }
        ]

        resp = self.client.get(f"/api/instruments/{self.inst.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["isin"] == "IE00B4L5Y983"
        assert resp.data["current_price"] == "80.00"
        assert len(resp.data["news"]) == 1

    def test_instrument_not_found(self):
        resp = self.client.get("/api/instruments/99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestInstrumentAnalysisAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="Test",
            currency="EUR",
            asset_type="ETF",
        )

    @patch("apps.instruments.views.InstrumentAnalysisView._analyze")
    def test_get_analysis(self, mock_analyze):
        mock_analyze.return_value = {
            "recommendation": "HOLD",
            "confidence": "medium",
            "reasoning": "Mixed signals.",
            "signals": [
                {"signal": "Price above 20-day SMA", "sentiment": "bullish"},
                {"signal": "Price below 50-day SMA", "sentiment": "bearish"},
            ],
            "metrics": {
                "current_price": "80.00",
                "sma_20": "78.00",
                "sma_50": "82.00",
                "weekly_change_pct": "1.50",
                "monthly_change_pct": "-2.30",
            },
        }

        resp = self.client.get(f"/api/instruments/{self.inst.id}/analysis/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["recommendation"] == "HOLD"
        assert len(resp.data["signals"]) == 2

    def test_no_ticker_returns_error(self):
        inst = Instrument.objects.create(
            isin="XX0000000000",
            name="No Ticker",
            currency="EUR",
            asset_type="OTHER",
        )
        resp = self.client.get(f"/api/instruments/{inst.id}/analysis/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
