# Portfolio Advice Engine: Rule Specification

> Comprehensive rule set for the AI-powered portfolio advisor.
> Each rule is self-contained and independently evaluable.

---

## Data Model Reference

The advice engine has access to the following data for each portfolio:

| Data Source | Fields Available |
|---|---|
| `Holding` | `quantity`, `avg_buy_price`, linked `Instrument` |
| `Instrument` | `ticker`, `name`, `isin`, `currency`, `sector`, `country`, `asset_type` (STOCK/ETF/BOND/FUND/OTHER) |
| `Transaction` | `type` (BUY/SELL/DIVIDEND/FEE/FX), `quantity`, `price`, `fee`, `date`, `broker_source` |
| `MarketDataService` | `get_current_price(instrument)` -> `PriceResult(price, currency)` |
| `MarketDataService` | `get_historical_prices(instrument, start, end)` -> `list[PricePoint(date, price)]` |
| `MarketDataService` | `get_ohlcv(instrument, period, interval)` -> `DataFrame[Open,High,Low,Close,Volume]` |
| `indicators.py` | `calculate_sma(closes, window)`, `calculate_rsi(closes, window=14)` |
| Derived | Portfolio performance time series (daily), allocation by sector/country/asset_type/currency |

---

## Response Schema

Each rule evaluation returns zero or more advice items matching this structure:

```python
@dataclass
class AdviceItem:
    rule_id: str           # e.g. "RISK_001"
    category: str          # risk | performance | diversification | cost | income | technical | behavioral | health
    priority: str          # critical | warning | info | positive
    title: str             # short label, e.g. "Single-Stock Concentration"
    message: str           # full advice text with interpolated values
    holdings: list[str]    # tickers of affected holdings (empty if portfolio-level)
    metadata: dict         # rule-specific numeric values for frontend rendering
```

Rules are evaluated in order of priority: critical first, then warning, info, positive. The frontend should display a maximum of ~8-10 items, prioritizing critical and warning.

---

## 1. Risk Management

### RISK_001 -- Single-Holding Concentration

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | critical if weight >= 40%, warning if weight >= 25% |
| **Data needed** | All holdings with current market values |
| **Condition** | Any single holding's market value / total portfolio value >= 25% |
| **Formula** | `weight_pct = (holding.quantity * current_price) / total_portfolio_value * 100` |
| **Template** | `"{name} ({ticker}) represents {weight_pct:.1f}% of your portfolio. A single position above {threshold}% creates significant concentration risk. Consider trimming to below 20% and reallocating to uncorrelated assets."` |
| **Metadata** | `{ "ticker": str, "weight_pct": float, "threshold": int }` |

### RISK_002 -- Top-3 Concentration

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | warning |
| **Data needed** | All holdings with current market values |
| **Condition** | Sum of the top 3 holdings by weight > 70% of portfolio |
| **Formula** | `top3_weight = sum(sorted(weights, reverse=True)[:3])` |
| **Template** | `"Your top 3 holdings ({name1}, {name2}, {name3}) account for {top3_pct:.1f}% of total value. Portfolios with heavy top-concentration are vulnerable to idiosyncratic shocks. Target keeping the top 3 below 60%."` |
| **Metadata** | `{ "top3_pct": float, "holdings": list[str] }` |

### RISK_003 -- Portfolio Volatility Alert

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | warning if annualized vol > 25%, critical if > 40% |
| **Data needed** | Portfolio performance daily series (minimum 30 data points) |
| **Condition** | Annualized portfolio volatility exceeds threshold |
| **Formula** | `daily_returns = series.pct_change().dropna()` | `ann_vol = daily_returns.std() * sqrt(252) * 100` |
| **Template** | `"Your portfolio's annualized volatility is {vol:.1f}%, which is {qualifier} than a typical balanced portfolio (12-15%). Consider adding bonds or low-volatility ETFs to reduce overall risk."` |
| **Metadata** | `{ "annualized_vol": float }` |
| **Note** | `qualifier = "moderately higher" if vol <= 35% else "significantly higher"` |

