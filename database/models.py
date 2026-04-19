from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class User:
    id: int
    telegram_id: int
    username: Optional[str]
    full_name: str
    created_at: str


@dataclass(slots=True)
class Plan:
    id: int
    name: str
    duration_days: int
    price: float
    description: str
    is_active: int
    created_at: str
    updated_at: str


@dataclass(slots=True)
class PaymentMethod:
    id: int
    method_name: str
    account_name: str
    account_number: str
    extra_info: Optional[str]
    is_active: int
    created_at: str
    updated_at: str


@dataclass(slots=True)
class Order:
    id: int
    user_id: int
    plan_id: int
    amount: float
    screenshot_file_id: str
    status: str
    created_at: str
    approved_at: Optional[str]
    rejected_at: Optional[str]
    admin_id: Optional[int]
    admin_message_id: Optional[int]


@dataclass(slots=True)
class VPNKey:
    id: int
    user_id: int
    order_id: int
    outline_key_id: str
    access_url: str
    key_name: str
    created_at: str
    expires_at: str
    status: str


@dataclass(slots=True)
class UserActivePlan:
    plan_name: str
    access_url: str
    created_at: str
    expires_at: str
    status: str
