from rest_framework import serializers

from .models import BrokerConnection


class BrokerConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerConnection
        fields = ["id", "broker_type", "last_sync", "created_at"]
        read_only_fields = ["id", "last_sync", "created_at"]