### RISK_004 -- Maximum Drawdown Warning

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | critical if drawdown > 30%, warning if > 15% |
| **Data needed** | Portfolio performance daily series (minimum 60 data points) |
| **Condition** | Max drawdown from peak within the trailing 12 months exceeds threshold |
| **Formula** | `cummax = series.cummax()` | `drawdown = (series - cummax) / cummax * 100` | `max_dd = drawdown.min()` |
| **Template** | `"Your portfolio experienced a {max_dd:.1f}% drawdown from its peak in the past 12 months. {follow_up}"` |
| **Note** | `follow_up = "This exceeds typical bear-market thresholds. Review your risk tolerance and ensure you have adequate emergency reserves." if max_dd < -30 else "Consider whether your asset allocation matches your risk tolerance."` |
| **Metadata** | `{ "max_drawdown_pct": float, "peak_date": str, "trough_date": str }` |

### RISK_005 -- Currency Exposure Concentration

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | warning |
| **Data needed** | Holdings with instrument.currency, current market values |
| **Condition** | A single non-base currency (i.e. not EUR, assuming EUR base) represents > 40% of portfolio value |
| **Formula** | `currency_weights = group_by(instrument.currency).sum(market_value) / total_value * 100` |
| **Template** | `"{pct:.0f}% of your portfolio is denominated in {currency}. Significant unhedged foreign-currency exposure adds exchange-rate risk. Consider whether this aligns with your outlook on {currency}/EUR."` |
| **Metadata** | `{ "currency": str, "weight_pct": float }` |

### RISK_006 -- Single-Country Exposure

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | warning |
| **Data needed** | Holdings with instrument.country, current market values |
| **Condition** | A single country represents > 60% of portfolio value (excluding holdings where country is Unknown) |
| **Formula** | `country_weights = group_by(instrument.country).sum(market_value) / total_value * 100` |
| **Template** | `"{pct:.0f}% of your portfolio is concentrated in {country}. Country-specific political, regulatory, or economic events could disproportionately impact your returns. Consider geographic diversification."` |
| **Metadata** | `{ "country": str, "weight_pct": float }` |

### RISK_007 -- Correlated Holdings Warning

| Field | Value |
|---|---|
| **Category** | risk |
| **Priority** | warning |
| **Data needed** | Historical prices for all holdings (90-day window), minimum 2 holdings with price data |
| **Condition** | Average pairwise correlation of daily returns across all holdings > 0.7 |
| **Formula** | For each pair of holdings with sufficient history: `corr = returns_a.corr(returns_b)`. Average all pairwise correlations. |
| **Template** | `"Your holdings have an average pairwise correlation of {avg_corr:.2f}. High correlation means your positions tend to move together, reducing the diversification benefit. Look for assets with lower or negative correlation to your existing holdings."` |
| **Metadata** | `{ "avg_correlation": float, "most_correlated_pair": [str, str], "pair_correlation": float }` |
| **Note** | This is computationally expensive. Cache the result and recompute at most once per day. Skip if portfolio has < 3 holdings with price data. |

---

## 2. Diversification

### DIV_001 -- Insufficient Holdings

| Field | Value |
|---|---|
| **Category** | diversification |
| **Priority** | warning if count < 5, info if count < 10 |
| **Data needed** | Count of holdings |
| **Condition** | Number of holdings < 10 |
| **Template (< 5)** | `"Your portfolio has only {count} position{s}. Academic research suggests a minimum of 15-20 holdings to achieve basic diversification. With so few positions, a single stock event could significantly impact your portfolio."` |
| **Template (5-9)** | `"Your portfolio has {count} positions. While better than a handful, you may still benefit from adding holdings across different sectors and geographies to improve diversification."` |
| **Metadata** | `{ "holding_count": int }` |

### DIV_002 -- Sector Concentration

| Field | Value |
|---|---|
| **Category** | diversification |
| **Priority** | critical if > 60%, warning if > 40% |
| **Data needed** | Holdings with instrument.sector, current market values |
| **Condition** | Any single sector > 40% of portfolio value (excluding "Unknown") |
| **Formula** | `sector_weights = group_by(instrument.sector).sum(market_value) / total_value * 100` |
| **Template** | `"{pct:.0f}% of your portfolio is in the {sector} sector. Sector-specific downturns (regulatory changes, commodity price shifts, tech corrections) could significantly impact your returns. Consider rebalancing to spread across at least 4-5 sectors."` |
| **Metadata** | `{ "sector": str, "weight_pct": float }` |

### DIV_003 -- Missing Sector Exposure

