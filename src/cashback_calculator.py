from datetime import datetime

CASHBACK_RATE = 0.10
PERIOD_CAP = 100_000
QRIS_CAP = 10_000
ONLINE_CAP = 20_000

# Purchase types that map to QRIS (offline QR scan) — cap Rp 10.000/txn.
# Update this set if CIMB uses additional labels for QRIS in the future.
QRIS_PURCHASE_TYPES = {
    "purchase with qr",
}

# Purchase types that are NOT eligible for cashback.
# Extend as new ineligible types are encountered in emails.
INELIGIBLE_PURCHASE_TYPES = {
    "cash advance",
    "installment",
    "cicilan",
    "recurring",
    "gesek tunai",
}


def classify_transaction(purchase_type: str) -> tuple[str, int]:
    """
    Return (category, per_transaction_cap) for a purchase type string.
    category: 'qris' | 'online' | 'ineligible'
    """
    pt = purchase_type.lower().strip()

    if pt in QRIS_PURCHASE_TYPES:
        return "qris", QRIS_CAP

    for ineligible in INELIGIBLE_PURCHASE_TYPES:
        if ineligible in pt:
            return "ineligible", 0

    # Default: treat as online purchase (cap Rp 20.000)
    return "online", ONLINE_CAP


def calculate_cashback(amount: float, purchase_type: str) -> float:
    """
    Calculate per-transaction cashback before applying the period cap.
    Returns 0 for ineligible purchase types.
    """
    category, cap = classify_transaction(purchase_type)
    if category == "ineligible":
        return 0.0
    return min(amount * CASHBACK_RATE, cap)


def get_billing_period(txn_date: datetime) -> tuple[datetime, datetime, str]:
    """
    Return (period_start, period_end, period_name) for a transaction date.

    Rule: billing period = 17th of the previous month → 16th of the current month.
    The period is named for the month in which it ends (the 16th).

    Examples:
      2026-06-10 → 17 May – 16 Jun  → "Jun 2026"
      2026-06-25 → 17 Jun – 16 Jul  → "Jul 2026"
    """
    if txn_date.day <= 16:
        period_end = txn_date.replace(
            day=16, hour=23, minute=59, second=59, microsecond=0
        )
        if txn_date.month == 1:
            period_start = txn_date.replace(
                year=txn_date.year - 1, month=12, day=17,
                hour=0, minute=0, second=0, microsecond=0,
            )
        else:
            period_start = txn_date.replace(
                month=txn_date.month - 1, day=17,
                hour=0, minute=0, second=0, microsecond=0,
            )
        period_name = txn_date.strftime("%b %Y")
    else:
        period_start = txn_date.replace(
            day=17, hour=0, minute=0, second=0, microsecond=0
        )
        if txn_date.month == 12:
            period_end = txn_date.replace(
                year=txn_date.year + 1, month=1, day=16,
                hour=23, minute=59, second=59, microsecond=0,
            )
            period_name = f"Jan {txn_date.year + 1}"
        else:
            next_month = txn_date.month + 1
            period_end = txn_date.replace(
                month=next_month, day=16,
                hour=23, minute=59, second=59, microsecond=0,
            )
            period_name = datetime(txn_date.year, next_month, 1).strftime("%b %Y")

    return period_start, period_end, period_name
