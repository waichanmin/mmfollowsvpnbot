from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List
import os

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str | None) -> List[int]:
    if not raw:
        return []
    admin_ids: List[int] = []
    for item in raw.split(','):
        item = item.strip()
        if not item:
            continue
        admin_ids.append(int(item))
    return admin_ids


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: List[int]
    admin_chat_id: int
    database_path: str
    outline_api_url: str
    outline_api_cert_sha256: str
    default_currency: str
    default_timezone: str
    log_level: str
    support_contact: str

    @property
    def is_outline_enabled(self) -> bool:
        return bool(self.outline_api_url and self.outline_api_cert_sha256)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    bot_token = os.getenv('BOT_TOKEN', '').strip()
    if not bot_token:
        raise ValueError('BOT_TOKEN is required')

    admin_ids = _parse_admin_ids(os.getenv('ADMIN_IDS'))
    admin_chat_raw = os.getenv('ADMIN_CHAT_ID', '').strip()
    if not admin_ids:
        raise ValueError('ADMIN_IDS is required')
    if not admin_chat_raw:
        raise ValueError('ADMIN_CHAT_ID is required')

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        admin_chat_id=int(admin_chat_raw),
        database_path=os.getenv('DATABASE_PATH', 'outline_vpn_bot.sqlite3').strip(),
        outline_api_url=os.getenv('OUTLINE_API_URL', '').strip(),
        outline_api_cert_sha256=os.getenv('OUTLINE_API_CERT_SHA256', '').strip(),
        default_currency=os.getenv('DEFAULT_CURRENCY', 'MMK').strip(),
        default_timezone=os.getenv('DEFAULT_TIMEZONE', 'Asia/Yangon').strip(),
        log_level=os.getenv('LOG_LEVEL', 'INFO').strip(),
        support_contact=os.getenv('SUPPORT_CONTACT', '@admin').strip(),
    )
