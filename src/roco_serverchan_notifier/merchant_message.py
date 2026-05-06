from __future__ import annotations

from typing import Any

from .push_models import NotificationMessage


def product_summary(products: list[dict[str, Any]]) -> str:
    names = [str(product.get("name") or "未知") for product in products]
    return f"{len(names)}件商品：{'、'.join(names)}" if names else "当前暂无活跃商品"


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_luoke_bay(value: int) -> str:
    if value >= 10000:
        amount = value / 10000
        amount_text = f"{amount:.2f}".rstrip("0").rstrip(".")
        return f"{amount_text}万洛克贝"
    return f"{value}洛克贝"


def _format_price(value: int) -> str:
    return f"{value:,}"


def _status_line(round_info: dict[str, Any]) -> str:
    return f"轮次：{round_info.get('current', '--')}/{round_info.get('total', '--')} · 剩余：{round_info.get('countdown', '--')}"


def _product_lines(
    index: int,
    product: dict[str, Any],
    *,
    include_price_info: bool,
) -> list[str]:
    name = product.get("name", "未知")
    time_label = product.get("time_label", "--:--")
    lines = [f"{index}. {name}", f"时段：{time_label}"]
    if include_price_info:
        price = _to_int(product.get("price"))
        buy_limit_num = _to_int(product.get("buy_limit_num"))
        if price is not None and buy_limit_num is not None:
            total = price * buy_limit_num
            lines.extend(
                [
                    f"数量：{buy_limit_num}",
                    f"单价：{_format_price(price)}",
                    f"合计：{_format_price(total)}（{_format_luoke_bay(total)}）",
                ]
            )
        else:
            lines.append("价格：未收录")
    return lines


def build_merchant_markdown(processed: dict[str, Any], *, include_price_info: bool = False) -> str:
    round_info = processed.get("round_info") or {}
    products = processed.get("products") or []
    lines = [_status_line(round_info)]

    if products:
        lines.append("")
        for index, product in enumerate(products, start=1):
            if index > 1:
                lines.append("")
            lines.extend(_product_lines(index, product, include_price_info=include_price_info))
    else:
        lines.extend(["", "当前暂无活跃商品。"])

    return "\n".join(lines)


def build_notification_message(processed: dict[str, Any], *, include_price_info: bool = False) -> NotificationMessage:
    products = processed.get("products") or []
    body = product_summary(products)
    markdown = build_merchant_markdown(processed, include_price_info=include_price_info)
    return NotificationMessage("远行商人已刷新", body, markdown)