| Field | Value |
|---|---|
| **Category** | diversification |
| **Priority** | info |
| **Data needed** | Set of sectors present in portfolio, total number of holdings |
| **Condition** | Portfolio has >= 8 holdings but all are concentrated in <= 2 sectors |
| **Formula** | `unique_sectors = set(h.instrument.sector for h in holdings if h.instrument.sector)` |
| **Template** | `"Despite having {count} holdings, your portfolio only covers {sector_count} sector{s}: {sectors}. Spreading across more sectors can reduce correlation and smooth returns."` |
| **Metadata** | `{ "holding_count": int, "sector_count": int, "sectors": list[str] }` |

### DIV_004 -- Asset Class Imbalance

| Field | Value |
|---|---|
| **Category** | diversification |
| **Priority** | info |
| **Data needed** | Holdings with instrument.asset_type, current market values |
| **Condition** | Portfolio is 100% one asset type (e.g. all STOCKs) and has >= 5 holdings |
| **Formula** | `asset_types = set(h.instrument.asset_type for h in holdings)` |
| **Template** | `"Your portfolio is entirely composed of {asset_type}s. Adding other asset classes (bonds, ETFs, or funds) can reduce volatility and provide more stable returns during equity drawdowns."` |
| **Metadata** | `{ "asset_type": str, "weight_pct": 100.0 }` |

### DIV_005 -- Single-Geography Portfolio

| Field | Value |
|---|---|
| **Category** | diversification |
| **Priority** | info |
| **Data needed** | Holdings with instrument.country |
| **Condition** | All holdings with known country are from the same country, and portfolio has >= 5 holdings |
| **Template** | `"All your holdings are domiciled in {country}. International diversification can reduce country-specific risk and provide access to different growth cycles."` |
| **Metadata** | `{ "country": str }` |

---

## 3. Performance

### PERF_001 -- Overall Portfolio Return

| Field | Value |
|---|---|
| **Category** | performance |
| **Priority** | positive if return > 0, info if return <= 0 |
| **Data needed** | Total cost basis, total market value |
| **Condition** | Always generated (portfolio has holdings) |
| **Formula** | `return_pct = (total_value - total_cost) / total_cost * 100` |
| **Template (positive)** | `"Your portfolio is up {return_pct:.1f}% overall ({gain_eur:+.2f} EUR). {context}"` |
| **Template (negative)** | `"Your portfolio is down {return_pct:.1f}% overall ({loss_eur:.2f} EUR). {context}"` |
| **Note** | `context = "Stay focused on your long-term strategy and avoid panic-selling." if return < -10 else "Markets fluctuate -- paper losses are only realized if you sell." if return < 0 else ""` |
| **Metadata** | `{ "return_pct": float, "gain_loss_eur": float }` |

### PERF_002 -- Significant Underperformers

| Field | Value |
|---|---|
| **Category** | performance |
| **Priority** | warning if loss > 20%, info if loss > 10% |
| **Data needed** | Holdings with avg_buy_price and current price |
| **Condition** | Individual holding's unrealized loss exceeds threshold |
| **Formula** | `return_pct = (current_price - avg_buy_price) / avg_buy_price * 100` |
| **Template (> 20% loss)** | `"{name} ({ticker}) is down {loss_pct:.1f}% from your average cost. Losses of this magnitude warrant a fundamental review. Ask: would you buy this stock today at the current price? If not, consider cutting the position."` |
| **Template (10-20% loss)** | `"{name} ({ticker}) is down {loss_pct:.1f}% from your cost basis. Review whether the original investment thesis still holds."` |
| **Metadata** | `{ "ticker": str, "loss_pct": float, "cost_basis": float, "current_price": float }` |

### PERF_003 -- Strong Performers

| Field | Value |
|---|---|
| **Category** | performance |
| **Priority** | positive |
| **Data needed** | Holdings with avg_buy_price and current price |
| **Condition** | Individual holding's unrealized gain > 25% |
| **Formula** | `return_pct = (current_price - avg_buy_price) / avg_buy_price * 100` |
| **Template** | `"{name} ({ticker}) is up {gain_pct:.1f}% from your cost basis. Consider whether to take partial profits to lock in gains, or let it run if the fundamentals remain strong."` |
| **Metadata** | `{ "ticker": str, "gain_pct": float }` |

### PERF_004 -- Unrealized Loss Exceeds Threshold (Deep Losers)

