from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PricePoint, PriceResult
from apps.portfolios.models import Holding, Portfolio, Transaction, TransactionType
from apps.users.models import User


@pytest.mark.django_db
class TestPortfolioAnalytics:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="MSCI World",
            currency="EUR",
            asset_type="ETF",
            sector="Diversified",
            country="Ireland",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("75.50"),
        )

    @patch("apps.portfolios.views.MarketDataService")
    def test_summary(self, MockService):
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("80.00"),
            currency="EUR",
        )
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/summary/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_value"] == "800.00"
        assert resp.data["total_gain_loss"] == "45.00"

    @patch("apps.portfolios.views.MarketDataService")
    def test_performance(self, MockService):
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="degiro",
            broker_reference="ref1",
        )
        MockService.return_value.get_historical_prices.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("75.50")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("76.00")),
        ]
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/performance/?period=1W")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["series"]) > 0

    def test_allocation_by_sector(self):
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/allocation/?group_by=sector")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) > 0
        assert resp.data[0]["group"] == "Diversified"

    def test_allocation_invalid_group_by(self):
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/allocation/?group_by=password")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
