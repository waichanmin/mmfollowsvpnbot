from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON;')
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception('Database transaction rolled back')
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.transaction() as conn:
            conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    duration_days INTEGER NOT NULL,
                    price REAL NOT NULL,
                    description TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS payment_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    method_name TEXT NOT NULL UNIQUE,
                    account_name TEXT NOT NULL,
                    account_number TEXT NOT NULL,
                    extra_info TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_selections (
                    user_id INTEGER PRIMARY KEY,
                    plan_id INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    screenshot_file_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    approved_at TEXT,
                    rejected_at TEXT,
                    admin_id INTEGER,
                    admin_message_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS vpn_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER NOT NULL UNIQUE,
                    outline_key_id TEXT NOT NULL,
                    access_url TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_vpn_keys_user ON vpn_keys(user_id);
                '''
            )
            self._seed_defaults(conn)

    def _seed_defaults(self, conn: sqlite3.Connection) -> None:
        plan_count = conn.execute('SELECT COUNT(*) AS count FROM plans').fetchone()['count']
        if plan_count == 0:
            conn.executemany(
                '''
                INSERT INTO plans (name, duration_days, price, description, is_active)
                VALUES (?, ?, ?, ?, 1)
                ''',
                [
                    ('7 Days', 7, 3500, 'Short-term access for trial and travel.'),
                    ('30 Days', 30, 10000, 'Monthly plan for regular use.'),
                    ('90 Days', 90, 27000, 'Quarterly plan with better value.'),
                    ('180 Days', 180, 50000, 'Long-term plan for heavy users.'),
                ],
            )

        payment_count = conn.execute('SELECT COUNT(*) AS count FROM payment_methods').fetchone()['count']
        if payment_count == 0:
            conn.executemany(
                '''
                INSERT INTO payment_methods (method_name, account_name, account_number, extra_info, is_active)
                VALUES (?, ?, ?, ?, 1)
                ''',
                [
                    ('KBZPay', 'VPN Store', '09xxxxxxxxx', 'Send exact amount and include your Telegram username.'),
                    ('WavePay', 'VPN Store', '09xxxxxxxxx', 'Screenshot must clearly show transfer success.'),
                    ('AYA Pay', 'VPN Store', '09xxxxxxxxx', 'Use your full name in the note if possible.'),
                    ('Binance Pay', 'VPN Store', '123456789', 'USDT accepted if configured by admin.'),
                ],
            )

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def upsert_user(self, telegram_id: int, username: Optional[str], full_name: str) -> int:
        with self.transaction() as conn:
            conn.execute(
                '''
                INSERT INTO users (telegram_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name
                ''',
                (telegram_id, username, full_name),
            )
            row = conn.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
            return int(row['id'])

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[sqlite3.Row]:
        with self.transaction() as conn:
            return conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()

    def get_active_plans(self) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            rows = conn.execute(
                'SELECT * FROM plans WHERE is_active = 1 ORDER BY duration_days ASC'
            ).fetchall()
            return list(rows)

    def get_all_plans(self) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            rows = conn.execute('SELECT * FROM plans ORDER BY duration_days ASC').fetchall()
            return list(rows)

    def get_plan(self, plan_id: int) -> Optional[sqlite3.Row]:
        with self.transaction() as conn:
            return conn.execute('SELECT * FROM plans WHERE id = ?', (plan_id,)).fetchone()

    def add_plan(self, name: str, duration_days: int, price: float, description: str) -> int:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO plans (name, duration_days, price, description)
                VALUES (?, ?, ?, ?)
                ''',
                (name, duration_days, price, description),
            )
            return int(cursor.lastrowid)

    def update_plan(self, plan_id: int, name: str, duration_days: int, price: float, description: str, is_active: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                '''
                UPDATE plans
                SET name=?, duration_days=?, price=?, description=?, is_active=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                ''',
                (name, duration_days, price, description, is_active, plan_id),
            )

    def delete_plan(self, plan_id: int) -> None:
        with self.transaction() as conn:
            conn.execute('DELETE FROM plans WHERE id = ?', (plan_id,))

    def get_active_payment_methods(self) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            rows = conn.execute(
                'SELECT * FROM payment_methods WHERE is_active = 1 ORDER BY id ASC'
            ).fetchall()
            return list(rows)

    def get_all_payment_methods(self) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            rows = conn.execute('SELECT * FROM payment_methods ORDER BY id ASC').fetchall()
            return list(rows)

    def get_payment_method(self, payment_id: int) -> Optional[sqlite3.Row]:
        with self.transaction() as conn:
            return conn.execute('SELECT * FROM payment_methods WHERE id = ?', (payment_id,)).fetchone()

    def add_payment_method(self, method_name: str, account_name: str, account_number: str, extra_info: str) -> int:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO payment_methods (method_name, account_name, account_number, extra_info)
                VALUES (?, ?, ?, ?)
                ''',
                (method_name, account_name, account_number, extra_info),
            )
            return int(cursor.lastrowid)

    def update_payment_method(self, payment_id: int, method_name: str, account_name: str, account_number: str, extra_info: str, is_active: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                '''
                UPDATE payment_methods
                SET method_name=?, account_name=?, account_number=?, extra_info=?, is_active=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                ''',
                (method_name, account_name, account_number, extra_info, is_active, payment_id),
            )

    def delete_payment_method(self, payment_id: int) -> None:
        with self.transaction() as conn:
            conn.execute('DELETE FROM payment_methods WHERE id = ?', (payment_id,))

    def set_user_selection(self, user_id: int, plan_id: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                '''
                INSERT INTO user_selections (user_id, plan_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    plan_id=excluded.plan_id,
                    updated_at=CURRENT_TIMESTAMP
                ''',
                (user_id, plan_id),
            )

    def get_user_selection(self, user_id: int) -> Optional[sqlite3.Row]:
        with self.transaction() as conn:
            return conn.execute(
                '''
                SELECT us.user_id, us.plan_id, p.name, p.duration_days, p.price, p.description
                FROM user_selections us
                JOIN plans p ON p.id = us.plan_id
                WHERE us.user_id = ?
                ''',
                (user_id,),
            ).fetchone()

    def has_pending_order_for_plan(self, user_id: int, plan_id: int) -> bool:
        with self.transaction() as conn:
            row = conn.execute(
                'SELECT 1 FROM orders WHERE user_id = ? AND plan_id = ? AND status = ? LIMIT 1',
                (user_id, plan_id, 'pending'),
            ).fetchone()
            return row is not None

    def create_order(self, user_id: int, plan_id: int, amount: float, screenshot_file_id: str) -> int:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO orders (user_id, plan_id, amount, screenshot_file_id, status)
                VALUES (?, ?, ?, ?, 'pending')
                ''',
                (user_id, plan_id, amount, screenshot_file_id),
            )
            return int(cursor.lastrowid)

    def get_order_full(self, order_id: int) -> Optional[sqlite3.Row]:
        with self.transaction() as conn:
            return conn.execute(
                '''
                SELECT
                    o.*, u.telegram_id, u.username, u.full_name,
                    p.name AS plan_name, p.duration_days, p.description AS plan_description
                FROM orders o
                JOIN users u ON u.id = o.user_id
                JOIN plans p ON p.id = o.plan_id
                WHERE o.id = ?
                ''',
                (order_id,),
            ).fetchone()

    def set_order_admin_message(self, order_id: int, admin_message_id: int) -> None:
        with self.transaction() as conn:
            conn.execute('UPDATE orders SET admin_message_id = ? WHERE id = ?', (admin_message_id, order_id))

    def get_pending_orders(self, limit: int = 20) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            rows = conn.execute(
                '''
                SELECT
                    o.*, u.telegram_id, u.username, u.full_name, p.name AS plan_name
                FROM orders o
                JOIN users u ON u.id = o.user_id
                JOIN plans p ON p.id = o.plan_id
                WHERE o.status = 'pending'
                ORDER BY o.created_at ASC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
            return list(rows)

    def approve_order(self, order_id: int, admin_id: int) -> bool:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                UPDATE orders
                SET status = 'approved', approved_at = CURRENT_TIMESTAMP, admin_id = ?
                WHERE id = ? AND status = 'pending'
                ''',
                (admin_id, order_id),
            )
            return cursor.rowcount == 1

    def approve_order_with_key(
        self,
        order_id: int,
        admin_id: int,
        user_id: int,
        outline_key_id: str,
        access_url: str,
        key_name: str,
        approved_at: str,
        expires_at: str,
    ) -> bool:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                UPDATE orders
                SET status = 'approved', approved_at = ?, admin_id = ?
                WHERE id = ? AND status = 'pending'
                ''',
                (approved_at, admin_id, order_id),
            )
            if cursor.rowcount != 1:
                return False

            conn.execute(
                '''
                INSERT INTO vpn_keys (user_id, order_id, outline_key_id, access_url, key_name, created_at, expires_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                ''',
                (user_id, order_id, outline_key_id, access_url, key_name, approved_at, expires_at),
            )
            return True

    def reject_order(self, order_id: int, admin_id: int) -> bool:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                UPDATE orders
                SET status = 'rejected', rejected_at = CURRENT_TIMESTAMP, admin_id = ?
                WHERE id = ? AND status = 'pending'
                ''',
                (admin_id, order_id),
            )
            return cursor.rowcount == 1

    def add_vpn_key(self, user_id: int, order_id: int, outline_key_id: str, access_url: str, key_name: str, created_at: str, expires_at: str) -> int:
        with self.transaction() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO vpn_keys (user_id, order_id, outline_key_id, access_url, key_name, created_at, expires_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                ''',
                (user_id, order_id, outline_key_id, access_url, key_name, created_at, expires_at),
            )
            return int(cursor.lastrowid)

    def get_latest_active_key_for_user(self, telegram_id: int) -> Optional[sqlite3.Row]:
        with self.transaction() as conn:
            return conn.execute(
                '''
                SELECT
                    p.name AS plan_name,
                    v.access_url,
                    v.created_at,
                    v.expires_at,
                    v.status
                FROM vpn_keys v
                JOIN users u ON u.id = v.user_id
                JOIN orders o ON o.id = v.order_id
                JOIN plans p ON p.id = o.plan_id
                WHERE u.telegram_id = ? AND v.status = 'active'
                ORDER BY v.expires_at DESC
                LIMIT 1
                ''',
                (telegram_id,),
            ).fetchone()

    def get_user_stats(self) -> sqlite3.Row:
        with self.transaction() as conn:
            return conn.execute(
                '''
                SELECT
                    (SELECT COUNT(*) FROM users) AS total_users,
                    (SELECT COUNT(*) FROM orders) AS total_orders,
                    (SELECT COUNT(*) FROM orders WHERE status='pending') AS pending_orders,
                    (SELECT COUNT(*) FROM orders WHERE status='approved') AS approved_orders,
                    (SELECT COUNT(*) FROM orders WHERE status='rejected') AS rejected_orders
                '''
            ).fetchone()

    def get_sales_stats(self) -> sqlite3.Row:
        with self.transaction() as conn:
            return conn.execute(
                '''
                SELECT
                    COALESCE(SUM(amount), 0) AS total_revenue,
                    COUNT(*) AS approved_sales
                FROM orders
                WHERE status='approved'
                '''
            ).fetchone()
