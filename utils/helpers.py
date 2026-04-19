from __future__ import annotations

from html import escape
from typing import Any

from telegram import Update


def display_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return 'Unknown User'
    full_name = ' '.join(part for part in [user.first_name, user.last_name] if part)
    return full_name or user.username or str(user.id)


def row_to_dict(row: Any) -> dict:
    return dict(row) if row is not None else {}


def html_code(value: Any) -> str:
    return f'<code>{escape(str(value))}</code>'
