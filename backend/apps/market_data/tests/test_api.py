from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PriceResult
from apps.users.models import User


@pytest.mark.django_db
class TestPriceAPI:
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

    @patch("apps.market_data.views.MarketDataService")
    def test_get_price(self, MockService):
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("75.50"),
            currency="EUR",
        )
        resp = self.client.get("/api/prices/IWDA.AS/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["price"] == "75.50"
