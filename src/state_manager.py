import json
import os
from datetime import datetime


class StateManager:
    """
    Persists processed transaction IDs and per-billing-period cashback totals
    in a JSON file that is committed to the repository.
    """

    def __init__(self, state_file: str = "state.json"):
        self.state_file = state_file
        self._state = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "processed_transaction_ids": [],
            "periods": {},
            "last_updated": None,
        }

    def save(self) -> None:
        self._state["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_processed(self, transaction_id: str) -> bool:
        return transaction_id in self._state["processed_transaction_ids"]

    def get_period(self, period_name: str) -> dict:
        """
        Return the mutable period dict for period_name, creating it if absent.
        Callers can read updated totals directly from the returned dict after
        calling add_transaction(), because it is the same object stored in state.
        """
        if period_name not in self._state["periods"]:
            self._state["periods"][period_name] = {
                "cashback_total": 0.0,
                "transaction_count": 0,
                "total_amount": 0.0,
                "transactions": [],
            }
        return self._state["periods"][period_name]

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        transaction_id: str,
        txn_record: dict,
        period_name: str,
        cashback: float,
    ) -> None:
        self._state["processed_transaction_ids"].append(transaction_id)
        period = self.get_period(period_name)
        period["cashback_total"] += cashback
        period["transaction_count"] += 1
        period["total_amount"] += txn_record.get("amount", 0.0)
        period["transactions"].append(txn_record)
