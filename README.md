# Outline VPN Telegram Bot

A production-oriented Telegram bot for selling Outline VPN access keys with admin approval flow, SQLite storage, and Outline Server API integration.

## Features

- User plan browsing and selection
- Payment instructions and screenshot submission
- Admin approval / rejection actions with inline buttons
- Automatic Outline key generation on approval
- SQLite persistence for users, plans, orders, payment methods, and VPN keys
- Admin tools for plans, payments, pending orders, sales, users, and broadcast
- `/myplan` and `/help` support

## Project Structure

```text
outline_vpn_bot/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── bot/
│   ├── __init__.py
│   ├── keyboards.py
│   ├── messages.py
│   └── handlers/
│       ├── __init__.py
│       ├── admin.py
│       └── user.py
├── database/
│   ├── __init__.py
│   ├── db.py
│   └── models.py
├── services/
│   ├── __init__.py
│   ├── outline.py
│   ├── order_service.py
│   └── payment.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

## Setup

1. Create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment file:
   ```bash
   cp .env.example .env
   ```
4. Fill in Telegram and Outline credentials.
5. Run the bot:
   ```bash
   python app.py
   ```

## Admin Flow

1. User chooses a plan.
2. Bot shows payment methods.
3. User uploads payment screenshot.
4. Bot creates pending order and sends it to admin chat with approve/reject buttons.
5. Admin approves.
6. Bot creates Outline access key and sends it to the user.
7. Admin rejects.
8. Bot updates order status and notifies the user.

## Commands

### User
- `/start`
- `/help`
- `/myplan`

### Admin
- `/admin`
- `/plans`
- `/addplan`
- `/editplan`
- `/deleteplan <id>`
- `/payments`
- `/addpayment`
- `/editpayment`
- `/deletepayment <id>`
- `/pending`
- `/users`
- `/sales`
- `/broadcast`

## Notes About Outline API

- The bot expects the Outline management API URL in `OUTLINE_API_URL`.
- The bot pins the SHA-256 certificate fingerprint from `OUTLINE_API_CERT_SHA256`.
- On approval, it creates a key, optionally renames it, stores the result in SQLite, and sends the access URL to the user.

## Recommended Improvements

- Move SQLite to PostgreSQL for higher concurrency
- Add audit trail table for admin actions
- Add background job for expiring / disabling old keys
- Add richer FSM for admin data entry
- Add payment amount validation and OCR-assisted checks if needed
- Add per-admin action logging to a separate channel