| Field | Value |
|---|---|
| **Category** | performance |
| **Priority** | critical |
| **Data needed** | Holdings with avg_buy_price and current price |
| **Condition** | Individual holding's unrealized loss > 50% |
| **Formula** | `return_pct = (current_price - avg_buy_price) / avg_buy_price * 100` |
| **Template** | `"{name} ({ticker}) has lost {loss_pct:.1f}% of its value. A 50%+ loss requires a 100%+ gain just to break even. Seriously evaluate whether this position has a realistic recovery path or if the capital would be better deployed elsewhere."` |
| **Metadata** | `{ "ticker": str, "loss_pct": float, "recovery_needed_pct": float }` |
| **Note** | `recovery_needed_pct = (1 / (1 + return_pct/100) - 1) * 100` (e.g. -50% loss needs +100% to recover) |

### PERF_005 -- Period Return Context

| Field | Value |
|---|---|
| **Category** | performance |
| **Priority** | info |
| **Data needed** | Portfolio performance series, 1 month and 3 month lookback |
| **Condition** | Always generated if sufficient data (>= 30 days of history) |
| **Formula** | `return_1m = (current_value / value_30d_ago - 1) * 100` | `return_3m = (current_value / value_90d_ago - 1) * 100` |
| **Template** | `"Your portfolio has returned {return_1m:+.1f}% over the past month and {return_3m:+.1f}% over the past 3 months."` |
| **Metadata** | `{ "return_1m": float, "return_3m": float }` |

### PERF_006 -- Best and Worst Performers Summary

| Field | Value |
|---|---|
| **Category** | performance |
| **Priority** | info |
| **Data needed** | All holdings with unrealized gain/loss % |
| **Condition** | Portfolio has >= 3 holdings |
| **Template** | `"Best performer: {best_name} ({best_ticker}) at {best_pct:+.1f}%. Worst performer: {worst_name} ({worst_ticker}) at {worst_pct:+.1f}%. Spread: {spread:.0f} percentage points."` |
| **Metadata** | `{ "best_ticker": str, "best_pct": float, "worst_ticker": str, "worst_pct": float, "spread": float }` |

---

## 4. Income

### INC_001 -- Portfolio Dividend Yield

| Field | Value |
|---|---|
| **Category** | income |
| **Priority** | info if yield > 0, positive if yield > 3% |
| **Data needed** | DIVIDEND transactions from the last 12 months, current portfolio value |
| **Condition** | Portfolio has received dividends in the last 12 months |
| **Formula** | `trailing_12m_dividends = sum(tx.quantity * tx.price for tx in dividend_txs where tx.date >= today - 365)` | `yield_pct = trailing_12m_dividends / total_value * 100` |
| **Template** | `"Your trailing 12-month dividend yield is {yield_pct:.2f}% (EUR {dividends:.2f} received). {context}"` |
| **Note** | `context = "This is above the S&P 500 average yield of ~1.5%." if yield > 2 else "Consider adding dividend-paying stocks or ETFs if income is a priority."` |
| **Metadata** | `{ "yield_pct": float, "total_dividends_12m": float }` |

### INC_002 -- Dividend Concentration

| Field | Value |
|---|---|
| **Category** | income |
| **Priority** | warning |
| **Data needed** | DIVIDEND transactions grouped by instrument, last 12 months |
| **Condition** | A single instrument contributed > 50% of total dividends received in the last 12 months |
| **Formula** | `per_instrument_div = group_by(instrument).sum(amount)` | `max_pct = max(per_instrument_div.values()) / total_div * 100` |
| **Template** | `"{pct:.0f}% of your dividend income comes from {name} ({ticker}). If this company cuts its dividend, your income stream would be significantly impacted. Diversify your income sources."` |
| **Metadata** | `{ "ticker": str, "income_concentration_pct": float }` |

### INC_003 -- No Dividend Income

| Field | Value |
|---|---|
| **Category** | income |
| **Priority** | info |
| **Data needed** | DIVIDEND transactions from the last 12 months, holding count |
| **Condition** | Portfolio has >= 5 holdings but zero dividend transactions in 12 months |
| **Template** | `"Your portfolio has not generated any dividend income in the past 12 months. If passive income is a goal, consider allocating a portion to dividend-paying stocks or income-focused ETFs."` |
| **Metadata** | `{ "holding_count": int, "months_without_dividends": int }` |

---

## 5. Cost Awareness

### COST_001 -- Fee Drag

