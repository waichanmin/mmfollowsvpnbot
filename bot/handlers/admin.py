from __future__ import annotations

import logging
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from bot import keyboards, messages
from services.outline import OutlineAPIError

logger = logging.getLogger(__name__)

PLAN_DRAFT = 'plan_draft'
PAYMENT_DRAFT = 'payment_draft'
BROADCAST_MODE = 'broadcast_mode'


def admin_only(func: Callable):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        settings = context.application.bot_data['settings']
        user = update.effective_user
        if not user or user.id not in settings.admin_ids:
            if update.effective_message:
                await update.effective_message.reply_text('Unauthorized.')
            elif update.callback_query:
                await update.callback_query.answer('Unauthorized', show_alert=True)
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            '🛠 <b>Admin Menu</b>', parse_mode='HTML', reply_markup=keyboards.admin_menu_keyboard()
        )


@admin_only
async def list_plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    plans = db.get_all_plans()
    lines = ['<b>Plans</b>']
    for plan in plans:
        status = 'Active' if int(plan['is_active']) else 'Disabled'
        lines.append(
            f"#{plan['id']} | {plan['name']} | {plan['duration_days']} days | {plan['price']} | {status}"
        )
    text = '\n'.join(lines)
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboards.admin_menu_keyboard())


@admin_only
async def add_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[PLAN_DRAFT] = {'mode': 'add'}
    await update.effective_message.reply_text(
        'Send plan in this format:\n<name>|<duration_days>|<price>|<description>'
    )


@admin_only
async def edit_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[PLAN_DRAFT] = {'mode': 'edit'}
    await update.effective_message.reply_text(
        'Send plan update in this format:\n<id>|<name>|<duration_days>|<price>|<is_active:0_or_1>|<description>'
    )


@admin_only
async def delete_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    args = context.args
    if not args:
        await update.effective_message.reply_text('Usage: /deleteplan <plan_id>')
        return
    db.delete_plan(int(args[0]))
    await update.effective_message.reply_text('Plan deleted.')


@admin_only
async def list_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    methods = db.get_all_payment_methods()
    lines = ['<b>Payment Methods</b>']
    for method in methods:
        status = 'Active' if int(method['is_active']) else 'Disabled'
        lines.append(
            f"#{method['id']} | {method['method_name']} | {method['account_name']} | {method['account_number']} | {status}"
        )
    text = '\n'.join(lines)
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboards.admin_menu_keyboard())


@admin_only
async def add_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[PAYMENT_DRAFT] = {'mode': 'add'}
    if update.effective_message:
        await update.effective_message.reply_text(
            'Send payment method in this format:\n<method>|<account_name>|<account_number>|<extra_info>'
        )
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            'Send payment method in this format:\n<method>|<account_name>|<account_number>|<extra_info>'
        )


@admin_only
async def edit_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[PAYMENT_DRAFT] = {'mode': 'edit'}
    if update.effective_message:
        await update.effective_message.reply_text(
            'Send payment update in this format:\n<id>|<method>|<account_name>|<account_number>|<is_active:0_or_1>|<extra_info>'
        )
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            'Send payment update in this format:\n<id>|<method>|<account_name>|<account_number>|<is_active:0_or_1>|<extra_info>'
        )


@admin_only
async def delete_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    args = context.args
    if not args:
        await update.effective_message.reply_text('Usage: /deletepayment <payment_id>')
        return
    db.delete_payment_method(int(args[0]))
    await update.effective_message.reply_text('Payment method deleted.')


@admin_only
async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    orders = [dict(row) for row in db.get_pending_orders()]
    if not update.effective_message:
        return
    await update.effective_message.reply_text(messages.pending_summary(orders), parse_mode='HTML')
    for order in orders:
        await update.effective_message.reply_photo(
            photo=order['screenshot_file_id'],
            caption=messages.admin_order_message(order, context.application.bot_data['settings'].default_currency),
            parse_mode='HTML',
            reply_markup=keyboards.admin_order_actions(int(order['id'])),
        )


@admin_only
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    stats = db.get_user_stats()
    text = (
        '<b>User Stats</b>\n'
        f"Total Users: {stats['total_users']}\n"
        f"Total Orders: {stats['total_orders']}\n"
        f"Pending: {stats['pending_orders']}\n"
        f"Approved: {stats['approved_orders']}\n"
        f"Rejected: {stats['rejected_orders']}"
    )
    await update.effective_message.reply_text(text, parse_mode='HTML')


@admin_only
async def sales_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    settings = context.application.bot_data['settings']
    stats = db.get_sales_stats()
    text = (
        '<b>Sales Stats</b>\n'
        f"Approved Sales: {stats['approved_sales']}\n"
        f"Revenue: {stats['total_revenue']} {settings.default_currency}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode='HTML')
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboards.admin_menu_keyboard())


@admin_only
async def outline_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    outline_service = context.application.bot_data['outline_service']
    if not update.effective_message:
        return
    await update.effective_message.reply_text('Checking Outline server...')
    try:
        result = await outline_service.health_check()
        await update.effective_message.reply_text(f'✅ {result}')
    except OutlineAPIError as exc:
        await update.effective_message.reply_text(
            '❌ Outline check failed.\n'
            f'Reason: {exc}\n\n'
            'Check URL/network/firewall and certificate fingerprint.'
        )


@admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[BROADCAST_MODE] = True
    await update.effective_message.reply_text('Send the broadcast message text now. /cancel to stop.')


