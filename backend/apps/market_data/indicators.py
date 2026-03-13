from __future__ import annotations

import pandas as pd


def calculate_sma(closes: pd.Series, window: int, *, intraday: bool = False) -> list[dict]:
    """Calculate Simple Moving Average. Returns list of {time, value} dicts."""
    sma = closes.rolling(window=window).mean().dropna()
    return [
        {"time": _format_time(idx, intraday), "value": round(float(val), 4)}
        for idx, val in sma.items()
    ]


def calculate_rsi(closes: pd.Series, window: int = 14, *, intraday: bool = False) -> list[dict]:
    """Calculate Relative Strength Index. Returns list of {time, value} dicts."""
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.replace([float("inf"), float("-inf")], float("nan"))
    rsi = rsi.fillna(50.0)
    rsi = rsi.iloc[window:]  # drop the initial window where rolling mean is NaN

    return [
        {"time": _format_time(idx, intraday), "value": round(float(val), 2)}
        for idx, val in rsi.items()
    ]


def _format_time(idx, intraday: bool = False) -> str | int:
    """Format pandas index to date string (daily) or unix timestamp (intraday)."""
    if intraday:
        return int(idx.timestamp())
    if hasattr(idx, "date"):
        return str(idx.date())
    return str(idx)
