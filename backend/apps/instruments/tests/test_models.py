import pytest

from apps.instruments.models import Instrument


@pytest.mark.django_db
class TestInstrument:
    def test_create_instrument(self):
        inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="iShares Core MSCI World",
            currency="EUR",
            sector="Diversified",
            country="IE",
            asset_type="ETF",
        )
        assert inst.isin == "IE00B4L5Y983"
        assert str(inst) == "IWDA.AS - iShares Core MSCI World"

    def test_isin_unique(self):
        Instrument.objects.create(isin="IE00B4L5Y983", name="Test", currency="EUR", asset_type="ETF")
        with pytest.raises(Exception):
            Instrument.objects.create(isin="IE00B4L5Y983", name="Dupe", currency="EUR", asset_type="ETF")