@admin_only
async def process_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    text = update.effective_message.text.strip()

    if context.user_data.get(BROADCAST_MODE):
        context.user_data.pop(BROADCAST_MODE, None)
        users = []
        with db.transaction() as conn:
            users = conn.execute('SELECT telegram_id FROM users').fetchall()
        sent = 0
        for row in users:
            try:
                await context.bot.send_message(chat_id=row['telegram_id'], text=text)
                sent += 1
            except Exception:
                logger.exception('Broadcast failed for user %s', row['telegram_id'])
        await update.effective_message.reply_text(f'Broadcast sent to {sent} users.')
        return

    if PLAN_DRAFT in context.user_data:
        draft = context.user_data.pop(PLAN_DRAFT)
        parts = [part.strip() for part in text.split('|')]
        try:
            if draft['mode'] == 'add':
                name, duration_days, price, description = parts
                db.add_plan(name, int(duration_days), float(price), description)
                await update.effective_message.reply_text('Plan added successfully.')
            else:
                plan_id, name, duration_days, price, is_active, description = parts
                db.update_plan(int(plan_id), name, int(duration_days), float(price), description, int(is_active))
                await update.effective_message.reply_text('Plan updated successfully.')
        except Exception as exc:
            logger.exception('Failed to process plan draft')
            await update.effective_message.reply_text(f'Failed to save plan: {exc}')
        return

    if PAYMENT_DRAFT in context.user_data:
        draft = context.user_data.pop(PAYMENT_DRAFT)
        parts = [part.strip() for part in text.split('|')]
        try:
            if draft['mode'] == 'add':
                method, account_name, account_number, extra_info = parts
                db.add_payment_method(method, account_name, account_number, extra_info)
                await update.effective_message.reply_text('Payment method added successfully.')
            else:
                payment_id, method, account_name, account_number, is_active, extra_info = parts
                db.update_payment_method(
                    int(payment_id), method, account_name, account_number, extra_info, int(is_active)
                )
                await update.effective_message.reply_text('Payment method updated successfully.')
        except Exception as exc:
            logger.exception('Failed to process payment method draft')
            await update.effective_message.reply_text(f'Failed to save payment method: {exc}')


@admin_only
async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['settings']
    order_service = context.application.bot_data['order_service']

    data = query.data
    if data == 'admin:pending_list':
        orders = [dict(row) for row in db.get_pending_orders()]
        await query.answer()
        await query.edit_message_text(
            messages.pending_summary(orders),
            parse_mode='HTML',
            reply_markup=keyboards.admin_menu_keyboard(),
        )
        for order in orders:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=order['screenshot_file_id'],
                caption=messages.admin_order_message(order, settings.default_currency),
                parse_mode='HTML',
                reply_markup=keyboards.admin_order_actions(int(order['id'])),
            )
        return
    if data == 'admin:list_plans':
        await list_plans_command(update, context)
        return
    if data == 'admin:list_payments':
        await list_payments_command(update, context)
        return
    if data == 'admin:add_payment':
        await query.answer()
        await add_payment_command(update, context)
        return
    if data == 'admin:edit_payment':
        await query.answer()
        await edit_payment_command(update, context)
        return
    if data == 'admin:sales_stats':
        await sales_command(update, context)
        return
    if data == 'admin:user_stats':
        await users_command(update, context)
        return

    parts = data.split(':')
    if len(parts) != 3 or parts[1] not in {'approve', 'reject'}:
        await query.answer('Unknown action', show_alert=True)
        return

    action, order_id = parts[1], int(parts[2])
    try:
        if action == 'approve':
            await query.answer('Approving...')
            order, outline_key, approved_date, expiry_date = await order_service.approve_order(order_id, query.from_user.id)
            await context.bot.send_message(
                chat_id=order['telegram_id'],
                text=messages.approved_message(order['plan_name'], approved_date, expiry_date, outline_key.access_url),
                parse_mode='HTML',
            )
            await query.edit_message_caption(
                caption=(
                    messages.admin_order_message(order, settings.default_currency)
                    + f'\n\n✅ Approved on <code>{approved_date}</code>'
                    + f'\n👤 Approved by: <code>{query.from_user.id}</code>'
                    + f'\n🔑 Key issued: <code>{outline_key.key_id}</code>'
                    + f'\n📅 Expires: <code>{expiry_date}</code>'
                ),
                parse_mode='HTML',
            )
        else:
            await query.answer('Rejecting...')
            order = order_service.reject_order(order_id, query.from_user.id)
            await context.bot.send_message(
                chat_id=order['telegram_id'],
                text=messages.rejected_message(settings.support_contact),
                parse_mode='HTML',
            )
            await query.edit_message_caption(
                caption=messages.admin_order_message(order, settings.default_currency) + '\n\n❌ Rejected',
                parse_mode='HTML',
            )
    except OutlineAPIError as exc:
        await query.answer('Outline API failed', show_alert=True)
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                f'Failed to generate Outline key for order #{order_id}: {exc}\n\n'
                'Please verify:\n'
                '1) OUTLINE_API_URL is reachable from server\n'
                '2) OUTLINE_API_CERT_SHA256 matches current Outline cert\n'
                '3) Outline Manager API is up'
            ),
        )
    except ValueError as exc:
        await query.answer(str(exc), show_alert=True)
    except Exception as exc:
        logger.exception('Admin action failed')
        await query.answer('Unexpected error', show_alert=True)
        await context.bot.send_message(chat_id=query.from_user.id, text=f'Unexpected error: {exc}')
