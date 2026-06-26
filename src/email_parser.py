"""
Parse CIMB OCTO transaction notification emails.

Email format (HTML table, key-value rows):
  Date/Time       : 25Jun26 19:45
  Transaction ID  : 001251210581
  Purchase Type   : Purchase with QR
  Merchant Name   : W.M ROJO LELE PKC
  Fee             : IDR 0.00
  Total Payment   : IDR 25,000.00
  Source of Fund Account : 9441-XXXX-XXXX-1234
  Poin Xtra used  : 0
"""

import email.utils
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# CIMB date format examples: '25Jun26 19:45', '25Jun2026 19:45'
_DATE_FMTS = [
    "%d%b%y %H:%M",    # 25Jun26 19:45
    "%d%b%Y %H:%M",    # 25Jun2026 19:45
    "%d %b %Y %H:%M",  # 25 Jun 2026 19:45
    "%d/%m/%Y %H:%M",  # 25/06/2026 19:45
    "%d-%m-%Y %H:%M",  # 25-06-2026 19:45
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_body(msg) -> tuple[str, str]:
    """Extract (html_body, text_body) from an email.message.Message."""
    html_body = ""
    text_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            charset = part.get_content_charset() or "utf-8"
            try:
                raw = part.get_payload(decode=True)
                if raw is None:
                    continue
                decoded = raw.decode(charset, errors="replace")
            except Exception:
                continue
            if ct == "text/html" and not html_body:
                html_body = decoded
            elif ct == "text/plain" and not text_body:
                text_body = decoded
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            raw = msg.get_payload(decode=True)
            decoded = raw.decode(charset, errors="replace") if raw else ""
        except Exception:
            decoded = ""
        if msg.get_content_type() == "text/html":
            html_body = decoded
        else:
            text_body = decoded

    return html_body, text_body


def _fields_from_html(html: str) -> dict[str, str]:
    """
    Extract key-value fields from the CIMB HTML email body.
    Primary strategy: 2-cell <tr> rows (label | value).
    Fallback: colon-separated lines in the extracted text.
    """
    soup = BeautifulSoup(html, "html.parser")
    fields: dict[str, str] = {}

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = cells[0].get_text(separator=" ", strip=True).rstrip(":").strip()
            value = cells[1].get_text(separator=" ", strip=True)
            if key and value:
                fields[key] = value

    if fields:
        return fields

    # Fallback: parse text content of the whole email
    return _fields_from_text(soup.get_text(separator="\n"))


def _fields_from_text(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key and value and len(key) < 60:
            fields[key] = value
    return fields


def _parse_amount(s: str) -> float:
    """Parse 'IDR 25,000.00' or '25.000,00' → float."""
    # Remove currency symbols and letters
    s = re.sub(r"[A-Za-z\s]", "", s)
    # If the string uses Indonesian format (dot as thousands, comma as decimal)
    # e.g. '25.000,00' → switch separators
    if re.search(r"\d\.\d{3},\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        # Standard format: remove commas (thousands separator)
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_datetime(s: str) -> datetime | None:
    s = s.strip()
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_cimb_email(email_data: dict) -> dict | None:
    """
    Parse a CIMB OCTO transaction notification email dict (from GmailReader).

    Returns a dict with keys:
      transaction_id, datetime, purchase_type, merchant_name, amount
    or None if parsing fails.
    """
    msg = email_data["message"]
    html_body, text_body = _get_body(msg)

    fields: dict[str, str] = {}
    if html_body:
        fields = _fields_from_html(html_body)
    if not fields and text_body:
        fields = _fields_from_text(text_body)

    if not fields:
        log.warning(f"No fields extracted from email id={email_data['message_id']}")
        return None

    # Normalise keys for case-insensitive lookup
    fl = {k.lower(): v for k, v in fields.items()}

    def get(*keys: str) -> str:
        for k in keys:
            v = fl.get(k.lower())
            if v:
                return v.strip()
        return ""

    txn_id = get("transaction id", "transaction_id", "transaction no", "no transaksi", "id")
    date_str = get("date/time", "date time", "datetime", "date", "tanggal", "waktu")
    purchase_type = get("purchase type", "type", "tipe", "tipe transaksi", "jenis transaksi")
    merchant = get("merchant name", "merchant", "nama merchant", "nama toko")
    total_str = get("total payment", "total", "amount", "jumlah", "nominal")

    if not txn_id:
        log.warning(f"No transaction ID in email id={email_data['message_id']}")
        return None

    txn_dt = _parse_datetime(date_str) if date_str else None
    if txn_dt is None:
        # Fall back to the email's Date header
        try:
            txn_dt = email.utils.parsedate_to_datetime(email_data.get("date", ""))
        except Exception:
            txn_dt = datetime.now()

    amount = _parse_amount(total_str)
    if amount <= 0:
        log.warning(
            f"Zero or unparseable amount '{total_str}' in email id={email_data['message_id']}"
        )
        return None

    return {
        "transaction_id": txn_id,
        "datetime": txn_dt,
        "purchase_type": purchase_type or "unknown",
        "merchant_name": merchant or "Unknown Merchant",
        "amount": amount,
    }
