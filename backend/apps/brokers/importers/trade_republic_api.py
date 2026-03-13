from .base import BrokerImporter, TransactionData


class TradeRepublicApiImporter(BrokerImporter):
    broker_name = "trade_republic"

    def __init__(self, phone_number: str, pin: str):
        self.phone_number = phone_number
        self.pin = pin

    def import_transactions(self, source=None) -> list[TransactionData]:
        # TODO: implement via Trade Republic API
        raise NotImplementedError("Trade Republic API sync coming soon")