| Field | Value |
|---|---|
| **Category** | cost |
| **Priority** | warning if fee_ratio > 2%, info if > 1% |
| **Data needed** | All FEE transactions + fee fields on BUY/SELL transactions, total cost basis |
| **Condition** | Total fees paid / total capital deployed > threshold |
| **Formula** | `total_fees = sum(tx.fee for tx in all_txs) + sum(tx.quantity * tx.price for tx in fee_txs)` | `fee_ratio = total_fees / total_cost * 100` |
| **Template** | `"You've paid EUR {total_fees:.2f} in transaction fees ({fee_ratio:.2f}% of invested capital). {context}"` |
| **Note** | `context = "This is eating into your returns. Consider using a lower-cost broker or making fewer, larger trades." if fee_ratio > 2 else "Keep an eye on fees -- they compound against you over time."` |
| **Metadata** | `{ "total_fees": float, "fee_ratio_pct": float }` |

### COST_002 -- High-Fee Individual Transactions

| Field | Value |
|---|---|
| **Category** | cost |
| **Priority** | info |
| **Data needed** | BUY/SELL transactions with fee > 0 |
| **Condition** | Any transaction where fee / (quantity * price) > 3% |
| **Formula** | `fee_pct = tx.fee / (tx.quantity * tx.price) * 100` |
| **Template** | `"Transaction on {date}: {type} {ticker} had a {fee_pct:.1f}% fee ({fee_eur:.2f} EUR on a {value:.2f} EUR trade). Small trades with flat fees can have disproportionate costs."` |
| **Metadata** | `{ "ticker": str, "date": str, "fee_pct": float, "fee_eur": float }` |
| **Note** | Show at most the 3 worst offenders. |

### COST_003 -- Tax-Loss Harvesting Opportunity

| Field | Value |
|---|---|
| **Category** | cost |
| **Priority** | info |
| **Data needed** | Holdings with unrealized losses, total realized gains from SELL transactions in current calendar year |
| **Condition** | Holding has unrealized loss > 5% AND there are realized gains in the current year |
| **Formula** | `unrealized_loss = (current_price - avg_buy_price) * quantity` | `realized_gains = sum(gain for sell_txs in current_year where gain > 0)` |
| **Template** | `"{name} ({ticker}) has an unrealized loss of EUR {loss:.2f} ({loss_pct:.1f}%). You have EUR {realized_gains:.2f} in realized gains this year. Selling this position could offset taxable gains (check local tax rules for wash-sale restrictions)."` |
| **Metadata** | `{ "ticker": str, "unrealized_loss": float, "realized_gains_ytd": float }` |
| **Note** | This is informational only. Tax rules vary by jurisdiction. Always include the disclaimer about checking local regulations. |

---

## 6. Technical Signals

### TECH_001 -- RSI Overbought

| Field | Value |
|---|---|
| **Category** | technical |
| **Priority** | info |
| **Data needed** | OHLCV data for each holding (3-month daily), RSI(14) calculation |
| **Condition** | RSI(14) > 70 for any holding |
| **Formula** | `rsi = calculate_rsi(closes, 14)` | Check latest RSI value |
| **Template** | `"{name} ({ticker}) has an RSI of {rsi:.0f}, indicating overbought conditions. This doesn't guarantee a decline, but historically suggests the stock may be due for a pullback or consolidation."` |
| **Metadata** | `{ "ticker": str, "rsi": float }` |

### TECH_002 -- RSI Oversold

| Field | Value |
|---|---|
| **Category** | technical |
| **Priority** | info |
| **Data needed** | OHLCV data for each holding (3-month daily), RSI(14) calculation |
| **Condition** | RSI(14) < 30 for any holding |
| **Template** | `"{name} ({ticker}) has an RSI of {rsi:.0f}, indicating oversold conditions. This may represent a buying opportunity if the fundamentals are sound, but can also signal continued weakness."` |
| **Metadata** | `{ "ticker": str, "rsi": float }` |

### TECH_003 -- Golden Cross (Bullish SMA Crossover)

| Field | Value |
|---|---|
| **Category** | technical |
| **Priority** | positive |
| **Data needed** | SMA(20) and SMA(50) for each holding, at least 2 recent data points for each |
| **Condition** | SMA(20) crossed above SMA(50) within the last 5 trading days |
| **Formula** | `prev_diff = sma20[-5] - sma50[-5]` | `curr_diff = sma20[-1] - sma50[-1]` | Trigger if `prev_diff <= 0 and curr_diff > 0` |
| **Template** | `"{name} ({ticker}) just formed a golden cross (20-day SMA crossed above 50-day SMA). This bullish technical signal often precedes sustained upward momentum."` |
| **Metadata** | `{ "ticker": str, "sma20": float, "sma50": float }` |

