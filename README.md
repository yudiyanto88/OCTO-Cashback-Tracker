# OCTO Card Cashback Tracker

Automation that reads CIMB Niaga OCTO Card transaction notification emails from Gmail, calculates cashback earned per billing period, and sends a Telegram notification for each new transaction.

## Cashback Rules (OCTO Card Mastercard)

| Purchase Type | Rate | Cap / txn | Cap / period |
|---|---|---|---|
| QRIS (`Purchase with QR`) | 10% | Rp 10.000 | Rp 100.000 |
| Online purchase | 10% | Rp 20.000 | Rp 100.000 |
| Hotel, Airlines, Tour & Travel, cicilan, Cash Advance, recurring, gesek tunai | — | ineligible | — |

**Billing period:** 17th of the previous month → 16th of the current month.  
Example: billing period Jul 2026 = 17 Jun → 16 Jul 2026.

## Telegram Notification Format

```
🧾 Transaksi Baru — OCTO Card

Merchant : W.M ROJO LELE PKC
Nominal  : Rp 25.000
Cashback : Rp 2.500

Progress Jul 2026: Rp 52.500 / Rp 100.000
Sisa              : Rp 47.500
Estimasi          : ~5 transaksi 25rb lagi untuk maksimal
```

When the Rp 100.000 cap is reached:
```
🎉 Cashback bulan ini sudah maksimal. Pakai kartu lain untuk transaksi berikutnya.
```

## Setup

### 1. Fork / clone this repository

### 2. Gmail — enable IMAP and create an App Password

1. Go to [Google Account → Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already enabled
3. Go to **App Passwords** (search "App Passwords" in the account search bar)
4. Create a new App Password: App = Mail, Device = Other → name it "OCTO Tracker"
5. Copy the 16-character password

### 3. Telegram — create a bot and get your Chat ID

1. Open [@BotFather](https://t.me/botfather) on Telegram and send `/newbot`
2. Follow the prompts; copy the **HTTP API token**
3. Send any message to your new bot, then open:  
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`  
   and copy the `"id"` value from `result[0].message.chat`

### 4. Add GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_ADDRESS` | your Gmail address |
| `GMAIL_APP_PASSWORD` | the 16-char App Password from step 2 |
| `TELEGRAM_BOT_TOKEN` | bot token from BotFather |
| `TELEGRAM_CHAT_ID` | your Telegram chat ID |

### 5. Enable GitHub Actions

Go to **Actions** tab in your repository and enable workflows if prompted.

The workflow runs automatically 4× per day (10:00, 16:00, 22:00, 04:00 WIB).  
You can also trigger it manually from the **Actions** tab → **Check OCTO Transactions** → **Run workflow**.

## State

Transaction state is stored in [`state.json`](state.json) and auto-committed by the workflow after each run. It tracks:
- All processed transaction IDs (to prevent duplicate notifications)
- Per-period cashback totals and transaction history

## Local Testing

```bash
pip install -r requirements.txt

export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export TELEGRAM_BOT_TOKEN="123456789:ABC..."
export TELEGRAM_CHAT_ID="987654321"

python main.py
```

## Updating Purchase Type Rules

Edit [`src/cashback_calculator.py`](src/cashback_calculator.py):

- `QRIS_PURCHASE_TYPES` — set of strings that map to QRIS (cap Rp 10.000/txn)
- `INELIGIBLE_PURCHASE_TYPES` — set of strings that get 0% cashback
- Anything else defaults to online purchase (cap Rp 20.000/txn)

These are plain Python sets, easy to extend as new purchase type strings are discovered in emails.
