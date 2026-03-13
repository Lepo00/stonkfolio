from .base import BrokerImporter, TransactionData


class BitpandaApiImporter(BrokerImporter):
    broker_name = "bitpanda"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def import_transactions(self, source=None) -> list[TransactionData]:
        # TODO: implement via Bitpanda API
        raise NotImplementedError("Bitpanda API sync coming soon")