### TECH_004 -- Death Cross (Bearish SMA Crossover)

| Field | Value |
|---|---|
| **Category** | technical |
| **Priority** | warning |
| **Data needed** | SMA(20) and SMA(50) for each holding, at least 2 recent data points for each |
| **Condition** | SMA(20) crossed below SMA(50) within the last 5 trading days |
| **Formula** | `prev_diff = sma20[-5] - sma50[-5]` | `curr_diff = sma20[-1] - sma50[-1]` | Trigger if `prev_diff >= 0 and curr_diff < 0` |
| **Template** | `"{name} ({ticker}) just formed a death cross (20-day SMA crossed below 50-day SMA). This bearish signal suggests potential downward pressure. Review your thesis for this position."` |
| **Metadata** | `{ "ticker": str, "sma20": float, "sma50": float }` |

### TECH_005 -- Price Below SMA50 (Downtrend)

| Field | Value |
|---|---|
| **Category** | technical |
| **Priority** | info |
| **Data needed** | Current price, SMA(50) for each holding |
| **Condition** | Current price is more than 10% below SMA(50) |
| **Formula** | `pct_below = (current_price - sma50) / sma50 * 100` | Trigger if `pct_below < -10` |
| **Template** | `"{name} ({ticker}) is trading {pct_below:.1f}% below its 50-day moving average, suggesting a downtrend. Monitor for stabilization before adding to the position."` |
| **Metadata** | `{ "ticker": str, "current_price": float, "sma50": float, "pct_below_sma": float }` |

### TECH_006 -- Portfolio-Wide Momentum Score

| Field | Value |
|---|---|
| **Category** | technical |
| **Priority** | info |
| **Data needed** | RSI(14) for all holdings with available data |
| **Condition** | Average portfolio RSI computed as a weighted average (by position size) |
| **Formula** | `portfolio_rsi = sum(rsi_i * weight_i) / sum(weight_i)` |
| **Template (RSI > 65)** | `"Your portfolio's weighted average RSI is {rsi:.0f}, suggesting overall bullish momentum. Be cautious about adding to positions that are already extended."` |
| **Template (RSI < 35)** | `"Your portfolio's weighted average RSI is {rsi:.0f}, suggesting overall bearish conditions. This may present opportunities if you have conviction in your holdings."` |
| **Template (35-65)** | `"Your portfolio's weighted average RSI is {rsi:.0f}, suggesting neutral momentum."` |
| **Metadata** | `{ "portfolio_rsi": float }` |

---

## 7. Behavioral Finance

### BEHAV_001 -- Disposition Effect: Holding Losers Too Long

| Field | Value |
|---|---|
| **Category** | behavioral |
| **Priority** | warning |
| **Data needed** | Holdings with unrealized loss > 20%, plus the date of last BUY transaction for those holdings |
| **Condition** | Holding is down > 20% from cost basis AND the last transaction for that instrument was a BUY more than 6 months ago (no recent averaging down or selling) |
| **Formula** | `loss_pct = (current_price - avg_buy_price) / avg_buy_price * 100` | `last_tx_date = max(tx.date for tx in instrument_txs)` | `months_held = (today - last_tx_date).days / 30` |
| **Template** | `"You've held {name} ({ticker}) at a {loss_pct:.0f}% loss for over {months:.0f} months without action. Investors often hold losers hoping to break even (the 'disposition effect'). Objectively reassess: would you buy this stock today?"` |
| **Metadata** | `{ "ticker": str, "loss_pct": float, "months_held": float }` |

### BEHAV_002 -- Disposition Effect: Selling Winners Too Early

| Field | Value |
|---|---|
| **Category** | behavioral |
| **Priority** | info |
| **Data needed** | SELL transactions in the last 6 months where the sale was profitable, paired with the remaining portfolio's performance |
| **Condition** | User sold a winning position and the stock has continued to rise > 15% since the sale |
| **Formula** | For each SELL with gain: `post_sale_return = (current_price - sale_price) / sale_price * 100`. Trigger if `post_sale_return > 15%` |
| **Template** | `"You sold {name} ({ticker}) on {date} at a profit, but the stock has risen {post_sale_pct:.0f}% further since then. While taking profits is prudent, consider whether you're cutting winners short. Letting winners run is a key factor in long-term returns."` |
| **Metadata** | `{ "ticker": str, "sale_date": str, "sale_price": float, "current_price": float, "post_sale_pct": float }` |
| **Note** | Only check the last 6 months of sales. Show at most 2 instances. |

