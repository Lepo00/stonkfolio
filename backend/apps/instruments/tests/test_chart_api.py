from unittest.mock import patch

import pandas as pd
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.users.models import User


@pytest.mark.django_db
class TestInstrumentChartAPI:
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
        )

    def _mock_ohlcv_df(self, periods=30, freq="D"):
        dates = pd.date_range("2025-01-01", periods=periods, freq=freq)
        return pd.DataFrame(
            {
                "Open": [100.0 + i * 0.5 for i in range(periods)],
                "High": [101.0 + i * 0.5 for i in range(periods)],
                "Low": [99.0 + i * 0.5 for i in range(periods)],
                "Close": [100.5 + i * 0.5 for i in range(periods)],
                "Volume": [1000000 + i * 10000 for i in range(periods)],
            },
            index=dates,
        )

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_default_period(self, MockService):
        MockService.return_value.get_ohlcv.return_value = self._mock_ohlcv_df()
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["ticker"] == "IWDA.AS"
        assert resp.data["currency"] == "EUR"
        assert len(resp.data["ohlc"]) == 30
        assert "open" in resp.data["ohlc"][0]
        assert "high" in resp.data["ohlc"][0]
        assert "low" in resp.data["ohlc"][0]
        assert "close" in resp.data["ohlc"][0]
        assert "volume" in resp.data["ohlc"][0]
        assert "time" in resp.data["ohlc"][0]

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_with_indicators(self, MockService):
        MockService.return_value.get_ohlcv.return_value = self._mock_ohlcv_df(periods=60)
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=3M")
        assert resp.status_code == status.HTTP_200_OK
        assert "sma_20" in resp.data["indicators"]
        assert "sma_50" in resp.data["indicators"]
        assert "rsi_14" in resp.data["indicators"]
        assert len(resp.data["indicators"]["sma_20"]) == 41
        assert len(resp.data["indicators"]["sma_50"]) == 11

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_sparse_data_indicators_empty(self, MockService):
        MockService.return_value.get_ohlcv.return_value = self._mock_ohlcv_df(periods=10)
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=1M")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["ohlc"]) == 10
        assert resp.data["indicators"]["sma_20"] == []
        assert resp.data["indicators"]["sma_50"] == []

    def test_chart_invalid_period(self):
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=INVALID")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_chart_instrument_not_found(self):
        resp = self.client.get("/api/instruments/99999/chart/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_chart_no_ticker(self):
        inst = Instrument.objects.create(
            isin="XX0000000000",
            name="No Ticker",
            currency="EUR",
            asset_type="OTHER",
        )
        resp = self.client.get(f"/api/instruments/{inst.id}/chart/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_intraday_returns_unix_timestamps(self, MockService):
        dates = pd.date_range("2025-01-15 09:30", periods=10, freq="5min")
        df = pd.DataFrame(
            {
                "Open": [100.0] * 10,
                "High": [101.0] * 10,
                "Low": [99.0] * 10,
                "Close": [100.5] * 10,
                "Volume": [50000] * 10,
            },
            index=dates,
        )
        MockService.return_value.get_ohlcv.return_value = df
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=1D")
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data["ohlc"][0]["time"], int)
