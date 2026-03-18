"""Tests for the advice engine fast rules, dedup, and sorting.

Pure dataclass tests — no database or Django setup required.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from apps.portfolios.advice.dedup import PRIORITY_ORDER, deduplicate
from apps.portfolios.advice.engine import AdviceEngine
from apps.portfolios.advice.models import AdviceContext, AdviceItem, HoldingData
from apps.portfolios.advice.rules_fast import FastRules

# ── Helpers ──────────────────────────────────────────────────


def _make_holding(**overrides) -> HoldingData:
    defaults = {
        "ticker": "AAPL",
        "name": "Apple",
        "isin": "US0378331005",
        "instrument_id": 1,
        "quantity": Decimal("10"),
        "avg_buy_price": Decimal("150"),
        "current_price": Decimal("160"),
        "market_value": Decimal("1600"),
        "cost_basis": Decimal("1500"),
        "weight_pct": 16.0,
        "return_pct": 6.67,
        "sector": "Technology",
        "country": "US",
        "asset_type": "STOCK",
        "currency": "USD",
    }
    defaults.update(overrides)
    return HoldingData(**defaults)


def _make_context(**overrides) -> AdviceContext:
    defaults = {
        "portfolio_id": 1,
        "holding_count": 5,
        "holdings": [],
        "unpriced_holdings": [],
        "total_value": Decimal("10000"),
        "total_cost": Decimal("9000"),
        "overall_return_pct": 11.1,
        "sector_weights": {},
        "country_weights": {},
        "currency_weights": {},
        "asset_type_weights": {},
        "all_transactions": [],
        "dividend_txs_12m": [],
        "fee_total": Decimal("0"),
        "first_transaction_date": date(2025, 1, 1),
        "last_trade_date": date(2026, 3, 1),
        "perf_series": None,
    }
    defaults.update(overrides)
    return AdviceContext(**defaults)


def _find_items(items: list[AdviceItem], rule_id: str) -> list[AdviceItem]:
    return [i for i in items if i.rule_id == rule_id]


# ── RISK_001: Single-Holding Concentration ───────────────────


class TestRisk001:
    def test_critical_at_40_pct(self):
        h = _make_holding(ticker="TSLA", name="Tesla", weight_pct=45.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_risk_001()
        assert len(items) == 1
        assert items[0].priority == "critical"
        assert items[0].rule_id == "RISK_001"
        assert items[0].metadata["threshold"] == 40

    def test_warning_at_25_pct(self):
        h = _make_holding(ticker="TSLA", name="Tesla", weight_pct=30.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_risk_001()
        assert len(items) == 1
        assert items[0].priority == "warning"
        assert items[0].metadata["threshold"] == 25

    def test_no_trigger_below_25(self):
        h = _make_holding(ticker="TSLA", name="Tesla", weight_pct=20.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_risk_001()
        assert len(items) == 0

    def test_boundary_exactly_40(self):
        h = _make_holding(weight_pct=40.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_risk_001()
        assert len(items) == 1
        assert items[0].priority == "critical"

    def test_boundary_exactly_25(self):
        h = _make_holding(weight_pct=25.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_risk_001()
        assert len(items) == 1
        assert items[0].priority == "warning"

    def test_unpriced_holding_skipped(self):
        h = _make_holding(weight_pct=None)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_risk_001()
        assert len(items) == 0


# ── RISK_002: Top-3 Concentration ────────────────────────────


class TestRisk002:
    def test_triggers_above_70(self):
        holdings = [
            _make_holding(ticker="A", name="A", weight_pct=30.0, instrument_id=1),
            _make_holding(ticker="B", name="B", weight_pct=25.0, instrument_id=2),
            _make_holding(ticker="C", name="C", weight_pct=20.0, instrument_id=3),
            _make_holding(ticker="D", name="D", weight_pct=15.0, instrument_id=4),
            _make_holding(ticker="E", name="E", weight_pct=10.0, instrument_id=5),
        ]
        ctx = _make_context(holdings=holdings)
        items = FastRules(ctx).rule_risk_002()
        assert len(items) == 1
        assert items[0].rule_id == "RISK_002"
        assert items[0].metadata["top3_pct"] == 75.0

    def test_no_trigger_at_70(self):
        holdings = [
            _make_holding(ticker="A", name="A", weight_pct=25.0, instrument_id=1),
            _make_holding(ticker="B", name="B", weight_pct=23.0, instrument_id=2),
            _make_holding(ticker="C", name="C", weight_pct=22.0, instrument_id=3),
            _make_holding(ticker="D", name="D", weight_pct=15.0, instrument_id=4),
            _make_holding(ticker="E", name="E", weight_pct=15.0, instrument_id=5),
        ]
        ctx = _make_context(holdings=holdings)
        items = FastRules(ctx).rule_risk_002()
        assert len(items) == 0

    def test_fewer_than_4_holdings_skipped(self):
        holdings = [
            _make_holding(ticker="A", name="A", weight_pct=50.0, instrument_id=1),
            _make_holding(ticker="B", name="B", weight_pct=30.0, instrument_id=2),
            _make_holding(ticker="C", name="C", weight_pct=20.0, instrument_id=3),
        ]
        ctx = _make_context(holdings=holdings)
        items = FastRules(ctx).rule_risk_002()
        assert len(items) == 0


# ── RISK_005: Currency Exposure ──────────────────────────────


class TestRisk005:
    def test_triggers_above_40_non_eur(self):
        ctx = _make_context(currency_weights={"USD": 55.0, "EUR": 45.0})
        items = FastRules(ctx).rule_risk_005()
        assert len(items) == 1
        assert items[0].metadata["currency"] == "USD"

    def test_eur_exempt(self):
        ctx = _make_context(currency_weights={"EUR": 100.0})
        items = FastRules(ctx).rule_risk_005()
        assert len(items) == 0

    def test_no_trigger_at_40(self):
        ctx = _make_context(currency_weights={"USD": 40.0, "EUR": 60.0})
        items = FastRules(ctx).rule_risk_005()
        assert len(items) == 0

    def test_multiple_currencies(self):
        ctx = _make_context(currency_weights={"USD": 45.0, "GBP": 42.0, "EUR": 13.0})
        items = FastRules(ctx).rule_risk_005()
        assert len(items) == 2
        currencies = {i.metadata["currency"] for i in items}
        assert currencies == {"USD", "GBP"}


# ── DIV_001: Insufficient Holdings ───────────────────────────


class TestDiv001:
    def test_warning_under_5(self):
        ctx = _make_context(holding_count=3)
        items = FastRules(ctx).rule_div_001()
        assert len(items) == 1
        assert items[0].priority == "warning"
        assert items[0].metadata["holding_count"] == 3

    def test_info_between_5_and_9(self):
        ctx = _make_context(holding_count=7)
        items = FastRules(ctx).rule_div_001()
        assert len(items) == 1
        assert items[0].priority == "info"

    def test_no_trigger_at_10(self):
        ctx = _make_context(holding_count=10)
        items = FastRules(ctx).rule_div_001()
        assert len(items) == 0

    def test_single_holding(self):
        ctx = _make_context(holding_count=1)
        items = FastRules(ctx).rule_div_001()
        assert len(items) == 1
        assert items[0].priority == "warning"
        # Check pluralization
        assert "1 position" in items[0].message


# ── DIV_002: Sector Concentration ────────────────────────────


class TestDiv002:
    def test_critical_above_60(self):
        ctx = _make_context(sector_weights={"Technology": 65.0, "Finance": 35.0})
        items = FastRules(ctx).rule_div_002()
        assert len(items) == 1
        assert items[0].priority == "critical"
        assert items[0].metadata["sector"] == "Technology"

    def test_warning_above_40(self):
        ctx = _make_context(sector_weights={"Technology": 45.0, "Finance": 35.0, "Energy": 20.0})
        items = FastRules(ctx).rule_div_002()
        assert len(items) == 1
        assert items[0].priority == "warning"

    def test_no_trigger_at_40(self):
        ctx = _make_context(sector_weights={"Technology": 40.0, "Finance": 35.0, "Energy": 25.0})
        items = FastRules(ctx).rule_div_002()
        assert len(items) == 0

    def test_unknown_sector_skipped(self):
        ctx = _make_context(sector_weights={"Unknown": 80.0, "Technology": 20.0})
        items = FastRules(ctx).rule_div_002()
        assert len(items) == 0


# ── PERF_001: Overall Portfolio Return ───────────────────────


class TestPerf001:
    def test_positive_return(self):
        ctx = _make_context(
            overall_return_pct=15.0,
            total_value=Decimal("11500"),
            total_cost=Decimal("10000"),
            holding_count=5,
        )
        items = FastRules(ctx).rule_perf_001()
        assert len(items) == 1
        assert items[0].priority == "positive"
        assert items[0].metadata["return_pct"] == 15.0

    def test_negative_return(self):
        ctx = _make_context(
            overall_return_pct=-5.0,
            total_value=Decimal("9500"),
            total_cost=Decimal("10000"),
            holding_count=5,
        )
        items = FastRules(ctx).rule_perf_001()
        assert len(items) == 1
        assert items[0].priority == "info"
        assert items[0].metadata["return_pct"] == -5.0

    def test_deep_negative_return_message(self):
        ctx = _make_context(
            overall_return_pct=-15.0,
            total_value=Decimal("8500"),
            total_cost=Decimal("10000"),
            holding_count=5,
        )
        items = FastRules(ctx).rule_perf_001()
        assert len(items) == 1
        assert "panic-selling" in items[0].message

    def test_empty_portfolio_no_trigger(self):
        ctx = _make_context(holding_count=0)
        items = FastRules(ctx).rule_perf_001()
        assert len(items) == 0


# ── PERF_002: Underperformers ────────────────────────────────


class TestPerf002:
    def test_warning_at_20_loss(self):
        h = _make_holding(
            ticker="BAD",
            name="Bad Corp",
            return_pct=-25.0,
            current_price=Decimal("75"),
            avg_buy_price=Decimal("100"),
            cost_basis=Decimal("1000"),
        )
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_002()
        assert len(items) == 1
        assert items[0].priority == "warning"
        assert items[0].metadata["loss_pct"] == 25.0

    def test_info_at_10_loss(self):
        h = _make_holding(
            ticker="MEH",
            name="Meh Corp",
            return_pct=-12.0,
            current_price=Decimal("88"),
            avg_buy_price=Decimal("100"),
            cost_basis=Decimal("1000"),
        )
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_002()
        assert len(items) == 1
        assert items[0].priority == "info"

    def test_no_trigger_under_10(self):
        h = _make_holding(return_pct=-5.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_002()
        assert len(items) == 0


# ── PERF_003: Strong Performers ──────────────────────────────


class TestPerf003:
    def test_triggers_above_25(self):
        h = _make_holding(
            ticker="WIN",
            name="Winner Inc",
            return_pct=30.0,
        )
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_003()
        assert len(items) == 1
        assert items[0].priority == "positive"
        assert items[0].metadata["gain_pct"] == 30.0

    def test_no_trigger_at_25(self):
        h = _make_holding(return_pct=25.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_003()
        assert len(items) == 0

    def test_no_trigger_for_negative(self):
        h = _make_holding(return_pct=-10.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_003()
        assert len(items) == 0


# ── PERF_004: Deep Losers ────────────────────────────────────


class TestPerf004:
    def test_triggers_below_minus_50(self):
        h = _make_holding(
            ticker="DEEP",
            name="Deep Loss Ltd",
            return_pct=-60.0,
            current_price=Decimal("40"),
            avg_buy_price=Decimal("100"),
            cost_basis=Decimal("1000"),
        )
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_004()
        assert len(items) == 1
        assert items[0].priority == "critical"
        assert items[0].rule_id == "PERF_004"
        # -60% loss => recovery needed = (1 / (1 + (-60)/100) - 1) * 100 = (1/0.4 - 1)*100 = 150%
        assert items[0].metadata["recovery_needed_pct"] == 150.0

    def test_recovery_needed_at_50_pct_loss(self):
        h = _make_holding(
            ticker="HALF",
            name="Half Corp",
            return_pct=-50.1,
            current_price=Decimal("49.9"),
            avg_buy_price=Decimal("100"),
        )
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_004()
        assert len(items) == 1
        # -50.1% => recovery = (1/(1-0.501) - 1)*100 = (1/0.499 - 1)*100 ≈ 100.4%
        assert items[0].metadata["recovery_needed_pct"] > 100.0

    def test_no_trigger_at_exactly_minus_50(self):
        h = _make_holding(return_pct=-50.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_004()
        assert len(items) == 0

    def test_no_trigger_for_moderate_loss(self):
        h = _make_holding(return_pct=-30.0)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_perf_004()
        assert len(items) == 0


# ── HEALTH_001: Negligible Positions ─────────────────────────


class TestHealth001:
    def test_individual_items_when_3_or_fewer(self):
        holdings = [
            _make_holding(ticker="T1", name="Tiny1", weight_pct=0.5, market_value=Decimal("50"), instrument_id=1),
            _make_holding(ticker="T2", name="Tiny2", weight_pct=0.3, market_value=Decimal("30"), instrument_id=2),
        ]
        ctx = _make_context(holdings=holdings)
        items = FastRules(ctx).rule_health_001()
        assert len(items) == 2
        for it in items:
            assert it.rule_id == "HEALTH_001"

    def test_grouped_when_more_than_3(self):
        holdings = [
            _make_holding(ticker=f"T{i}", name=f"Tiny{i}", weight_pct=0.2, instrument_id=i) for i in range(1, 6)
        ]
        ctx = _make_context(holdings=holdings)
        items = FastRules(ctx).rule_health_001()
        assert len(items) == 1
        assert items[0].metadata["count"] == 5
        assert len(items[0].holdings) == 5

    def test_no_trigger_above_1_pct(self):
        h = _make_holding(weight_pct=1.5)
        ctx = _make_context(holdings=[h])
        items = FastRules(ctx).rule_health_001()
        assert len(items) == 0

    def test_exactly_3_not_grouped(self):
        holdings = [
            _make_holding(ticker=f"T{i}", name=f"Tiny{i}", weight_pct=0.5, instrument_id=i) for i in range(1, 4)
        ]
        ctx = _make_context(holdings=holdings)
        items = FastRules(ctx).rule_health_001()
        assert len(items) == 3


# ── HEALTH_005: Unpriced Instruments ─────────────────────────


class TestHealth005:
    def test_triggers_with_unpriced(self):
        unpriced = [
            _make_holding(ticker="DERP", current_price=None, weight_pct=None, market_value=None),
        ]
        ctx = _make_context(unpriced_holdings=unpriced)
        items = FastRules(ctx).rule_health_005()
        assert len(items) == 1
        assert items[0].priority == "warning"
        assert "DERP" in items[0].holdings

    def test_no_trigger_when_all_priced(self):
        ctx = _make_context(unpriced_holdings=[])
        items = FastRules(ctx).rule_health_005()
        assert len(items) == 0

    def test_multiple_unpriced(self):
        unpriced = [
            _make_holding(ticker="X", instrument_id=1, current_price=None, weight_pct=None, market_value=None),
            _make_holding(ticker="Y", instrument_id=2, current_price=None, weight_pct=None, market_value=None),
        ]
        ctx = _make_context(unpriced_holdings=unpriced)
        items = FastRules(ctx).rule_health_005()
        assert len(items) == 1
        assert items[0].metadata["count"] == 2
        assert set(items[0].holdings) == {"X", "Y"}


# ── Dedup: PERF_002 dropped when PERF_004 fires for same ticker ──


class TestDedup:
    def test_perf_002_dropped_when_perf_004_fires_same_ticker(self):
        items = [
            AdviceItem(
                rule_id="PERF_002",
                category="performance",
                priority="warning",
                title="Underperformer",
                message="down",
                holdings=["DEEP"],
            ),
            AdviceItem(
                rule_id="PERF_004",
                category="performance",
                priority="critical",
                title="Deep Loss",
                message="way down",
                holdings=["DEEP"],
            ),
        ]
        result = deduplicate(items)
        rule_ids = [i.rule_id for i in result]
        assert "PERF_004" in rule_ids
        assert "PERF_002" not in rule_ids

    def test_perf_002_kept_when_different_tickers(self):
        items = [
            AdviceItem(
                rule_id="PERF_002",
                category="performance",
                priority="warning",
                title="Underperformer",
                message="down",
                holdings=["AAA"],
            ),
            AdviceItem(
                rule_id="PERF_004",
                category="performance",
                priority="critical",
                title="Deep Loss",
                message="way down",
                holdings=["BBB"],
            ),
        ]
        result = deduplicate(items)
        rule_ids = [i.rule_id for i in result]
        assert "PERF_002" in rule_ids
        assert "PERF_004" in rule_ids

    def test_no_dedup_without_superseding_rule(self):
        items = [
            AdviceItem(
                rule_id="PERF_002",
                category="performance",
                priority="warning",
                title="Underperformer",
                message="down",
                holdings=["AAA"],
            ),
        ]
        result = deduplicate(items)
        assert len(result) == 1

    def test_partial_overlap_keeps_perf_002_if_extra_tickers(self):
        """PERF_002 covers [DEEP, AAA] but PERF_004 only covers [DEEP].
        Since AAA is not covered by PERF_004, PERF_002 is kept."""
        items = [
            AdviceItem(
                rule_id="PERF_002",
                category="performance",
                priority="warning",
                title="Underperformer",
                message="down",
                holdings=["DEEP", "AAA"],
            ),
            AdviceItem(
                rule_id="PERF_004",
                category="performance",
                priority="critical",
                title="Deep Loss",
                message="way down",
                holdings=["DEEP"],
            ),
        ]
        result = deduplicate(items)
        rule_ids = [i.rule_id for i in result]
        assert "PERF_002" in rule_ids
        assert "PERF_004" in rule_ids


# ── Sort Order: critical > warning > info > positive ─────────


class TestSortOrder:
    def test_priority_ordering(self):
        items = [
            AdviceItem(rule_id="A", category="x", priority="positive", title="", message=""),
            AdviceItem(rule_id="B", category="x", priority="critical", title="", message=""),
            AdviceItem(rule_id="C", category="x", priority="info", title="", message=""),
            AdviceItem(rule_id="D", category="x", priority="warning", title="", message=""),
        ]
        items.sort(key=lambda it: PRIORITY_ORDER.get(it.priority, 99))
        priorities = [i.priority for i in items]
        assert priorities == ["critical", "warning", "info", "positive"]


# ── At Least 1 Positive Guaranteed in Top 10 ────────────────


class TestPositiveGuarantee:
    def test_positive_included_in_limited_results(self):
        """When there are >10 items and no positive in the top 9,
        the sort_and_limit method should pull one in."""
        items = []
        # 9 critical items
        for i in range(9):
            items.append(
                AdviceItem(
                    rule_id=f"CRIT_{i}",
                    category="risk",
                    priority="critical",
                    title=f"Critical {i}",
                    message="bad",
                )
            )
        # 3 warning items
        for i in range(3):
            items.append(
                AdviceItem(
                    rule_id=f"WARN_{i}",
                    category="risk",
                    priority="warning",
                    title=f"Warning {i}",
                    message="meh",
                )
            )
        # 1 positive item (would normally be cut off)
        items.append(
            AdviceItem(
                rule_id="POS_1",
                category="performance",
                priority="positive",
                title="Good stuff",
                message="nice",
            )
        )

        result = AdviceEngine._sort_and_limit(items)
        assert len(result) == 10
        positives = [i for i in result if i.priority == "positive"]
        assert len(positives) >= 1

    def test_positive_already_in_top_10(self):
        """If a positive is already in the first 9, no special handling needed."""
        items = []
        for i in range(8):
            items.append(
                AdviceItem(
                    rule_id=f"CRIT_{i}",
                    category="risk",
                    priority="critical",
                    title=f"Critical {i}",
                    message="bad",
                )
            )
        items.append(
            AdviceItem(
                rule_id="POS_0",
                category="performance",
                priority="positive",
                title="Good",
                message="nice",
            )
        )
        # Fill with more items
        for i in range(5):
            items.append(
                AdviceItem(
                    rule_id=f"WARN_{i}",
                    category="risk",
                    priority="warning",
                    title=f"Warning {i}",
                    message="meh",
                )
            )

        # Sort first (as engine does)
        items.sort(key=lambda it: PRIORITY_ORDER.get(it.priority, 99))
        result = AdviceEngine._sort_and_limit(items)
        assert len(result) == 10

    def test_no_positive_available(self):
        """If there are no positive items at all, result should just be top 10."""
        items = []
        for i in range(15):
            items.append(
                AdviceItem(
                    rule_id=f"CRIT_{i}",
                    category="risk",
                    priority="critical",
                    title=f"Critical {i}",
                    message="bad",
                )
            )
        result = AdviceEngine._sort_and_limit(items)
        assert len(result) == 10

    def test_fewer_than_10_items_returned_as_is(self):
        items = [
            AdviceItem(rule_id="A", category="x", priority="critical", title="", message=""),
            AdviceItem(rule_id="B", category="x", priority="positive", title="", message=""),
        ]
        result = AdviceEngine._sort_and_limit(items)
        assert len(result) == 2


# ── Integration: evaluate_all runs without error ─────────────


class TestEvaluateAll:
    def test_basic_evaluation(self):
        """evaluate_all should collect results from all rules without crashing."""
        h = _make_holding(weight_pct=50.0, return_pct=30.0)
        ctx = _make_context(
            holdings=[h],
            holding_count=1,
            sector_weights={"Technology": 100.0},
            currency_weights={"USD": 100.0},
        )
        items = FastRules(ctx).evaluate_all()
        # Should have at least RISK_001 (50% weight), PERF_003 (30% gain), DIV_001 (1 holding)
        rule_ids = {i.rule_id for i in items}
        assert "RISK_001" in rule_ids
        assert "PERF_003" in rule_ids
        assert "DIV_001" in rule_ids

    def test_empty_portfolio(self):
        """An empty portfolio should not crash."""
        ctx = _make_context(holding_count=0, holdings=[])
        items = FastRules(ctx).evaluate_all()
        # Should still get DIV_001 if holding_count < 5
        # Actually holding_count=0 < 5 => DIV_001 warning
        assert any(i.rule_id == "DIV_001" for i in items)
