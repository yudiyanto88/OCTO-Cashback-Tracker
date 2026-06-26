"""
OCTO Card Cashback Tracker
Reads CIMB OCTO transaction emails from Gmail, calculates cashback,
and sends a Telegram notification for each new transaction.
"""

import logging
import os
import sys

from src.cashback_calculator import (
    PERIOD_CAP,
    calculate_cashback,
    classify_transaction,
    get_billing_period,
)
from src.email_parser import parse_cimb_email
from src.gmail_reader import GmailReader
from src.state_manager import StateManager
from src.telegram_notifier import send_telegram_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def main() -> int:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    state = StateManager("state.json")
    reader = GmailReader(gmail_address, gmail_app_password)

    emails = reader.fetch_cimb_emails()
    log.info(f"Total CIMB emails fetched: {len(emails)}")

    new_count = 0

    for email_data in emails:
        txn = parse_cimb_email(email_data)
        if txn is None:
            continue

        txn_id = txn["transaction_id"]

        if state.is_processed(txn_id):
            log.debug(f"Already processed, skipping: {txn_id}")
            continue

        category, _ = classify_transaction(txn["purchase_type"])
        if category == "ineligible":
            log.info(
                f"Ineligible purchase type '{txn['purchase_type']}' "
                f"for txn {txn_id} — marking processed, no notification"
            )
            state.add_transaction(
                txn_id,
                {
                    "id": txn_id,
                    "date": txn["datetime"].isoformat(),
                    "merchant": txn["merchant_name"],
                    "amount": txn["amount"],
                    "purchase_type": txn["purchase_type"],
                    "cashback": 0.0,
                    "period": "n/a",
                },
                "n/a",
                0.0,
            )
            continue

        _, _, period_name = get_billing_period(txn["datetime"])

        # Snapshot totals BEFORE this transaction so we can compute remaining cap
        period_data = state.get_period(period_name)
        pre_total = period_data["cashback_total"]

        raw_cashback = calculate_cashback(txn["amount"], txn["purchase_type"])
        remaining_cap = max(0.0, PERIOD_CAP - pre_total)
        actual_cashback = min(raw_cashback, remaining_cap)

        txn_record = {
            "id": txn_id,
            "date": txn["datetime"].isoformat(),
            "merchant": txn["merchant_name"],
            "amount": txn["amount"],
            "purchase_type": txn["purchase_type"],
            "cashback": actual_cashback,
            "period": period_name,
        }
        # state.add_transaction mutates period_data in-place
        state.add_transaction(txn_id, txn_record, period_name, actual_cashback)

        # Read updated totals (period_data is the same dict object)
        send_telegram_notification(
            bot_token=bot_token,
            chat_id=chat_id,
            merchant=txn["merchant_name"],
            amount=txn["amount"],
            cashback=actual_cashback,
            period_name=period_name,
            period_total=period_data["cashback_total"],
            txn_count=period_data["transaction_count"],
            total_amount=period_data["total_amount"],
        )

        log.info(
            f"New txn [{txn_id}]: {txn['merchant_name']} "
            f"Rp {txn['amount']:,.0f} → cashback Rp {actual_cashback:,.0f} "
            f"| {period_name} total: Rp {period_data['cashback_total']:,.0f}"
        )
        new_count += 1

    state.save()
    log.info(f"Finished. {new_count} new transaction(s) processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
