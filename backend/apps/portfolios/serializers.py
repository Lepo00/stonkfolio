from rest_framework import serializers

from apps.instruments.serializers import InstrumentSerializer

from .models import Holding, Portfolio, Transaction


class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class HoldingSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Holding
        fields = ["id", "instrument", "quantity", "avg_buy_price"]


class TransactionSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "instrument",
            "type",
            "quantity",
            "price",
            "fee",
            "date",
            "broker_source",
            "broker_reference",
        ]
        read_only_fields = ["id", "broker_source", "broker_reference"]
