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


class AdviceItemSerializer(serializers.Serializer):
    rule_id = serializers.CharField()
    category = serializers.CharField()
    priority = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    holdings = serializers.ListField(child=serializers.CharField(), required=False)
    metadata = serializers.DictField(required=False)


class AdviceResponseSerializer(serializers.Serializer):
    items = AdviceItemSerializer(many=True)
    has_pending_analysis = serializers.BooleanField()
    disclaimer = serializers.CharField()
