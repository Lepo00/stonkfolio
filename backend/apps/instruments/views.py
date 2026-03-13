import logging
from decimal import Decimal

import yfinance as yf
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_data.indicators import calculate_rsi, calculate_sma
from apps.market_data.services import MarketDataService

from .models import Instrument
from .serializers import InstrumentSerializer

logger = logging.getLogger(__name__)


class InstrumentDetailView(APIView):
    """Get instrument details including current price and news."""

    def get(self, request, pk):
        try:
            instrument = Instrument.objects.get(pk=pk)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        data = InstrumentSerializer(instrument).data

        # Fetch current price
        if instrument.ticker:
            try:
                service = MarketDataService()
                price_result = service.get_current_price(instrument)
                data["current_price"] = f"{price_result.price:.2f}"
                data["price_currency"] = price_result.currency
            except Exception:
                logger.exception("Failed to fetch price for instrument %s", pk)
                data["current_price"] = None
                data["price_currency"] = None

        # Fetch news
        if instrument.ticker:
            try:
                data["news"] = self._get_news(instrument.ticker)
            except Exception:
                logger.exception("Failed to fetch news for instrument %s", pk)
                data["news"] = []
        else:
            data["news"] = []

        return Response(data)

    def _get_news(self, ticker: str) -> list[dict]:
        """Fetch latest news for a ticker from yfinance."""
        t = yf.Ticker(ticker)
        try:
            news = t.news or []
        except Exception:
            return []

        return [
            {
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
                "published": item.get("providerPublishTime", ""),
                "thumbnail": item.get("thumbnail", {}).get("resolutions", [{}])[0].get("url", "")
                if item.get("thumbnail")
                else "",
            }
            for item in news[:10]
        ]


class InstrumentAnalysisView(APIView):
    """AI-powered hold/sell recommendation based on basic technical indicators."""

    def get(self, request, pk):
        try:
            instrument = Instrument.objects.get(pk=pk)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        if not instrument.ticker:
            return Response({"error": "No ticker available for analysis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            analysis = self._analyze(instrument.ticker)
            return Response(analysis)
        except Exception:
            logger.exception("Analysis failed for instrument %s", pk)
            return Response({"error": "Analysis temporarily unavailable"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _analyze(self, ticker: str) -> dict:
        """
        Simple technical analysis based on moving averages and recent performance.
        Returns a recommendation: HOLD, SELL, or BUY with reasoning.
        """
        t = yf.Ticker(ticker)
        hist = t.history(period="6mo")

        if hist.empty or len(hist) < 20:
            return {
                "recommendation": "HOLD",
                "confidence": "low",
                "reasoning": "Insufficient data for analysis.",
                "signals": [],
            }

        current_price = Decimal(str(hist["Close"].iloc[-1]))
        sma_20 = Decimal(str(hist["Close"].tail(20).mean()))
        sma_50 = Decimal(str(hist["Close"].tail(50).mean())) if len(hist) >= 50 else sma_20

        # Calculate recent performance
        price_1w_ago = Decimal(str(hist["Close"].iloc[-5])) if len(hist) >= 5 else current_price
        price_1m_ago = Decimal(str(hist["Close"].iloc[-20])) if len(hist) >= 20 else current_price

        weekly_change = ((current_price - price_1w_ago) / price_1w_ago * 100) if price_1w_ago else Decimal("0")
        monthly_change = ((current_price - price_1m_ago) / price_1m_ago * 100) if price_1m_ago else Decimal("0")

        signals = []
        score = 0

        # Signal 1: Price vs SMA20
        if current_price > sma_20:
            signals.append({"signal": "Price above 20-day SMA", "sentiment": "bullish"})
            score += 1
        else:
            signals.append({"signal": "Price below 20-day SMA", "sentiment": "bearish"})
            score -= 1

        # Signal 2: Price vs SMA50
        if len(hist) >= 50:
            if current_price > sma_50:
                signals.append({"signal": "Price above 50-day SMA", "sentiment": "bullish"})
                score += 1
            else:
                signals.append({"signal": "Price below 50-day SMA", "sentiment": "bearish"})
                score -= 1

        # Signal 3: SMA crossover
        if sma_20 > sma_50:
            signals.append({"signal": "20-day SMA above 50-day SMA (golden cross)", "sentiment": "bullish"})
            score += 1
        elif len(hist) >= 50:
            signals.append({"signal": "20-day SMA below 50-day SMA (death cross)", "sentiment": "bearish"})
            score -= 1

        # Signal 4: Recent momentum
        if monthly_change > 5:
            signals.append({"signal": f"Strong monthly gain ({monthly_change:.1f}%)", "sentiment": "bullish"})
            score += 1
        elif monthly_change < -5:
            signals.append({"signal": f"Significant monthly loss ({monthly_change:.1f}%)", "sentiment": "bearish"})
            score -= 1

        # Determine recommendation
        if score >= 2:
            recommendation = "BUY"
            confidence = "medium"
        elif score <= -2:
            recommendation = "SELL"
            confidence = "medium"
        else:
            recommendation = "HOLD"
            confidence = "low"

        reasoning_parts = []
        bullish = [s for s in signals if s["sentiment"] == "bullish"]
        bearish = [s for s in signals if s["sentiment"] == "bearish"]

        if bullish:
            reasoning_parts.append(f"Bullish signals: {', '.join(s['signal'] for s in bullish)}.")
        if bearish:
            reasoning_parts.append(f"Bearish signals: {', '.join(s['signal'] for s in bearish)}.")

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": " ".join(reasoning_parts) or "Mixed signals — consider holding.",
            "signals": signals,
            "metrics": {
                "current_price": f"{current_price:.2f}",
                "sma_20": f"{sma_20:.2f}",
                "sma_50": f"{sma_50:.2f}",
                "weekly_change_pct": f"{weekly_change:.2f}",
                "monthly_change_pct": f"{monthly_change:.2f}",
            },
        }


CHART_PERIOD_MAP = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "15m"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "ALL": ("max", "1wk"),
}


class InstrumentChartView(APIView):
    """OHLCV chart data with technical indicators."""

    def get(self, request, pk):
        try:
            instrument = Instrument.objects.get(pk=pk)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        if not instrument.ticker:
            return Response({"error": "No ticker available for chart data"}, status=status.HTTP_400_BAD_REQUEST)

        period = request.query_params.get("period", "6M")
        if period not in CHART_PERIOD_MAP:
            return Response(
                {"error": f"Invalid period. Allowed: {', '.join(CHART_PERIOD_MAP.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        yf_period, yf_interval = CHART_PERIOD_MAP[period]

        try:
            service = MarketDataService()
            df = service.get_ohlcv(instrument, yf_period, yf_interval)
        except Exception:
            logger.exception("Failed to fetch chart data for instrument %s", pk)
            return Response({"error": "Chart data temporarily unavailable"}, status=status.HTTP_502_BAD_GATEWAY)

        is_intraday = yf_interval in ("5m", "15m")
        ohlc = []
        for idx, row in df.iterrows():
            time_val = int(idx.timestamp()) if is_intraday else str(idx.date())
            ohlc.append({
                "time": time_val,
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })

        closes = df["Close"].astype(float)
        indicators = {
            "sma_20": calculate_sma(closes, window=20, intraday=is_intraday),
            "sma_50": calculate_sma(closes, window=50, intraday=is_intraday),
            "rsi_14": calculate_rsi(closes, window=14, intraday=is_intraday),
        }

        return Response({
            "ticker": instrument.ticker,
            "currency": instrument.currency,
            "ohlc": ohlc,
            "indicators": indicators,
        })
