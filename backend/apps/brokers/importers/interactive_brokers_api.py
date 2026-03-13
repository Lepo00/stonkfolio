from .base import BrokerImporter, TransactionData


class InteractiveBrokersApiImporter(BrokerImporter):
    broker_name = "interactive_brokers"

    def __init__(self, token: str):
        self.token = token

    def import_transactions(self, source=None) -> list[TransactionData]:
        # TODO: implement via IBKR Client Portal API or TWS API
        raise NotImplementedError("Interactive Brokers API sync coming soon")
