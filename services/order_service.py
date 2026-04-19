from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from database.db import Database
from services.outline import OutlineAPIError, OutlineKey, OutlineService

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db: Database, outline_service: OutlineService, default_timezone: str = 'UTC') -> None:
        self.db = db
        self.outline_service = outline_service
        self.default_timezone = default_timezone

    def _current_time(self) -> datetime:
        try:
            tz = ZoneInfo(self.default_timezone)
        except Exception:
            logger.warning('Invalid timezone %s, falling back to UTC', self.default_timezone)
            tz = timezone.utc
        return datetime.now(tz).replace(microsecond=0)

    def generate_key_name(self, telegram_id: int, username: str | None, plan_name: str, expires_at: datetime) -> str:
        safe_username = username or f'User_{telegram_id}'
        safe_plan = plan_name.replace(' ', '_')
        return f'{safe_username}_{safe_plan}_{expires_at.date().isoformat()}'[:100]

    async def approve_order(self, order_id: int, admin_id: int) -> tuple[dict, OutlineKey, str, str]:
        order = self.db.get_order_full(order_id)
        if not order:
            raise ValueError('Order not found')
        if order['status'] != 'pending':
            raise ValueError('Only pending orders can be approved')

        approved_at = self._current_time()
        expires_at = approved_at + timedelta(days=int(order['duration_days']))
        key_name = self.generate_key_name(order['telegram_id'], order['username'], order['plan_name'], expires_at)
        approved_at_iso = approved_at.isoformat()
        expires_at_iso = expires_at.isoformat()

        try:
            outline_key = await self.outline_service.create_access_key(key_name)
        except OutlineAPIError:
            logger.exception('Outline key creation failed for order %s', order_id)
            raise
        except Exception:
            logger.exception('Unexpected error while creating Outline key for order %s', order_id)
            raise

        approved = self.db.approve_order_with_key(
            order_id=order_id,
            admin_id=admin_id,
            user_id=int(order['user_id']),
            outline_key_id=outline_key.key_id,
            access_url=outline_key.access_url,
            key_name=outline_key.name,
            approved_at=approved_at_iso,
            expires_at=expires_at_iso,
        )
        if not approved:
            await self.outline_service.delete_access_key(outline_key.key_id)
            raise ValueError('Order was already processed by another admin')

        order = self.db.get_order_full(order_id)
        return dict(order), outline_key, approved_at.date().isoformat(), expires_at.date().isoformat()

    def reject_order(self, order_id: int, admin_id: int) -> dict:
        order = self.db.get_order_full(order_id)
        if not order:
            raise ValueError('Order not found')
        if order['status'] != 'pending':
            raise ValueError('Only pending orders can be rejected')
        rejected = self.db.reject_order(order_id=order_id, admin_id=admin_id)
        if not rejected:
            raise ValueError('Order was already processed by another admin')
        order = self.db.get_order_full(order_id)
        return dict(order)
