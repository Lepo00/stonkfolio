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


# ── Full Advice Page serializers ──────────────────────────


class SubScoreSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    weight = serializers.IntegerField()
    item_count = serializers.IntegerField()


class HealthScoreSerializer(serializers.Serializer):
    overall_score = serializers.IntegerField()
    summary = serializers.CharField()
    sub_scores = serializers.DictField(child=SubScoreSerializer())


class TopActionSerializer(serializers.Serializer):
    action = serializers.CharField()
    rationale = serializers.CharField()
    impact = serializers.CharField()
    urgency = serializers.CharField()
    related_rule_id = serializers.CharField()
    related_holdings = serializers.ListField(child=serializers.CharField(), required=False)


class SuggestedETFSerializer(serializers.Serializer):
    name = serializers.CharField()
    ticker = serializers.CharField()
    isin = serializers.CharField()
    provider = serializers.CharField()
    ter = serializers.CharField()
    index_tracked = serializers.CharField()
    why = serializers.CharField()


class RecommendationSerializer(serializers.Serializer):
    category = serializers.CharField()
    title = serializers.CharField()
    rationale = serializers.CharField()
    suggested_etfs = SuggestedETFSerializer(many=True)
    impact = serializers.CharField()
    confidence = serializers.CharField()
    priority = serializers.IntegerField()


class ScenarioAllocationSerializer(serializers.Serializer):
    """Wrapper for before/after in a scenario."""

    allocation = serializers.DictField(child=serializers.FloatField())
    metrics = serializers.DictField()


class ScenarioSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    before = serializers.SerializerMethodField()
    after = serializers.SerializerMethodField()

    def get_before(self, obj):
        return {
            "allocation": obj.before_allocation,
            "metrics": obj.metrics_before,
        }

    def get_after(self, obj):
        return {
            "allocation": obj.after_allocation,
            "metrics": obj.metrics_after,
        }


class FullAdviceResponseSerializer(serializers.Serializer):
    health_score = HealthScoreSerializer()
    top_actions = TopActionSerializer(many=True)
    recommendations = RecommendationSerializer(many=True)
    scenarios = ScenarioSerializer(many=True)
    advice_items = AdviceItemSerializer(many=True)
    has_pending_analysis = serializers.BooleanField()
    disclaimer = serializers.CharField()


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.CharField()
    content = serializers.CharField()


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)


class ChatResponseSerializer(serializers.Serializer):
    messages = ChatMessageSerializer(many=True)
    context_summary = serializers.CharField()
