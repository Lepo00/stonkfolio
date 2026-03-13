import pandas as pd
import pytest

from apps.market_data.indicators import calculate_sma, calculate_rsi


class TestCalculateSMA:
    def test_sma_basic(self):
        dates = pd.date_range("2025-01-01", periods=5, freq="D")
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        result = calculate_sma(closes, window=3)
        assert len(result) == 3
        assert result[0]["value"] == pytest.approx(2.0)
        assert result[1]["value"] == pytest.approx(3.0)
        assert result[2]["value"] == pytest.approx(4.0)
        assert result[0]["time"] == "2025-01-03"

    def test_sma_insufficient_data(self):
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        closes = pd.Series([1.0, 2.0], index=dates)
        result = calculate_sma(closes, window=5)
        assert result == []

    def test_sma_exact_window(self):
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        closes = pd.Series([10.0, 20.0, 30.0], index=dates)
        result = calculate_sma(closes, window=3)
        assert len(result) == 1
        assert result[0]["value"] == pytest.approx(20.0)


class TestCalculateRSI:
    def test_rsi_known_values(self):
        prices = [100.0 + i for i in range(15)] + [113.0]
        dates = pd.date_range("2025-01-01", periods=16, freq="D")
        closes = pd.Series(prices, index=dates)
        result = calculate_rsi(closes, window=14)
        assert len(result) >= 1
        assert result[0]["value"] > 90
        assert result[-1]["value"] < result[0]["value"]

    def test_rsi_insufficient_data(self):
        dates = pd.date_range("2025-01-01", periods=5, freq="D")
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        result = calculate_rsi(closes, window=14)
        assert result == []

    def test_rsi_bounds(self):
        dates = pd.date_range("2025-01-01", periods=50, freq="D")
        import numpy as np
        np.random.seed(42)
        closes = pd.Series(np.random.uniform(90, 110, 50), index=dates)
        result = calculate_rsi(closes, window=14)
        for point in result:
            assert 0 <= point["value"] <= 100