### BEHAV_003 -- Overtrading Warning

| Field | Value |
|---|---|
| **Category** | behavioral |
| **Priority** | warning |
| **Data needed** | BUY and SELL transactions in the last 3 months |
| **Condition** | More than 20 transactions in 3 months, OR a single instrument was bought and sold more than twice in 3 months |
| **Formula** | `tx_count_3m = count(txs where tx.date >= today - 90 and tx.type in [BUY, SELL])` |
| **Template (high volume)** | `"You've made {count} trades in the last 3 months. Frequent trading increases costs and typically underperforms a buy-and-hold strategy. Studies show that the most active traders earn the lowest returns."` |
| **Template (round-tripping)** | `"{ticker} has been bought and sold {round_trips} times in 3 months. Frequent round-tripping suggests short-term trading behavior, which rarely outperforms after fees and taxes."` |
| **Metadata** | `{ "tx_count_3m": int, "round_trip_tickers": list[str] }` |

### BEHAV_004 -- Recency Bias Warning

| Field | Value |
|---|---|
| **Category** | behavioral |
| **Priority** | info |
| **Data needed** | BUY transactions in the last 30 days, each holding's 1-month return prior to purchase |
| **Condition** | >= 2 recent BUY transactions where the instrument had a > 15% gain in the month before the purchase date |
| **Formula** | For each recent BUY: `pre_buy_return = (price_at_buy / price_30d_before_buy - 1) * 100`. Trigger if `pre_buy_return > 15` for >= 2 buys |
| **Template** | `"Several of your recent purchases ({tickers}) had strong runs before you bought them. Chasing recent performance (recency bias) often leads to buying near short-term tops. Ensure your purchases are based on fundamentals, not recent price action."` |
| **Metadata** | `{ "tickers": list[str], "pre_buy_returns": list[float] }` |

### BEHAV_005 -- Rebalancing Nudge

| Field | Value |
|---|---|
| **Category** | behavioral |
| **Priority** | info |
| **Data needed** | Holdings with current weight vs. weight at time of initial purchase (or a target weight if configured), and date of last portfolio-level trade |
| **Condition** | Any holding's weight has drifted more than 10 percentage points from equal weight (as a heuristic) AND no BUY or SELL transactions in the last 3 months |
| **Formula** | `equal_weight = 100 / holding_count` | `max_drift = max(abs(weight_i - equal_weight) for all holdings)` |
| **Template** | `"Your portfolio allocation has drifted significantly from equal weight (max drift: {drift:.0f}pp). You haven't traded in {months} months. Consider rebalancing to bring positions back to your target allocation."` |
| **Metadata** | `{ "max_drift_pp": float, "months_since_last_trade": int }` |
| **Note** | Equal weight is a heuristic. If target weights are not configured, use equal weight as the reference. |

---

## 8. Portfolio Health

### HEALTH_001 -- Negligible Positions

| Field | Value |
|---|---|
| **Category** | health |
| **Priority** | info |
| **Data needed** | Holdings with current market values |
| **Condition** | Any holding represents < 1% of total portfolio value |
| **Formula** | `weight_pct = market_value / total_value * 100` |
| **Template** | `"{name} ({ticker}) represents only {weight_pct:.1f}% of your portfolio (EUR {value:.2f}). Positions this small have negligible impact on overall returns. Consider either building the position to a meaningful size or closing it to simplify your portfolio."` |
| **Metadata** | `{ "ticker": str, "weight_pct": float, "market_value": float }` |
| **Note** | Group all negligible positions into a single advice item if there are more than 3. |

### HEALTH_002 -- Stale Positions (No Activity)

| Field | Value |
|---|---|
| **Category** | health |
| **Priority** | info |
| **Data needed** | Holdings cross-referenced with transactions; find holdings whose most recent transaction is > 12 months old |
| **Condition** | Last transaction for a holding was more than 12 months ago |
| **Formula** | `last_tx_date = max(tx.date for tx in txs where tx.instrument == holding.instrument)` | `months_since = (today - last_tx_date).days / 30` |
| **Template** | `"{name} ({ticker}) has had no activity for {months:.0f} months. While buy-and-hold is valid, ensure you're still periodically reviewing positions for fundamental changes."` |
| **Metadata** | `{ "ticker": str, "months_since_last_tx": float, "last_tx_date": str }` |

