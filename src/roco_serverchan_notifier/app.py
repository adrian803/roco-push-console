from __future__ import annotations

import asyncio
from typing import Any

import requests

from .config import ConfigStore, Settings
from .push import DeliveryReport, NotificationMessage, send_delivery
from .rocom import fetch_merchant_data, process_merchant_data


LAST_DELIVERY_REPORT: DeliveryReport | None = None


def _summary(products: list[dict[str, Any]]) -> str:
    names = [str(product.get("name") or "未知") for product in products]
    return f"当前售卖: {'、'.join(names)}" if names else "当前暂无活跃商品"


def build_merchant_markdown(processed: dict[str, Any]) -> str:
    round_info = processed.get("round_info") or {}
    products = processed.get("products") or []

    lines = [
        "### 远行商人刷新详情",
        "",
        f"- 当前轮次：{round_info.get('current', '--')}/{round_info.get('total', '--')}",
        f"- 剩余时间：{round_info.get('countdown', '--')}",
        f"- 商品数量：{len(products)}",
        "",
    ]

    if products:
        lines.append("#### 当前售卖")
        for product in products:
            name = product.get("name", "未知")
            time_label = product.get("time_label", "--:--")
            lines.append(f"- {name}（{time_label}）")
    else:
        lines.append("当前暂无活跃商品。")

    return "\n".join(lines)


def _clear_last_delivery_report() -> None:
    global LAST_DELIVERY_REPORT
    LAST_DELIVERY_REPORT = None


def _send_and_log(settings: Settings, message: NotificationMessage, session: requests.Session) -> bool:
    global LAST_DELIVERY_REPORT
    report = send_delivery(
        settings.providers,
        message,
        mode=settings.delivery_mode,
        selected_provider=settings.selected_provider,
        failover_order=settings.failover_order,
        session=session,
        timeout=settings.http_timeout,
    )
    LAST_DELIVERY_REPORT = report
    print(f"推送结果：{report.summary()}")
    for result in report.results:
        status = "成功" if result.success else "失败"
        print(f"  - {result.provider_name}({result.provider_type}): {status} {result.message}")
    return report.success


def get_last_delivery_report() -> DeliveryReport | None:
    return LAST_DELIVERY_REPORT


def run_once(settings: Settings) -> int:
    _clear_last_delivery_report()
    missing = settings.missing_required()
    if missing:
        print(f"缺少必要环境变量: {', '.join(missing)}")
        return 2

    session = requests.Session()
    try:
        raw_data = fetch_merchant_data(
            settings.game_api_url,
            settings.rocom_api_key,
            session=session,
            timeout=settings.http_timeout,
        )
    except Exception as exc:
        message = f"无法获取远行商人数据: {exc}"
        print(message)
        _send_and_log(
            settings,
            NotificationMessage("远行商人监控异常", message, message),
            session,
        )
        return 1

    processed = process_merchant_data(raw_data)
    products = processed.get("products") or []
    if not products and not settings.notify_empty:
        print("当前暂无活跃商品，已按 NOTIFY_EMPTY=false 跳过推送")
        return 0

    markdown = build_merchant_markdown(processed)
    title = "远行商人已刷新"
    body = _summary(products)
    success = _send_and_log(
        settings,
        NotificationMessage(title, body, f"{body}\n\n{markdown}"),
        session,
    )
    return 0 if success else 1


async def run(settings: Settings) -> int:
    return await asyncio.to_thread(run_once, settings)


async def main() -> int:
    return await run(ConfigStore().load())


def cli() -> None:
    raise SystemExit(asyncio.run(main()))
