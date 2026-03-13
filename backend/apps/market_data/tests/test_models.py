from decimal import Decimal

import pytest

from apps.instruments.models import Instrument
from apps.market_data.models import PriceCache


@pytest.mark.django_db
class TestPriceCache:
    def test_create_price_cache(self):
        inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            name="Test",
            currency="EUR",
            asset_type="ETF",
        )
        pc = PriceCache.objects.create(instrument=inst, price=Decimal("75.50"))
        assert pc.price == Decimal("75.50")
        assert pc.fetched_at is not None