### HEALTH_003 -- Large Unrealized-Gain Position (Rebalance Consideration)

| Field | Value |
|---|---|
| **Category** | health |
| **Priority** | info |
| **Data needed** | Holdings where unrealized gain > 50% AND weight > 15% |
| **Condition** | Holding has grown to a large weight through appreciation |
| **Template** | `"{name} ({ticker}) has gained {gain_pct:.0f}% and now represents {weight_pct:.1f}% of your portfolio. Consider taking partial profits to manage risk, even if you remain bullish on the stock."` |
| **Metadata** | `{ "ticker": str, "gain_pct": float, "weight_pct": float }` |

### HEALTH_004 -- Portfolio Age Context

| Field | Value |
|---|---|
| **Category** | health |
| **Priority** | info |
| **Data needed** | Date of first transaction |
| **Condition** | First transaction is less than 3 months ago |
| **Template** | `"Your portfolio is only {months:.0f} months old. Give your investments time to compound -- most investment strategies need at least 1-3 years to show their potential. Avoid making drastic changes based on short-term results."` |
| **Metadata** | `{ "portfolio_age_months": float, "first_transaction_date": str }` |

### HEALTH_005 -- Unpriced Instruments

| Field | Value |
|---|---|
| **Category** | health |
| **Priority** | warning |
| **Data needed** | Holdings where `get_current_price()` fails or instrument has no ticker |
| **Condition** | One or more holdings could not be priced |
| **Template** | `"{count} holding{s} ({tickers}) could not be priced. Portfolio valuations and analytics may be inaccurate. Check that ticker symbols are correctly assigned."` |
| **Metadata** | `{ "count": int, "tickers": list[str] }` |

---

## Evaluation Order and Limits

1. **Compute shared data once**: portfolio value, holding weights, sector/country/currency/asset_type allocations, performance series, per-holding returns. Pass this computed context to all rules.

2. **Evaluate all rules** and collect triggered `AdviceItem`s.

3. **Deduplicate**: If a holding triggers both PERF_002 (underperformer) and PERF_004 (deep loser), only keep PERF_004 (the higher severity one). If a holding triggers both RISK_001 (concentration) and HEALTH_003 (large gain + weight), keep both as they serve different purposes.

4. **Sort** by priority: critical -> warning -> info -> positive.

5. **Limit** to at most 10 items for the API response. Ensure at least 1 positive item is included if any positive rules triggered (even if it means dropping a lower-priority info item).

6. **Cache** the result for 15 minutes per portfolio. Technical rules (TECH_*) and correlation (RISK_007) should be cached for 24 hours as they are expensive to compute.

---

## Performance Considerations

| Rule Group | API Calls Needed | Estimated Latency | Caching Strategy |
|---|---|---|---|
| RISK_001-002, DIV_*, HEALTH_001 | `get_current_price` per holding | ~1-2s for 20 holdings | 5-min price cache (existing) |
| RISK_003-004, PERF_005 | Portfolio perf series (already computed) | ~2-3s | 15-min cache |
| RISK_005-006 | None (derived from holdings) | < 100ms | With price cache |
| RISK_007 (correlation) | `get_historical_prices` per holding | ~5-10s for 20 holdings | 24-hour cache |
| TECH_001-006 | `get_ohlcv` per holding + indicator calc | ~5-10s for 20 holdings | 24-hour cache |
| BEHAV_002, BEHAV_004 | `get_current_price` for sold stocks + `get_historical_prices` for recent buys | ~2-5s | 24-hour cache |
| INC_*, COST_*, BEHAV_001/003/005, HEALTH_002-004 | DB queries only (transactions) | < 500ms | 15-min cache |

**Recommendation**: Split the advice endpoint into two tiers:
- **Fast tier** (served immediately): All rules except RISK_007, TECH_*, BEHAV_002, BEHAV_004
- **Slow tier** (computed async, served from cache): RISK_007, TECH_*, BEHAV_002, BEHAV_004

The API can return fast-tier results immediately and include a `has_pending_analysis: true` flag. The frontend polls or uses a websocket to fetch the complete set once the slow tier finishes.

---

## Legal Disclaimer

Every advice response must include the following footer:

> "These insights are generated automatically for educational purposes only and do not constitute financial advice. Past performance does not guarantee future results. Always consult a qualified financial advisor before making investment decisions."
