from django.conf import settings
from django.db import models


class TransactionType(models.TextChoices):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    FX = "FX"


class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.user.username}/{self.name}"


class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="holdings")
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    avg_buy_price = models.DecimalField(max_digits=18, decimal_places=6)

    class Meta:
        unique_together = ["portfolio", "instrument"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="holding_quantity_non_negative",
            ),
        ]


class Transaction(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="transactions")
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    fee = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    date = models.DateField()
    broker_source = models.CharField(max_length=50)
    broker_reference = models.CharField(max_length=255)

    class Meta:
        unique_together = ["portfolio", "broker_reference"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["portfolio", "-date"]),
        ]
