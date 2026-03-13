from django.db import models


class PriceCache(models.Model):
    instrument = models.OneToOneField("instruments.Instrument", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    fetched_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.instrument} @ {self.price}"
