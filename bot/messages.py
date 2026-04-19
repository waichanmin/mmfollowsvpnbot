from __future__ import annotations

from collections.abc import Sequence


def welcome_message() -> str:
    return (
        'မင်္ဂလာပါ 👋\n\n'
        '<b>Outline VPN Access Bot</b> မှ ကြိုဆိုပါတယ်။\n'
        'လက်ရှိ available plan များကို ကြည့်ပြီး payment screenshot တင်နိုင်ပါတယ်။\n\n'
        'Welcome! Use the button below to browse available VPN plans.'
    )


def plan_list_message() -> str:
    return '<b>Available VPN Plans</b>\nChoose one plan to continue.'


def format_plan_details(plan: dict, currency: str, payment_block: str) -> str:
    return (
        '<b>Selected Plan</b>\n'
        f"• Name: <b>{plan['name']}</b>\n"
        f"• Duration: <b>{plan['duration_days']} days</b>\n"
        f"• Price: <b>{plan['price']} {currency}</b>\n"
        f"• Description: {plan['description'] or '-'}\n\n"
        f'{payment_block}\n\n'
        '📸 Please upload your payment screenshot now.\n'
        'Screenshot should clearly show amount, receiver, and successful transfer.'
    )


def payment_submitted_message() -> str:
    return (
        '✅ Your payment proof has been submitted and is waiting for admin approval.\n\n'
        'Please wait for confirmation. We will send your Outline key once approved.'
    )


def admin_order_message(order: dict, currency: str) -> str:
    username = f"@{order['username']}" if order['username'] else '-'
    return (
        '🧾 <b>New Payment Request</b>\n\n'
        f"Order ID: <code>{order['id']}</code>\n"
        f"User ID: <code>{order['telegram_id']}</code>\n"
        f"Username: {username}\n"
        f"Full Name: {order['full_name']}\n"
        f"Plan: <b>{order['plan_name']}</b>\n"
        f"Amount: <b>{order['amount']} {currency}</b>\n"
        f"Submitted: <code>{order['created_at']}</code>\n"
        f"Status: <b>{order['status'].upper()}</b>\n\n"
        '👇 Please use buttons below to approve or reject.'
    )


def approved_message(plan_name: str, approved_date: str, expiry_date: str, access_url: str) -> str:
    return (
        '✅ <b>Payment Approved</b>\n\n'
        f'Plan: <b>{plan_name}</b>\n'
        f'Approved Date: <code>{approved_date}</code>\n'
        f'Expiry Date: <code>{expiry_date}</code>\n\n'
        '<b>Your Outline Key</b>\n'
        f'<code>{access_url}</code>\n\n'
        '<b>How to use</b>\n'
        '1. Install the Outline Client\n'
        '2. Copy the key above\n'
        '3. Paste it into Outline Client\n'
        '4. Connect and enjoy secure internet access'
    )


def rejected_message(support_contact: str) -> str:
    return (
        '❌ <b>Payment Rejected</b>\n\n'
        'We could not verify your payment proof. '
        f'Please contact support or resubmit your screenshot: {support_contact}'
    )


def active_plan_message(plan: dict | None) -> str:
    if not plan:
        return 'You do not have an active plan right now.'
    return (
        '🔐 <b>Your Active VPN Plan</b>\n\n'
        f"Plan: <b>{plan['plan_name']}</b>\n"
        f"Created: <code>{plan['created_at']}</code>\n"
        f"Expires: <code>{plan['expires_at']}</code>\n"
        f"Status: <b>{plan['status']}</b>\n\n"
        f"Key: <code>{plan['access_url']}</code>"
    )


def help_message() -> str:
    return (
        '<b>Help</b>\n\n'
        '/start - Start the bot\n'
        '/myplan - View your active plan\n'
        '/help - Show this help\n\n'
        'Admin commands:\n'
        '/admin, /plans, /addplan, /editplan, /deleteplan, /payments, '
        '/addpayment, /editpayment, /deletepayment, /pending, /users, /sales, /outlinecheck, /broadcast'
    )


def pending_summary(orders: Sequence[dict]) -> str:
    if not orders:
        return 'No pending payment requests.'
    lines = ['<b>Pending Orders</b>']
    for order in orders:
        lines.append(
            f"• #{order['id']} | {order['full_name']} | {order['plan_name']} | {order['amount']}"
        )
    return '\n'.join(lines)
