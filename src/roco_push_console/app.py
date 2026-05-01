from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import requests

from .config import ConfigStore, Settings
from .push import DeliveryOptions, DeliveryReport, NotificationMessage, send_delivery
from .rocom import fetch_merchant_data, process_merchant_data


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    report: DeliveryReport | None = None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.exit_code == other
        if isinstance(other, RunResult):
            return (self.exit_code, self.report) == (other.exit_code, other.report)
        return False

    def __int__(self) -> int:
        return self.exit_code


def _summary(products: list[dict[str, Any]]) -> str:
    names = [str(product.get("name") or "未知") for product in products]
    return f"当前售卖: {'、'.join(names)}" if names else "当前暂无活跃商品"


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


def _product_line(product: dict[str, Any], *, include_price_info: bool) -> str:
    name = product.get("name", "未知")
    time_label = product.get("time_label", "--:--")
    if include_price_info:
        price = _to_int(product.get("price"))
        buy_limit_num = _to_int(product.get("buy_limit_num"))
        if price is not None and buy_limit_num is not None:
            total = price * buy_limit_num
            return (
                f"{name}*{buy_limit_num}（{time_label}）"
                f"单价{price} 合计{total:,}（{_format_luoke_bay(total)}）"
            )
    return f"{name}（{time_label}）"


def build_merchant_markdown(processed: dict[str, Any], *, include_price_info: bool = False) -> str:
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
            lines.append(f"- {_product_line(product, include_price_info=include_price_info)}")
    else:
        lines.append("当前暂无活跃商品。")

    return "\n".join(lines)


def _send_and_log(settings: Settings, message: NotificationMessage, session: requests.Session) -> DeliveryReport:
    report = send_delivery(
        settings.providers,
        message,
        options=DeliveryOptions(
            mode=settings.delivery_mode,
            selected_provider=settings.selected_provider,
            failover_order=settings.failover_order,
            session=session,
            timeout=settings.http_timeout,
        ),
    )
    print(f"推送结果：{report.summary()}")
    for result in report.results:
        status = "成功" if result.success else "失败"
        print(f"  - {result.provider_name}({result.provider_type}): {status} {result.message}")
    return report


def get_last_delivery_report() -> DeliveryReport | None:
    return None


def run_once(settings: Settings) -> RunResult:
    missing = settings.missing_required()
    if missing:
        print(f"缺少必要环境变量: {', '.join(missing)}")
        return RunResult(2)

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
        report = _send_and_log(
            settings,
            NotificationMessage("远行商人监控异常", message, message),
            session,
        )
        return RunResult(1, report)

    processed = process_merchant_data(raw_data)
    products = processed.get("products") or []
    if not products and not settings.notify_empty:
        print("当前暂无活跃商品，已按 NOTIFY_EMPTY=false 跳过推送")
        return RunResult(0)

    markdown = build_merchant_markdown(processed, include_price_info=settings.include_price_info)
    title = "远行商人已刷新"
    body = _summary(products)
    report = _send_and_log(
        settings,
        NotificationMessage(title, body, f"{body}\n\n{markdown}"),
        session,
    )
    return RunResult(0 if report.success else 1, report)


async def run(settings: Settings) -> RunResult:
    return await asyncio.to_thread(run_once, settings)


async def main() -> int:
    return (await run(ConfigStore().load())).exit_code


def cli() -> None:
    raise SystemExit(asyncio.run(main()))
