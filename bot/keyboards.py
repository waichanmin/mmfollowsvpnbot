from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def user_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton('📦 View Plans', callback_data='user:view_plans')]]
    )


def plans_keyboard(plans: list[dict]) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(f"{plan['name']} - {plan['price']}", callback_data=f"plan:{plan['id']}")]
        for plan in plans
    ]
    keyboard.append([InlineKeyboardButton('⬅️ Back', callback_data='user:back_home')])
    return InlineKeyboardMarkup(keyboard)


def admin_order_actions(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('✅ Approve', callback_data=f'admin:approve:{order_id}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'admin:reject:{order_id}'),
        ]]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('📌 Pending', callback_data='admin:pending_list')],
            [InlineKeyboardButton('📦 Plans', callback_data='admin:list_plans')],
            [InlineKeyboardButton('💳 Payments', callback_data='admin:list_payments')],
            [InlineKeyboardButton('📊 Sales', callback_data='admin:sales_stats')],
            [InlineKeyboardButton('👥 Users', callback_data='admin:user_stats')],
        ]
    )
