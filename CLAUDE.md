# OCTO Cashback Tracker

Tracks CIMB OCTO card cashback from Gmail transaction emails and sends Telegram notifications.

## How it works

1. GitHub Actions polls Gmail 4x/day via IMAP
2. Parses CIMB OCTO transaction emails
3. Calculates cashback per transaction
4. Sends Telegram notification for each new transaction
5. Commits updated `state.json` back to the repo

## Cashback rules

- Rate: 10% per transaction
- QRIS cap: Rp 10,000 per transaction
- Online cap: Rp 20,000 per transaction
- Period cap: Rp 100,000 per billing period
- Billing period: 17th of previous month → 16th of current month
- Admin fees and cash advances are ineligible

## Project structure

```
main.py                      # Entry point
src/
  gmail_reader.py            # IMAP Gmail reader (fetches CIMB emails)
  email_parser.py            # Parses HTML email → transaction dict
  cashback_calculator.py     # Cashback logic and billing period
  state_manager.py           # Reads/writes state.json
  telegram_notifier.py       # Builds message and sends to Telegram
state.json                   # Processed transaction IDs and period totals
.github/workflows/
  check-transactions.yml     # GitHub Actions schedule (4x/day)
```

## Email format

CIMB emails use alternating single-cell rows (not 2-column table):
```html
<td class="text-paramname">Transaction ID:</td>
<td class="text-paramvalue">001234567890</td>
```
Parser targets `text-paramname` / `text-paramvalue` CSS classes.

## Environment variables

Required (set as GitHub Secrets for Actions, or in `.env` for local):

| Variable | Description |
|---|---|
| `GMAIL_ADDRESS` | Gmail address that receives CIMB emails |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not account password) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat/user ID |

## Running locally

```bash
pip install -r requirements.txt
python main.py
```

## Adding manual transactions (no email)

If a transaction has no email (e.g., found via in-app screenshot), inject it directly into `state.json` matching the existing schema, then push to GitHub.

## state.json schema

```json
{
  "processed_transaction_ids": ["001234567890"],
  "periods": {
    "Jul 2026": {
      "cashback_total": 14100.0,
      "transaction_count": 5,
      "total_amount": 141000.0,
      "transactions": [...]
    }
  },
  "last_updated": "2026-06-26T17:00:00"
}
```
