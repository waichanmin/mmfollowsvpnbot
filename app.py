from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers import admin, user
from config import get_settings
from database.db import Database
from services.order_service import OrderService
from services.outline import OutlineService


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.getLogger(__name__).exception('Unhandled bot error', exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                'Something went wrong. Please try again later or contact admin.'
            )
        except Exception:
            logging.getLogger(__name__).exception('Failed to send error message to user')


def build_application() -> Application:
    settings = get_settings()
    configure_logging(settings.log_level)

    db = Database(settings.database_path)
    outline_service = OutlineService(settings.outline_api_url, settings.outline_api_cert_sha256)
    order_service = OrderService(db, outline_service)

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data['settings'] = settings
    application.bot_data['db'] = db
    application.bot_data['outline_service'] = outline_service
    application.bot_data['order_service'] = order_service

    application.add_handler(CommandHandler('start', user.start_command))
    application.add_handler(CommandHandler('help', user.help_command))
    application.add_handler(CommandHandler('myplan', user.my_plan_command))

    application.add_handler(CommandHandler('admin', admin.admin_command))
    application.add_handler(CommandHandler('plans', admin.list_plans_command))
    application.add_handler(CommandHandler('addplan', admin.add_plan_command))
    application.add_handler(CommandHandler('editplan', admin.edit_plan_command))
    application.add_handler(CommandHandler('deleteplan', admin.delete_plan_command))
    application.add_handler(CommandHandler('payments', admin.list_payments_command))
    application.add_handler(CommandHandler('addpayment', admin.add_payment_command))
    application.add_handler(CommandHandler('editpayment', admin.edit_payment_command))
    application.add_handler(CommandHandler('deletepayment', admin.delete_payment_command))
    application.add_handler(CommandHandler('pending', admin.pending_command))
    application.add_handler(CommandHandler('users', admin.users_command))
    application.add_handler(CommandHandler('sales', admin.sales_command))
    application.add_handler(CommandHandler('broadcast', admin.broadcast_command))

    application.add_handler(CallbackQueryHandler(user.show_plans, pattern=r'^user:view_plans$'))
    application.add_handler(CallbackQueryHandler(user.show_plans, pattern=r'^user:back_home$'))
    application.add_handler(CallbackQueryHandler(user.plan_selected, pattern=r'^plan:\d+$'))
    application.add_handler(CallbackQueryHandler(admin.admin_callback_router, pattern=r'^admin:'))

    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, user.payment_screenshot_received))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin.process_admin_text))

    application.add_error_handler(on_error)
    return application


if __name__ == '__main__':
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)
