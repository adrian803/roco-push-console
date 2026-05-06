from __future__ import annotations

import asyncio
from dataclasses import dataclass

import requests

from .config_store import ConfigStore
from .merchant_message import build_merchant_markdown, build_notification_message
from .push import DeliveryReport, send_delivery
from .push_models import DeliveryOptions, NotificationMessage
from .rocom import fetch_merchant_data, process_merchant_data
from .settings import Settings


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

    message = build_notification_message(processed, include_price_info=settings.include_price_info)
    report = _send_and_log(
        settings,
        message,
        session,
    )
    return RunResult(0 if report.success else 1, report)


async def run(settings: Settings) -> RunResult:
    return await asyncio.to_thread(run_once, settings)


async def main() -> int:
    return (await run(ConfigStore().load())).exit_code


def cli() -> None:
    raise SystemExit(asyncio.run(main()))
