from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot import keyboards, messages
from services.payment import render_payment_methods
from utils.helpers import display_name

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    user = update.effective_user
    if not user or not update.effective_message:
        return

    db.upsert_user(user.id, user.username, display_name(update))
    await update.effective_message.reply_text(
        messages.welcome_message(),
        parse_mode='HTML',
        reply_markup=keyboards.user_main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(messages.help_message(), parse_mode='HTML')


async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    plans = [dict(row) for row in db.get_active_plans()]
    if not plans:
        text = 'No active plans are available right now. Please contact admin.'
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text)
        elif update.effective_message:
            await update.effective_message.reply_text(text)
        return

    markup = keyboards.plans_keyboard(plans)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            messages.plan_list_message(), parse_mode='HTML', reply_markup=markup
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            messages.plan_list_message(), parse_mode='HTML', reply_markup=markup
        )


async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_user:
        return
    await query.answer()

    db = context.application.bot_data['db']
    settings = context.application.bot_data['settings']
    user_id = db.upsert_user(update.effective_user.id, update.effective_user.username, display_name(update))

    try:
        plan_id = int(query.data.split(':')[1])
    except (IndexError, ValueError):
        await query.edit_message_text('Invalid plan selection.')
        return

    plan = db.get_plan(plan_id)
    if not plan or not int(plan['is_active']):
        await query.edit_message_text('This plan is no longer available.')
        return

    db.set_user_selection(user_id, plan_id)
    payment_methods = [dict(row) for row in db.get_active_payment_methods()]
    payment_text = render_payment_methods(payment_methods)
    await query.edit_message_text(
        messages.format_plan_details(dict(plan), settings.default_currency, payment_text),
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('⬅️ Plans', callback_data='user:view_plans')]]
        ),
    )


async def payment_screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    settings = context.application.bot_data['settings']
    user = update.effective_user
    message = update.effective_message
    bot = context.bot
    if not user or not message or not message.photo:
        return

    user_id = db.upsert_user(user.id, user.username, display_name(update))
    selection = db.get_user_selection(user_id)
    if not selection:
        await message.reply_text('Please select a plan first by using /start.')
        return

    if db.has_pending_order_for_plan(user_id, int(selection['plan_id'])):
        await message.reply_text(
            'You already have a pending order for this plan. Please wait for admin review.'
        )
        return

    screenshot_file_id = message.photo[-1].file_id
    order_id = db.create_order(
        user_id=user_id,
        plan_id=int(selection['plan_id']),
        amount=float(selection['price']),
        screenshot_file_id=screenshot_file_id,
    )
    order = dict(db.get_order_full(order_id))

    admin_message = None
    try:
        admin_message = await bot.send_photo(
            chat_id=settings.admin_chat_id,
            photo=screenshot_file_id,
            caption=messages.admin_order_message(order, settings.default_currency),
            parse_mode='HTML',
            reply_markup=keyboards.admin_order_actions(order_id),
        )
    except Exception:
        logger.exception('Failed to send order %s to admin chat %s', order_id, settings.admin_chat_id)
        for admin_id in settings.admin_ids:
            try:
                sent = await bot.send_photo(
                    chat_id=admin_id,
                    photo=screenshot_file_id,
                    caption=messages.admin_order_message(order, settings.default_currency),
                    parse_mode='HTML',
                    reply_markup=keyboards.admin_order_actions(order_id),
                )
                if admin_message is None:
                    admin_message = sent
            except Exception:
                logger.exception('Failed to send order %s to admin %s', order_id, admin_id)

    if admin_message:
        db.set_order_admin_message(order_id, admin_message.message_id)
        await message.reply_text(messages.payment_submitted_message(), parse_mode='HTML')
    else:
        await message.reply_text(
            'Payment screenshot saved but failed to notify admin automatically. '
            'Please contact support.',
            parse_mode='HTML',
        )


async def my_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    if not update.effective_user or not update.effective_message:
        return
    plan = db.get_latest_active_key_for_user(update.effective_user.id)
    await update.effective_message.reply_text(
        messages.active_plan_message(dict(plan) if plan else None), parse_mode='HTML'
    )
