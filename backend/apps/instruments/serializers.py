from rest_framework import serializers

from .models import Instrument


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ["id", "isin", "ticker", "name", "currency", "sector", "country", "asset_type"]
