import html
import logging

import requests

log = logging.getLogger(__name__)

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
PERIOD_CAP = 100_000


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_rp(amount: float) -> str:
    """Format as Indonesian Rupiah notation: Rp 25.000"""
    return f"Rp {int(round(amount)):,}".replace(",", ".")


def _fmt_rp_short(amount: float) -> str:
    """Compact form used in the estimasi line: 25rb, 1.5jt, etc."""
    if amount >= 1_000_000:
        v = amount / 1_000_000
        s = f"{v:.1f}".rstrip("0").rstrip(".")
        return f"{s}jt"
    if amount >= 1_000:
        v = amount / 1_000
        s = f"{v:.1f}".rstrip("0").rstrip(".")
        return f"{s}rb"
    return str(int(round(amount)))


def _esc(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return html.escape(str(text))


# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------

def build_message(
    merchant: str,
    amount: float,
    cashback: float,
    period_name: str,
    period_total: float,
    txn_count: int,
    total_amount: float,
) -> str:
    sisa = max(0.0, PERIOD_CAP - period_total)

    lines = [
        "🐙 <b>Transaksi Baru — OCTO Card</b>",
        "",
        f"Merchant : {_esc(merchant)}",
        f"Nominal  : {_fmt_rp(amount)}",
        f"Cashback : {_fmt_rp(cashback)}",
        "",
        f"Progress {_esc(period_name)}: {_fmt_rp(period_total)} / {_fmt_rp(PERIOD_CAP)}",
        f"Sisa              : {_fmt_rp(sisa)}",
    ]

    if period_total >= PERIOD_CAP:
        lines += [
            "",
            "🎉 Cashback bulan ini sudah maksimal. Pakai kartu lain untuk transaksi berikutnya.",
        ]
    elif sisa > 0 and period_total > 0 and total_amount > 0:
        effective_rate = period_total / total_amount
        spending_needed = sisa / effective_rate
        lines.append(f"Perlu belanja     : {_fmt_rp(spending_needed)} lagi untuk cap penuh")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sender
# ---------------------------------------------------------------------------

def send_telegram_notification(
    bot_token: str,
    chat_id: str,
    merchant: str,
    amount: float,
    cashback: float,
    period_name: str,
    period_total: float,
    txn_count: int,
    total_amount: float,
) -> bool:
    text = build_message(
        merchant=merchant,
        amount=amount,
        cashback=cashback,
        period_name=period_name,
        period_total=period_total,
        txn_count=txn_count,
        total_amount=total_amount,
    )

    url = _TELEGRAM_URL.format(token=bot_token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            log.error(f"Telegram error {resp.status_code}: {resp.text}")
            return False
        log.info(f"Telegram notification sent for {merchant}")
        return True
    except requests.RequestException as e:
        log.error(f"Telegram request failed: {e}")
        return False
