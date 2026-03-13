from django.conf import settings
from django.db import models


class BrokerType(models.TextChoices):
    DEGIRO = "degiro"
    TRADE_REPUBLIC = "trade_republic"
    INTERACTIVE_BROKERS = "interactive_brokers"
    BITPANDA = "bitpanda"


class BrokerConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="broker_connections")
    broker_type = models.CharField(max_length=20, choices=BrokerType.choices)
    credentials_encrypted = models.TextField()
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "broker_type"]
