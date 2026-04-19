from __future__ import annotations

from typing import Sequence


def render_payment_methods(methods: Sequence[dict]) -> str:
    lines: list[str] = ['<b>Payment Methods</b>']
    for method in methods:
        lines.append(
            '\n'.join(
                [
                    f"• <b>{method['method_name']}</b>",
                    f"  Account Name: <code>{method['account_name']}</code>",
                    f"  Account / Phone: <code>{method['account_number']}</code>",
                    f"  Note: {method['extra_info'] or '-'}",
                ]
            )
        )
    return '\n\n'.join(lines)
