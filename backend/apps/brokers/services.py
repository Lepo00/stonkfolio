from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction as db_transaction

from apps.instruments.services import InstrumentResolver
from apps.portfolios.models import Holding, Portfolio, Transaction, TransactionType

from .importers.base import TransactionData


@dataclass
class ImportResult:
    imported: int
    skipped: int
    warnings: list[str]


class ImportService:
    def __init__(self, resolver=None):
        self.resolver = resolver or InstrumentResolver()

    @db_transaction.atomic
    def import_transactions(self, portfolio: Portfolio, data: list[TransactionData]) -> ImportResult:
        imported = 0
        skipped = 0
        warnings = []
        instruments_touched = set()

        for tx_data in data:
            if Transaction.objects.filter(portfolio=portfolio, broker_reference=tx_data.broker_reference).exists():
                skipped += 1
                continue

            instrument = self.resolver.get_or_create(
                isin=tx_data.isin,
                name=tx_data.product_name,
                currency=tx_data.currency,
            )

            if not instrument.ticker:
                warnings.append(f"Unresolved ticker for {tx_data.isin} ({tx_data.product_name})")

            Transaction.objects.create(
                portfolio=portfolio,
                instrument=instrument,
                type=tx_data.type.value,
                quantity=tx_data.quantity,
                price=tx_data.price,
                fee=tx_data.fee,
                date=tx_data.date,
                broker_source=tx_data.broker_source,
                broker_reference=tx_data.broker_reference,
            )
            instruments_touched.add(instrument.id)
            imported += 1

        for instrument_id in instruments_touched:
            self._recalculate_holding(portfolio, instrument_id)

        return ImportResult(imported=imported, skipped=skipped, warnings=warnings)

    def _recalculate_holding(self, portfolio: Portfolio, instrument_id: int):
        txs = Transaction.objects.filter(
            portfolio=portfolio,
            instrument_id=instrument_id,
        ).order_by("date")

        total_qty = Decimal("0")
        total_cost = Decimal("0")

        for tx in txs:
            if tx.type == TransactionType.BUY:
                total_qty += tx.quantity
                total_cost += tx.quantity * tx.price
            elif tx.type == TransactionType.SELL:
                if total_qty > 0:
                    avg_cost = total_cost / total_qty
                    total_cost -= tx.quantity * avg_cost
                total_qty -= tx.quantity

        if total_qty > 0:
            avg_price = total_cost / total_qty
            Holding.objects.update_or_create(
                portfolio=portfolio,
                instrument_id=instrument_id,
                defaults={"quantity": total_qty, "avg_buy_price": avg_price},
            )
        else:
            Holding.objects.filter(
                portfolio=portfolio,
                instrument_id=instrument_id,
            ).delete()
