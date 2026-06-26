import email
import email.utils
import imaplib
import logging
from datetime import datetime

log = logging.getLogger(__name__)

_CIMB_SENDER = "octo-noreply@cimbniaga.co.id"
_SUBJECT_KEYWORD = "OCTO Transaction Information"


class GmailReader:
    """Reads CIMB OCTO transaction notification emails via Gmail IMAP."""

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, address: str, app_password: str):
        self.address = address
        self.app_password = app_password

    def fetch_cimb_emails(self) -> list[dict]:
        """
        Return all CIMB transaction emails from INBOX, sorted oldest-first.
        Each item: {'message_id': str, 'date': str, 'message': email.message.Message}
        """
        results: list[dict] = []

        with imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT) as mail:
            mail.login(self.address, self.app_password)
            mail.select("INBOX")

            status, data = mail.search(
                None,
                f'(FROM "{_CIMB_SENDER}" SUBJECT "{_SUBJECT_KEYWORD}")',
            )
            if status != "OK":
                log.error(f"IMAP search failed with status: {status}")
                return results

            msg_ids = data[0].split()
            log.info(f"Found {len(msg_ids)} matching CIMB email(s)")

            for msg_id in msg_ids:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data or msg_data[0] is None:
                    log.warning(f"Could not fetch message id={msg_id}")
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                results.append(
                    {
                        "message_id": msg_id.decode(),
                        "date": msg.get("Date", ""),
                        "message": msg,
                    }
                )

        # Process oldest-first so cashback accumulates in correct order
        results.sort(key=_sort_key)
        return results


def _sort_key(entry: dict) -> datetime:
    try:
        return email.utils.parsedate_to_datetime(entry["date"])
    except Exception:
        return datetime.min
