from .base import BrokerImporter, TransactionData


class DegiroApiImporter(BrokerImporter):
    broker_name = "degiro"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def import_transactions(self, source=None) -> list[TransactionData]:
        # TODO: implement via degiro-connector
        raise NotImplementedError("DeGiro API sync coming soon")
